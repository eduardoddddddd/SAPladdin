from pathlib import Path

import pytest

from core.tools import gcloud


def _sample_instances() -> list[dict]:
    return [
        {
            "name": "abap-docker-host",
            "status": "RUNNING",
            "zone": "https://www.googleapis.com/compute/v1/projects/p/zones/europe-west1-b",
            "machineType": "https://www.googleapis.com/compute/v1/projects/p/machineTypes/e2-standard-8",
            "networkInterfaces": [
                {
                    "network": "https://www.googleapis.com/compute/v1/projects/p/global/networks/default",
                    "subnetwork": "https://www.googleapis.com/compute/v1/projects/p/regions/europe-west1/subnetworks/default",
                    "networkIP": "10.132.0.4",
                    "accessConfigs": [{"natIP": "34.79.100.46"}],
                }
            ],
            "tags": {"items": ["sap-lab", "docker"]},
            "serviceAccounts": [{"email": "sap-cal-manager@project.example.iam.gserviceaccount.com"}],
        },
        {
            "name": "codex-test-vm",
            "status": "TERMINATED",
            "zone": "https://www.googleapis.com/compute/v1/projects/p/zones/europe-west1-b",
            "machineType": "https://www.googleapis.com/compute/v1/projects/p/machineTypes/e2-micro",
            "networkInterfaces": [{"networkIP": "10.132.0.2", "accessConfigs": [{"natIP": "34.76.12.188"}]}],
            "tags": {"items": ["ssh-only"]},
            "serviceAccounts": [],
        },
    ]


def _sample_firewalls() -> list[dict]:
    return [
        {
            "name": "default-allow-ssh",
            "network": "https://www.googleapis.com/compute/v1/projects/p/global/networks/default",
            "direction": "INGRESS",
            "priority": 1000,
            "sourceRanges": ["0.0.0.0/0"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["22"]}],
        },
        {
            "name": "allow-sap-docker",
            "network": "https://www.googleapis.com/compute/v1/projects/p/global/networks/default",
            "direction": "INGRESS",
            "priority": 1000,
            "sourceRanges": ["0.0.0.0/0"],
            "targetTags": ["sap-lab"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["3200", "50000"]}],
        },
    ]


def test_load_gcloud_config_reads_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "gcloud_config.yaml"
    cfg_path.write_text(
        "gcloud:\n"
        "  project: proj-test\n"
        "  default_zone: europe-west1-b\n"
        "  ssh_user: Edu\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gcloud, "_CONFIG_PATH", cfg_path)

    cfg = gcloud._load_gcloud_config()

    assert cfg["project"] == "proj-test"
    assert cfg["default_zone"] == "europe-west1-b"
    assert cfg["ssh_user"] == "Edu"


@pytest.mark.asyncio
async def test_gcloud_set_defaults_writes_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "gcloud_config.yaml"
    monkeypatch.setattr(gcloud, "_CONFIG_PATH", cfg_path)

    result = await gcloud.gcloud_set_defaults(
        project="project-123",
        default_zone="europe-west1-b",
        ssh_user="Edu",
    )

    saved = cfg_path.read_text(encoding="utf-8")
    assert "project-123" in saved
    assert "europe-west1-b" in saved
    assert "ssh_user=Edu" in result


@pytest.mark.asyncio
async def test_gcloud_list_instances_filters_by_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gcloud, "_load_gcloud_config", lambda: {"project": "proj", "command_timeout_seconds": 30})

    async def fake_run_json(args, *, project, cfg, timeout_seconds=None):
        del args, cfg, timeout_seconds
        assert project == "proj"
        return _sample_instances()

    monkeypatch.setattr(gcloud, "_run_gcloud_json", fake_run_json)

    result = await gcloud.gcloud_list_instances(status_filter="RUNNING")

    assert "abap-docker-host" in result
    assert "codex-test-vm" not in result


def test_firewall_match_and_port_logic() -> None:
    instance = gcloud._extract_instance_summary(_sample_instances()[0])
    ssh_rule, sap_rule = _sample_firewalls()

    assert gcloud._firewall_targets_match(ssh_rule, instance) is True
    assert gcloud._firewall_targets_match(sap_rule, instance) is True
    assert gcloud._firewall_allows_port(ssh_rule, 22) is True
    assert gcloud._firewall_allows_port(sap_rule, 50000) is True
    assert gcloud._firewall_allows_port(sap_rule, 22) is False


@pytest.mark.asyncio
async def test_gcloud_check_ssh_access_reports_open_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gcloud, "_load_gcloud_config", lambda: {"project": "proj", "command_timeout_seconds": 30})

    async def fake_find(name, zone, project, cfg):
        del name, zone, project, cfg
        return _sample_instances()[0]

    async def fake_firewalls(project, cfg):
        del project, cfg
        return _sample_firewalls()

    monkeypatch.setattr(gcloud, "_find_instance", fake_find)
    monkeypatch.setattr(gcloud, "_list_firewall_rules", fake_firewalls)
    monkeypatch.setattr(gcloud, "_tcp_check", lambda host, port: (True, "ABIERTO"))

    result = await gcloud.gcloud_check_ssh_access("abap-docker-host")

    assert "ABIERTO" in result
    assert "default-allow-ssh" in result


@pytest.mark.asyncio
async def test_gcloud_network_report_flags_closed_sap_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gcloud, "_load_gcloud_config", lambda: {"project": "proj", "command_timeout_seconds": 30})

    async def fake_find(name, zone, project, cfg):
        del name, zone, project, cfg
        return _sample_instances()[0]

    async def fake_firewalls(project, cfg):
        del project, cfg
        return _sample_firewalls()

    def fake_tcp(host: str, port: int) -> tuple[bool, str]:
        del host
        return (port == 22, "ABIERTO" if port == 22 else "Connection refused")

    monkeypatch.setattr(gcloud, "_find_instance", fake_find)
    monkeypatch.setattr(gcloud, "_list_firewall_rules", fake_firewalls)
    monkeypatch.setattr(gcloud, "_tcp_check", fake_tcp)

    result = await gcloud.gcloud_instance_network_report("abap-docker-host")

    assert "22/tcp -> ABIERTO" in result
    assert "3200/tcp -> CERRADO" in result
    assert "ip_forward" in result


@pytest.mark.asyncio
async def test_gcloud_export_instance_to_host_adds_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gcloud,
        "_load_gcloud_config",
        lambda: {"project": "proj", "ssh_user": "Edu", "command_timeout_seconds": 30},
    )

    async def fake_find(name, zone, project, cfg):
        del name, zone, project, cfg
        return _sample_instances()[0]

    saved = {}

    monkeypatch.setattr(gcloud, "_find_instance", fake_find)
    monkeypatch.setattr(gcloud, "_load_hosts", lambda: [])
    monkeypatch.setattr(gcloud, "_save_hosts", lambda items: saved.setdefault("hosts", items))

    result = await gcloud.gcloud_export_instance_to_host(
        "abap-docker-host",
        alias="a4hgcp",
        key_path="C:/Users/Edu/.ssh/google_compute_engine",
    )

    assert "a4hgcp" in result
    assert saved["hosts"][0]["alias"] == "a4hgcp"
    assert saved["hosts"][0]["ip"] == "34.79.100.46"
    assert saved["hosts"][0]["gcp_instance"] == "abap-docker-host"
