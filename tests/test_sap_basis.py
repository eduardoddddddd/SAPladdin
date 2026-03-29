"""
Tests para core/tools/sap_basis.py
Todos usan mocks — no requieren SAP real.
"""
import pytest
from unittest.mock import AsyncMock, patch
from core.tools import sap_basis
from core.tools import ssh


# ─── Fake SSH client ───────────────────────────────────────────────────────

class _FakeStdout:
    def __init__(self, payload: str, exit_code: int = 0) -> None:
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
    """Simula paramiko.SSHClient con respuestas predefinidas por keyword."""

    RESPONSES: dict[str, str] = {
        "GetSystemInstanceList": (
            "01.01.2026 10:00:00\n"
            "GetSystemInstanceList\n"
            "hostname, instanceNr, httpPort, httpsPort, startPriority, features, dispstatus\n"
            "saphost1, 00, 50013, 50014, 1, ABAP|GATEWAY|ICMAN|IGS, GREEN\n"
            "saphost1, 01, 50113, 50114, 3, MESSAGESERVER|ENQUE, GREEN\n"
        ),
        "GetProcessList": (
            "02.01.2026 09:00:00\n"
            "GetProcessList\n"
            "name, description, dispstatus, textstatus, starttime, elapsedtime, pid\n"
            "disp+work, Dispatcher, GREEN, Running, 2026/01/01 08:00:00, 3600, 1234\n"
            "igswd_mt, IGS Watchdog, GREEN, Running, 2026/01/01 08:00:00, 3600, 1235\n"
            "gwrd, Gateway, GREEN, Running, 2026/01/01 08:00:00, 3600, 1236\n"
            "icman, ICM, YELLOW, Stopping, 2026/01/01 08:00:00, 3600, 1237\n"
        ),
        "GetAlertTree": (
            "Alert Tree\n"
            "Performance, -, -, GREEN\n"
            "Availability, -, -, YELLOW\n"
        ),
        "GetVersionInfo": (
            "GetVersionInfo\n"
            "name, version, patchlevel\n"
            "kernel, 7.54, 100\n"
            "dw, 7.54, 100\n"
        ),
        "GetQueueStatistic": (
            "GetQueueStatistic\n"
            "Typ, Now, High, Max\n"
            "ABAP/BTC, 0, 2, 2000\n"
            "ABAP/DIA, 3, 10, 2000\n"
        ),
        "/usr/sap": "PRD\nDEV\nQAS\ntrans\n",
        "sapservices": "pf=/usr/sap/PRD/SYS/profile/START_DVEBMGS00_saphost1\n",
        "disp+work": "kernel release: 754\npatch level: 100\n",
        "sapcontrol_start_output": "StartService PRD\nOK\n",
        "sapcontrol_stop_output": "StopService PRD\nOK\n",
        "dev_w": "",   # no dumps by default
    }

    def exec_command(self, command: str, timeout: int = 60, get_pty: bool = False):
        for keyword, response in self.RESPONSES.items():
            if keyword in command:
                return None, _FakeStdout(response), _FakeStderr()
        return None, _FakeStdout(f"(mock: {command})\n"), _FakeStderr()


@pytest.fixture(autouse=True)
def inject_fake_ssh(monkeypatch: pytest.MonkeyPatch):
    """Inyecta el fake client en el pool SSH antes de cada test."""
    fake_pool = {"sapapp1": _FakeSSHClient()}
    monkeypatch.setattr(ssh, "_ssh_pool", fake_pool)


# ─── Tests sap_list_instances ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sap_list_instances_returns_instance_data():
    result = await sap_basis.sap_list_instances(connection="sapapp1")
    assert "DVEBMGS00" in result or "saphost1" in result or "GetSystemInstanceList" in result


@pytest.mark.asyncio
async def test_sap_list_instances_no_connection_returns_error():
    result = await sap_basis.sap_list_instances(connection="nonexistent")
    assert "No se pudo" in result or "ERROR" in result


# ─── Tests sapcontrol_get_process_list ────────────────────────────────────

@pytest.mark.asyncio
async def test_get_process_list_contains_processes():
    result = await sap_basis.sapcontrol_get_process_list(
        instance_nr="00", connection="sapapp1"
    )
    assert "disp+work" in result
    assert "gwrd" in result


# ─── Tests sap_check_work_processes ───────────────────────────────────────

@pytest.mark.asyncio
async def test_check_work_processes_counts_statuses():
    result = await sap_basis.sap_check_work_processes(
        instance_nr="00", connection="sapapp1"
    )
    assert "GREEN=3" in result
    assert "YELLOW=1" in result


@pytest.mark.asyncio
async def test_check_work_processes_includes_raw_output():
    result = await sap_basis.sap_check_work_processes(
        instance_nr="00", connection="sapapp1"
    )
    assert "disp+work" in result


# ─── Tests sap_get_alerts ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sap_get_alerts_returns_tree():
    result = await sap_basis.sap_get_alerts(
        instance_nr="00", connection="sapapp1"
    )
    assert "Alert" in result or "GREEN" in result or "YELLOW" in result


# ─── Tests sap_start_instance / sap_stop_instance ─────────────────────────

@pytest.mark.asyncio
async def test_sap_start_instance_formats_output():
    result = await sap_basis.sap_start_instance(
        instance_nr="00", sid="PRD", connection="sapapp1"
    )
    assert "PRD" in result
    assert "inst=00" in result


@pytest.mark.asyncio
async def test_sap_stop_instance_includes_sid():
    result = await sap_basis.sap_stop_instance(
        instance_nr="00", sid="DEV", connection="sapapp1"
    )
    assert "DEV" in result


@pytest.mark.asyncio
async def test_sap_start_full_system_uses_startsystem():
    result = await sap_basis.sap_start_instance(
        instance_nr="00", sid="PRD", connection="sapapp1", full_system=True
    )
    assert "StartSystem" in result


# ─── Tests sap_list_sids ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sap_list_sids_detects_usr_sap():
    result = await sap_basis.sap_list_sids(connection="sapapp1")
    assert "/usr/sap" in result or "SIDs" in result or "sapservices" in result


# ─── Tests sap_kernel_info ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sap_kernel_info_returns_version_sections():
    result = await sap_basis.sap_kernel_info(
        instance_nr="00", sid="PRD", connection="sapapp1"
    )
    assert "GetVersionInfo" in result or "disp+work" in result or "kernel" in result


# ─── Tests sap_abap_short_dumps ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_sap_abap_short_dumps_no_dumps_message():
    result = await sap_basis.sap_abap_short_dumps(
        sid="PRD", instance_nr="00", connection="sapapp1"
    )
    # Con el mock sin dumps, debería informar de "no encontrados"
    assert "dump" in result.lower() or "PRD" in result
