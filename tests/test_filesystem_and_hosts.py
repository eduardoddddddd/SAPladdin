from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from core import hosts
from core.tools import filesystem, hosts_mgmt, ssh


class _FakeStdout:
    def __init__(self, payload: str) -> None:
        self._payload = payload.encode("utf-8")
        self.channel = self

    def read(self) -> bytes:
        return self._payload

    def recv_exit_status(self) -> int:
        return 0


class _FakeStderr:
    def read(self) -> bytes:
        return b""


class _FakeSSHClient:
    def exec_command(self, command: str, timeout: int, get_pty: bool = False):
        del timeout, get_pty
        if "GetProcessList" in command:
            payload = "disp+work, GREEN, Running\nigswd_mt, YELLOW, Running\n"
        else:
            payload = "00, DVEBMGS00, host1, 00\n01, ASCS01, host2, 01\n"
        return None, _FakeStdout(payload), _FakeStderr()


@pytest.fixture()
def allowed_tmp(monkeypatch: pytest.MonkeyPatch) -> Path:
    temp_root = Path(__file__).resolve().parent / "_tmp"
    temp_root.mkdir(exist_ok=True)
    test_dir = temp_root / f"case_{uuid4().hex}"
    test_dir.mkdir()
    monkeypatch.setattr(filesystem, "_allowed", lambda: [str(test_dir)])
    try:
        yield test_dir
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_search_files_defaults_to_case_insensitive_name_matching(allowed_tmp: Path) -> None:
    target = allowed_tmp / "SapNote.TXT"
    target.write_text("kernel patch\n", encoding="utf-8")

    result = await filesystem.search_files(str(allowed_tmp), "sapnote")

    assert str(target) in result


@pytest.mark.asyncio
async def test_search_files_respects_case_sensitive_content_and_name(allowed_tmp: Path) -> None:
    target = allowed_tmp / "SAPKernel.log"
    target.write_text("System OK\n", encoding="utf-8")

    result = await filesystem.search_files(
        str(allowed_tmp),
        "sapkernel",
        content_search="system",
        case_sensitive="true",
    )

    assert "No files matching" in result


@pytest.mark.asyncio
async def test_add_host_uses_database_field_for_mssql(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: list[dict] = []

    monkeypatch.setattr(hosts_mgmt, "_load_hosts", lambda: [])
    monkeypatch.setattr(hosts_mgmt, "_save_hosts", lambda items: saved.extend(items))

    result = await hosts_mgmt.add_host(
        name="sqlserver_prod",
        alias="sqlprd",
        host_type="mssql",
        ip="10.0.0.10",
        database="SAPPRD",
        user="sa",
    )

    assert "database=SAPPRD" in result
    assert saved[0]["database"] == "SAPPRD"
    assert "service" not in saved[0]


@pytest.mark.asyncio
async def test_ssh_connect_returns_clear_error_when_alias_is_missing() -> None:
    result = await ssh.ssh_connect(alias="missing-host")

    assert "No se pudo resolver el host SSH" in result


def test_get_host_config_matches_by_alias_or_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        hosts,
        "_load_hosts",
        lambda: [
            {"name": "oracle_prod", "alias": "oraprd", "host": "10.0.0.20"},
        ],
    )

    assert hosts.get_host_config("oraprd")["host"] == "10.0.0.20"
    assert hosts.get_host_config("oracle_prod")["host"] == "10.0.0.20"


@pytest.mark.asyncio
async def test_sap_check_work_processes_summarizes_statuses(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.tools import sap_basis

    monkeypatch.setattr(ssh, "_ssh_pool", {"sapapp1": _FakeSSHClient()})

    result = await sap_basis.sap_check_work_processes(
        alias="sapapp1",
        instance_nr="00",
    )

    assert "GREEN=1" in result
    assert "YELLOW=1" in result


@pytest.mark.asyncio
async def test_sap_list_instances_reuses_existing_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.tools import sap_basis

    monkeypatch.setattr(ssh, "_ssh_pool", {"sapapp1": _FakeSSHClient()})

    result = await sap_basis.sap_list_instances(alias="sapapp1")

    assert "DVEBMGS00" in result


def test_hana_load_config_falls_back_to_desktopcommanderpy(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.tools import hana
    import builtins

    fake_config = Path(r"C:\Users\Edu\DesktopCommanderPy\config\hana_config.yaml")
    yaml_text = (
        "hana:\n"
        "  host: test.example.com\n"
        "  port: 443\n"
        "  user: DBADMIN\n"
        "  password: secret\n"
        "  sslValidateCertificate: false\n"
    )

    monkeypatch.setattr(hana, "_candidate_config_paths", lambda: [fake_config])
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == str(fake_config))
    original_open = builtins.open

    def fake_open(path, *args, **kwargs):
        if str(path) == str(fake_config):
            from io import StringIO

            return StringIO(yaml_text)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    cfg = hana._load_hana_config()

    assert cfg["host"] == "test.example.com"
    assert cfg["sslValidateCertificate"] is False


def test_hana_safe_identifier_rejects_unsafe_names() -> None:
    from core.tools import hana

    with pytest.raises(ValueError):
        hana._safe_identifier("BAD-NAME", "schema")


def test_mssql_safe_identifier_rejects_unsafe_names() -> None:
    from core.tools import mssql

    with pytest.raises(ValueError):
        mssql._safe_identifier("master]; DROP TABLE x;--", "database")


def test_oracle_safe_identifier_rejects_unsafe_names() -> None:
    from core.tools import oracle

    with pytest.raises(ValueError):
        oracle._safe_identifier("SAPR3; DROP TABLE USERS", "owner")
