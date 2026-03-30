"""
SAPladdin - Google Cloud operational tools built on top of gcloud CLI.
"""

import asyncio
import json
import logging
import os
import re
import socket
from pathlib import Path
from typing import Annotated, Any

import yaml

from core.hosts import _load_hosts, _save_hosts
from core.tools.utils import build_subprocess_env

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "gcloud_config.yaml"
_DEFAULT_TIMEOUT = 60


def _default_gcloud_bin() -> str:
    return "gcloud.cmd" if os.name == "nt" else "gcloud"


def _fallback_gcloud_paths() -> list[Path]:
    if os.name != "nt":
        return []
    return [
        Path.home() / "AppData" / "Local" / "Google" / "Cloud SDK" / "google-cloud-sdk" / "bin" / "gcloud.cmd",
    ]


def _resolve_gcloud_bin(configured: str) -> str:
    if configured:
        path = Path(configured)
        if path.exists():
            return str(path)
        return configured
    for candidate in _fallback_gcloud_paths():
        if candidate.exists():
            return str(candidate)
    return _default_gcloud_bin()


def _default_config() -> dict[str, Any]:
    return {
        "project": "",
        "default_zone": "",
        "default_region": "",
        "ssh_user": "",
        "service_account_key_file": "",
        "gcloud_bin": _resolve_gcloud_bin(""),
        "command_timeout_seconds": _DEFAULT_TIMEOUT,
    }


def _load_gcloud_config() -> dict[str, Any]:
    cfg = _default_config()
    env_map = {
        "GOOGLE_CLOUD_PROJECT": "project",
        "GCP_PROJECT": "project",
        "GCLOUD_DEFAULT_ZONE": "default_zone",
        "GCLOUD_DEFAULT_REGION": "default_region",
        "GCLOUD_SSH_USER": "ssh_user",
        "GOOGLE_APPLICATION_CREDENTIALS": "service_account_key_file",
        "GCLOUD_BIN": "gcloud_bin",
    }
    for env_key, cfg_key in env_map.items():
        value = os.environ.get(env_key)
        if value:
            cfg[cfg_key] = value

    timeout_env = os.environ.get("GCLOUD_COMMAND_TIMEOUT_SECONDS")
    if timeout_env and timeout_env.isdigit():
        cfg["command_timeout_seconds"] = int(timeout_env)

    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
                file_cfg = yaml.safe_load(fh) or {}
            section = file_cfg.get("gcloud", {})
            for key, value in section.items():
                if key in cfg and value not in ("", None):
                    cfg[key] = value
        except Exception as exc:
            logger.warning("Could not load gcloud config from %s: %s", _CONFIG_PATH, exc)
    return cfg


def _save_gcloud_config(cfg: dict[str, Any]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
        yaml.safe_dump({"gcloud": cfg}, fh, sort_keys=False, allow_unicode=True)


def _safe_name(value: str, label: str) -> str:
    item = value.strip()
    if not item:
        raise ValueError(f"{label} vacío.")
    if not re.fullmatch(r"[a-z]([-a-z0-9]*[a-z0-9])?", item):
        raise ValueError(
            f"{label} inválido: {value!r}. Debe cumplir naming de GCE "
            "(minúsculas, números y guiones)."
        )
    return item


def _safe_csv_items(value: str, label: str) -> list[str]:
    items = []
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", item):
            raise ValueError(f"{label} contiene valor no permitido: {item!r}")
        items.append(item)
    return items


def _normalize_project(project: str, cfg: dict[str, Any]) -> str:
    chosen = (project or cfg.get("project") or "").strip()
    if not chosen:
        raise RuntimeError(
            "No se indicó project y no hay project configurado en config/gcloud_config.yaml."
        )
    return chosen


def _normalize_zone(zone: str, cfg: dict[str, Any]) -> str:
    chosen = (zone or cfg.get("default_zone") or "").strip()
    if not chosen:
        raise RuntimeError(
            "No se indicó zone y no hay default_zone configurada en config/gcloud_config.yaml."
        )
    return chosen


def _short_resource_name(value: str) -> str:
    return value.rsplit("/", 1)[-1] if value else ""


def _mask_path(value: str) -> str:
    if not value:
        return "(no configurado)"
    path = Path(value)
    return str(path.parent / path.name)


def _gcloud_env(cfg: dict[str, Any], project: str) -> dict[str, str]:
    env: dict[str, str] = {
        "CLOUDSDK_CORE_DISABLE_PROMPTS": "1",
        "CLOUDSDK_CORE_PROJECT": project,
        "GOOGLE_CLOUD_PROJECT": project,
    }
    key_file = cfg.get("service_account_key_file", "")
    if key_file:
        env["GOOGLE_APPLICATION_CREDENTIALS"] = key_file
        env["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] = key_file
    return env


async def _run_gcloud(
    args: list[str],
    *,
    project: str,
    cfg: dict[str, Any],
    timeout_seconds: int | None = None,
) -> str:
    binary = _resolve_gcloud_bin(cfg.get("gcloud_bin", ""))
    timeout = timeout_seconds or int(cfg.get("command_timeout_seconds") or _DEFAULT_TIMEOUT)
    env = build_subprocess_env(_gcloud_env(cfg, project))
    logger.info("gcloud command: %s %s", binary, " ".join(args))

    try:
        proc = await asyncio.create_subprocess_exec(
            binary,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            cwd=str(_PROJECT_ROOT),
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"No se encontró gcloud ({binary}). Ajusta gcloud_bin en config/gcloud_config.yaml."
        ) from exc

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(f"gcloud excedió timeout de {timeout}s.")

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        raise RuntimeError(stderr or stdout or f"gcloud exit code {proc.returncode}")
    return stdout


async def _run_gcloud_json(
    args: list[str],
    *,
    project: str,
    cfg: dict[str, Any],
    timeout_seconds: int | None = None,
) -> Any:
    raw = await _run_gcloud(
        [*args, "--format=json"],
        project=project,
        cfg=cfg,
        timeout_seconds=timeout_seconds,
    )
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gcloud devolvió JSON inválido: {exc}\n\n{raw[:1000]}") from exc


def _extract_instance_summary(item: dict[str, Any]) -> dict[str, Any]:
    nic = (item.get("networkInterfaces") or [{}])[0]
    access_configs = nic.get("accessConfigs") or [{}]
    primary_access = access_configs[0] if access_configs else {}
    return {
        "name": item.get("name", ""),
        "status": item.get("status", ""),
        "zone": _short_resource_name(item.get("zone", "")),
        "machine_type": _short_resource_name(item.get("machineType", "")),
        "internal_ip": nic.get("networkIP", ""),
        "external_ip": primary_access.get("natIP", ""),
        "network": _short_resource_name(nic.get("network", "")),
        "subnetwork": _short_resource_name(nic.get("subnetwork", "")),
        "tags": item.get("tags", {}).get("items", []) or [],
        "service_accounts": [
            sa.get("email", "") for sa in item.get("serviceAccounts", []) if sa.get("email")
        ],
    }


def _render_instance_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No hay instancias que cumplan el filtro."
    lines = [f"Instancias Google Cloud ({len(items)}):", "=" * 100]
    for item in items:
        summary = _extract_instance_summary(item)
        tags = ",".join(summary["tags"]) if summary["tags"] else "-"
        lines.append(
            f"{summary['name']:<22} {summary['status']:<12} {summary['zone']:<16} "
            f"{summary['machine_type']:<18} ext={summary['external_ip'] or '-':<15} "
            f"int={summary['internal_ip'] or '-':<15} tags={tags}"
        )
    return "\n".join(lines)


async def _find_instance(name: str, zone: str, project: str, cfg: dict[str, Any]) -> dict[str, Any]:
    safe_name = _safe_name(name, "instance_name")
    items = await _run_gcloud_json(["compute", "instances", "list"], project=project, cfg=cfg)
    matches = [item for item in items if item.get("name") == safe_name]
    if zone:
        matches = [item for item in matches if _short_resource_name(item.get("zone", "")) == zone]
    if not matches:
        scope = f" en zone {zone}" if zone else ""
        raise RuntimeError(f"No se encontró la VM '{safe_name}'{scope} en el proyecto {project}.")
    if len(matches) > 1 and not zone:
        zones = sorted({_short_resource_name(item.get("zone", "")) for item in matches})
        raise RuntimeError(
            f"La VM '{safe_name}' existe en varias zonas {zones}. Indica zone explícitamente."
        )
    return matches[0]


def _firewall_targets_match(rule: dict[str, Any], instance: dict[str, Any]) -> bool:
    instance_tags = set(instance.get("tags", []))
    instance_sas = set(instance.get("service_accounts", []))
    target_tags = set(rule.get("targetTags", []) or [])
    target_sas = set(rule.get("targetServiceAccounts", []) or [])
    if target_tags and not (target_tags & instance_tags):
        return False
    if target_sas and not (target_sas & instance_sas):
        return False
    return True


def _firewall_allows_port(rule: dict[str, Any], port: int) -> bool:
    if rule.get("direction") != "INGRESS":
        return False
    for allowed in rule.get("allowed", []) or []:
        protocol = (allowed.get("IPProtocol") or "").lower()
        ports = allowed.get("ports", [])
        if protocol == "all":
            return True
        if protocol != "tcp":
            continue
        if not ports:
            return True
        for spec in ports:
            if "-" in spec:
                start, end = spec.split("-", 1)
                if start.isdigit() and end.isdigit() and int(start) <= port <= int(end):
                    return True
            elif spec.isdigit() and int(spec) == port:
                return True
    return False


def _render_firewall_rule(rule: dict[str, Any]) -> str:
    allowed_parts = []
    for allowed in rule.get("allowed", []) or []:
        proto = allowed.get("IPProtocol", "?")
        ports = ",".join(allowed.get("ports", []) or [])
        allowed_parts.append(f"{proto}:{ports}" if ports else proto)
    source_ranges = ",".join(rule.get("sourceRanges", []) or []) or "-"
    target_tags = ",".join(rule.get("targetTags", []) or []) or "*"
    target_sas = ",".join(rule.get("targetServiceAccounts", []) or []) or "*"
    return (
        f"{rule.get('name', '?')}  dir={rule.get('direction', '?')}  "
        f"prio={rule.get('priority', '?')}  allow={'; '.join(allowed_parts) or '-'}  "
        f"src={source_ranges}  target_tags={target_tags}  target_sa={target_sas}"
    )


async def _list_firewall_rules(project: str, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    return await _run_gcloud_json(
        ["compute", "firewall-rules", "list"],
        project=project,
        cfg=cfg,
    )


def _tcp_check(host: str, port: int, timeout_seconds: float = 4.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True, "ABIERTO"
    except TimeoutError:
        return False, "TIMEOUT"
    except OSError as exc:
        return False, str(exc)


async def gcloud_get_config() -> str:
    """Muestra la configuración efectiva de Google Cloud usada por SAPladdin."""
    cfg = _load_gcloud_config()
    project = cfg.get("project") or "(no configurado)"
    zone = cfg.get("default_zone") or "(no configurada)"
    region = cfg.get("default_region") or "(no configurada)"
    ssh_user = cfg.get("ssh_user") or "(no configurado)"
    key_file = cfg.get("service_account_key_file", "")
    key_exists = Path(key_file).exists() if key_file else False

    lines = [
        "Google Cloud config efectiva",
        "=" * 40,
        f"project:                   {project}",
        f"default_zone:              {zone}",
        f"default_region:            {region}",
        f"ssh_user:                  {ssh_user}",
        f"gcloud_bin:                {_resolve_gcloud_bin(cfg.get('gcloud_bin', ''))}",
        f"command_timeout_seconds:   {cfg.get('command_timeout_seconds')}",
        f"service_account_key_file:  {_mask_path(key_file)}",
        f"key_file_exists:           {key_exists}",
    ]

    if project != "(no configurado)":
        try:
            active_project = await _run_gcloud(
                ["config", "get-value", "project"],
                project=project,
                cfg=cfg,
                timeout_seconds=20,
            )
            lines.append(f"gcloud active project:      {active_project.strip()}")
        except Exception as exc:
            lines.append(f"gcloud active project:      [error] {exc}")
    return "\n".join(lines)


async def gcloud_set_defaults(
    project: Annotated[str, "Proyecto por defecto de GCP. Vacío = no cambiar."] = "",
    default_zone: Annotated[str, "Zona por defecto. Ej: europe-west1-b."] = "",
    default_region: Annotated[str, "Región por defecto. Ej: europe-west1."] = "",
    ssh_user: Annotated[str, "Usuario SSH habitual para las VMs."] = "",
    service_account_key_file: Annotated[str, "Ruta al JSON de la service account."] = "",
    gcloud_bin: Annotated[str, "Ruta o comando de gcloud/gcloud.cmd."] = "",
    command_timeout_seconds: Annotated[int, "Timeout por defecto para gcloud."] = 0,
) -> str:
    """Guarda defaults de Google Cloud en config/gcloud_config.yaml."""
    cfg = _load_gcloud_config()
    changed = []

    updates = {
        "project": project.strip(),
        "default_zone": default_zone.strip(),
        "default_region": default_region.strip(),
        "ssh_user": ssh_user.strip(),
        "service_account_key_file": service_account_key_file.strip(),
        "gcloud_bin": gcloud_bin.strip(),
    }
    for key, value in updates.items():
        if value:
            cfg[key] = value
            changed.append(f"{key}={value}")
    if command_timeout_seconds > 0:
        cfg["command_timeout_seconds"] = command_timeout_seconds
        changed.append(f"command_timeout_seconds={command_timeout_seconds}")

    if not changed:
        return (
            "No se aplicaron cambios. Pasa al menos un valor para actualizar "
            "config/gcloud_config.yaml."
        )

    _save_gcloud_config(cfg)
    return (
        "✓ Configuración Google Cloud actualizada en config/gcloud_config.yaml\n"
        + "\n".join(f"  - {item}" for item in changed)
    )


async def gcloud_list_instances(
    status_filter: Annotated[str, "Filtrar por estado: RUNNING, TERMINATED, etc. Vacío = todos."] = "",
    zone: Annotated[str, "Zona concreta. Vacío = todas las visibles en el proyecto."] = "",
    name_filter: Annotated[str, "Subcadena del nombre de VM. Vacío = todas."] = "",
    project: Annotated[str, "Proyecto GCP. Vacío = usar config."] = "",
) -> str:
    """Lista instancias del proyecto GCP con datos operativos relevantes."""
    cfg = _load_gcloud_config()
    effective_project = _normalize_project(project, cfg)
    items = await _run_gcloud_json(["compute", "instances", "list"], project=effective_project, cfg=cfg)

    wanted_status = status_filter.strip().upper()
    wanted_zone = zone.strip()
    wanted_name = name_filter.strip().lower()
    filtered = []
    for item in items:
        summary = _extract_instance_summary(item)
        if wanted_status and summary["status"].upper() != wanted_status:
            continue
        if wanted_zone and summary["zone"] != wanted_zone:
            continue
        if wanted_name and wanted_name not in summary["name"].lower():
            continue
        filtered.append(item)
    return f"Proyecto: {effective_project}\n{_render_instance_table(filtered)}"


async def gcloud_describe_instance(
    instance_name: Annotated[str, "Nombre de la VM."],
    zone: Annotated[str, "Zona de la VM. Vacío = auto-resolver si es única."] = "",
    project: Annotated[str, "Proyecto GCP. Vacío = usar config."] = "",
) -> str:
    """Describe una VM con foco en operación, red, tags y service accounts."""
    cfg = _load_gcloud_config()
    effective_project = _normalize_project(project, cfg)
    resolved = await _find_instance(instance_name, zone.strip(), effective_project, cfg)
    summary = _extract_instance_summary(resolved)

    disks = [
        f"{_short_resource_name(disk.get('source', ''))}:{disk.get('boot', False)}:{disk.get('mode', '')}"
        for disk in resolved.get("disks", [])
    ]
    labels = resolved.get("labels", {})
    metadata_items = resolved.get("metadata", {}).get("items", []) or []
    metadata_pairs = [f"{item.get('key')}={item.get('value', '')}" for item in metadata_items[:10]]

    lines = [
        f"VM: {summary['name']}",
        "=" * 60,
        f"project:           {effective_project}",
        f"zone:              {summary['zone']}",
        f"status:            {summary['status']}",
        f"machine_type:      {summary['machine_type']}",
        f"network:           {summary['network']}",
        f"subnetwork:        {summary['subnetwork']}",
        f"internal_ip:       {summary['internal_ip'] or '-'}",
        f"external_ip:       {summary['external_ip'] or '-'}",
        f"tags:              {', '.join(summary['tags']) if summary['tags'] else '-'}",
        f"service_accounts:  {', '.join(summary['service_accounts']) if summary['service_accounts'] else '-'}",
        f"disks:             {', '.join(disks) if disks else '-'}",
        f"labels:            {labels if labels else '-'}",
        f"scheduling:        {resolved.get('scheduling', {}) or '-'}",
    ]
    if metadata_pairs:
        lines.append("metadata:")
        lines.extend(f"  - {pair}" for pair in metadata_pairs)
    return "\n".join(lines)


async def gcloud_start_instance(
    instance_name: Annotated[str, "Nombre de la VM a arrancar."],
    zone: Annotated[str, "Zona. Vacío = usar default_zone o resolver."] = "",
    project: Annotated[str, "Proyecto GCP. Vacío = usar config."] = "",
) -> str:
    """Arranca una VM de Google Compute Engine."""
    cfg = _load_gcloud_config()
    effective_project = _normalize_project(project, cfg)
    resolved = await _find_instance(instance_name, zone.strip(), effective_project, cfg)
    resolved_zone = _short_resource_name(resolved.get("zone", ""))
    output = await _run_gcloud(
        ["compute", "instances", "start", instance_name, "--zone", resolved_zone],
        project=effective_project,
        cfg=cfg,
        timeout_seconds=180,
    )
    latest = await _find_instance(instance_name, resolved_zone, effective_project, cfg)
    summary = _extract_instance_summary(latest)
    return (
        f"✓ VM arrancada: {summary['name']}\n"
        f"  project: {effective_project}\n"
        f"  zone:    {summary['zone']}\n"
        f"  status:  {summary['status']}\n"
        f"  ext_ip:  {summary['external_ip'] or '-'}\n"
        f"  int_ip:  {summary['internal_ip'] or '-'}\n\n"
        f"Salida gcloud:\n{output}"
    )


async def gcloud_stop_instance(
    instance_name: Annotated[str, "Nombre de la VM a detener."],
    zone: Annotated[str, "Zona. Vacío = usar default_zone o resolver."] = "",
    project: Annotated[str, "Proyecto GCP. Vacío = usar config."] = "",
) -> str:
    """Detiene una VM de Google Compute Engine."""
    cfg = _load_gcloud_config()
    effective_project = _normalize_project(project, cfg)
    resolved = await _find_instance(instance_name, zone.strip(), effective_project, cfg)
    resolved_zone = _short_resource_name(resolved.get("zone", ""))
    output = await _run_gcloud(
        ["compute", "instances", "stop", instance_name, "--zone", resolved_zone],
        project=effective_project,
        cfg=cfg,
        timeout_seconds=180,
    )
    latest = await _find_instance(instance_name, resolved_zone, effective_project, cfg)
    summary = _extract_instance_summary(latest)
    return (
        f"✓ VM detenida: {summary['name']}\n"
        f"  project: {effective_project}\n"
        f"  zone:    {summary['zone']}\n"
        f"  status:  {summary['status']}\n\n"
        f"Salida gcloud:\n{output}"
    )


async def gcloud_create_instance(
    instance_name: Annotated[str, "Nombre de la VM a crear."],
    machine_type: Annotated[str, "Machine type. Ej: e2-micro, e2-standard-8."] = "e2-micro",
    zone: Annotated[str, "Zona. Vacío = usar default_zone."] = "",
    image_family: Annotated[str, "Image family. Ej: debian-12, ubuntu-2204-lts, sles-12-sp5-sap."] = "debian-12",
    image_project: Annotated[str, "Proyecto de la imagen. Ej: debian-cloud."] = "debian-cloud",
    boot_disk_size_gb: Annotated[int, "Tamaño del disco raíz en GB."] = 10,
    boot_disk_type: Annotated[str, "Tipo de disco. Ej: pd-standard, pd-ssd."] = "pd-standard",
    network: Annotated[str, "Red VPC. Default: default."] = "default",
    subnet: Annotated[str, "Subred. Vacío = dejar que GCP resuelva."] = "",
    tags: Annotated[str, "Tags de red separados por coma."] = "",
    project: Annotated[str, "Proyecto GCP. Vacío = usar config."] = "",
) -> str:
    """Crea una VM útil para laboratorio/operación real mediante gcloud."""
    cfg = _load_gcloud_config()
    effective_project = _normalize_project(project, cfg)
    resolved_zone = _normalize_zone(zone, cfg)
    safe_name = _safe_name(instance_name, "instance_name")
    safe_tags = _safe_csv_items(tags, "tags")

    args = [
        "compute",
        "instances",
        "create",
        safe_name,
        "--zone",
        resolved_zone,
        "--machine-type",
        machine_type.strip(),
        "--image-family",
        image_family.strip(),
        "--image-project",
        image_project.strip(),
        "--boot-disk-size",
        f"{boot_disk_size_gb}GB",
        "--boot-disk-type",
        boot_disk_type.strip(),
        "--network",
        network.strip(),
    ]
    if subnet.strip():
        args.extend(["--subnet", subnet.strip()])
    if safe_tags:
        args.extend(["--tags", ",".join(safe_tags)])

    output = await _run_gcloud(args, project=effective_project, cfg=cfg, timeout_seconds=300)
    created = await _find_instance(safe_name, resolved_zone, effective_project, cfg)
    summary = _extract_instance_summary(created)
    return (
        f"✓ VM creada: {summary['name']}\n"
        f"  project:      {effective_project}\n"
        f"  zone:         {summary['zone']}\n"
        f"  status:       {summary['status']}\n"
        f"  machine_type: {summary['machine_type']}\n"
        f"  external_ip:  {summary['external_ip'] or '-'}\n"
        f"  internal_ip:  {summary['internal_ip'] or '-'}\n"
        f"  tags:         {', '.join(summary['tags']) if summary['tags'] else '-'}\n\n"
        f"Salida gcloud:\n{output}"
    )


async def gcloud_list_firewall_rules(
    network: Annotated[str, "Filtrar por red VPC. Vacío = todas."] = "",
    target_tag: Annotated[str, "Filtrar por target tag. Vacío = todos."] = "",
    port: Annotated[int, "Filtrar reglas que permiten este puerto TCP. 0 = todas."] = 0,
    project: Annotated[str, "Proyecto GCP. Vacío = usar config."] = "",
) -> str:
    """Lista reglas de firewall de GCP con foco en conectividad operativa."""
    cfg = _load_gcloud_config()
    effective_project = _normalize_project(project, cfg)
    rules = await _list_firewall_rules(effective_project, cfg)

    filtered = []
    for rule in rules:
        if network and _short_resource_name(rule.get("network", "")) != network.strip():
            continue
        if target_tag and target_tag.strip() not in (rule.get("targetTags", []) or []):
            continue
        if port > 0 and not _firewall_allows_port(rule, port):
            continue
        filtered.append(rule)

    if not filtered:
        return f"No hay firewall rules con esos filtros en el proyecto {effective_project}."
    lines = [f"Firewall rules ({len(filtered)}) - project {effective_project}", "=" * 110]
    for rule in filtered:
        lines.append(_render_firewall_rule(rule))
    return "\n".join(lines)


async def gcloud_check_ssh_access(
    instance_name: Annotated[str, "Nombre de la VM."],
    zone: Annotated[str, "Zona. Vacío = auto-resolver si es única."] = "",
    port: Annotated[int, "Puerto SSH/TCP a validar. Default 22."] = 22,
    project: Annotated[str, "Proyecto GCP. Vacío = usar config."] = "",
) -> str:
    """Valida acceso SSH/TCP a una VM y correlaciona IP, estado y firewall."""
    cfg = _load_gcloud_config()
    effective_project = _normalize_project(project, cfg)
    resolved = await _find_instance(instance_name, zone.strip(), effective_project, cfg)
    summary = _extract_instance_summary(resolved)
    rules = await _list_firewall_rules(effective_project, cfg)

    if summary["status"] != "RUNNING":
        return (
            f"VM {summary['name']} no está RUNNING.\n"
            f"  status: {summary['status']}\n"
            f"  zone:   {summary['zone']}\n"
            f"  ext_ip: {summary['external_ip'] or '-'}\n"
            "Arráncala antes de validar SSH."
        )
    if not summary["external_ip"]:
        return (
            f"VM {summary['name']} no tiene IP pública.\n"
            f"  zone: {summary['zone']}\n"
            "Sin IP pública no hay SSH directo desde internet salvo túnel/bastion/VPN."
        )

    applicable = [
        rule for rule in rules
        if _short_resource_name(rule.get("network", "")) == summary["network"]
        and _firewall_targets_match(rule, summary)
    ]
    matching_port = [rule for rule in applicable if _firewall_allows_port(rule, port)]
    tcp_ok, tcp_detail = _tcp_check(summary["external_ip"], port)

    lines = [
        f"SSH/TCP check for {summary['name']}",
        "=" * 60,
        f"project:        {effective_project}",
        f"zone:           {summary['zone']}",
        f"status:         {summary['status']}",
        f"external_ip:    {summary['external_ip']}",
        f"internal_ip:    {summary['internal_ip'] or '-'}",
        f"network:        {summary['network']}",
        f"tags:           {', '.join(summary['tags']) if summary['tags'] else '-'}",
        f"port_check:     {port}/tcp -> {'ABIERTO' if tcp_ok else 'CERRADO'} ({tcp_detail})",
        f"firewall_rules: {len(matching_port)} regla(s) parecen permitir {port}/tcp",
    ]
    if matching_port:
        lines.append("")
        lines.append("Reglas candidatas:")
        lines.extend(f"  - {rule.get('name')}" for rule in matching_port[:8])
    else:
        lines.append("")
        lines.append(
            "No se encontró una firewall rule candidata para ese puerto. "
            "Revisa target tags, target service accounts y source ranges."
        )

    lines.append("")
    lines.append("Runbook rápido:")
    if not tcp_ok and matching_port:
        lines.append("  1. El firewall GCP parece permitir el puerto; revisar servicio escuchando dentro de la VM.")
        lines.append("  2. Validar SSH/daemon o, si es Docker, revisar forwarding y publicación de puertos.")
    elif not tcp_ok and not matching_port:
        lines.append("  1. Crear o ajustar firewall rule para abrir el puerto al tag correcto.")
        lines.append("  2. Confirmar que la VM tiene el tag esperado y una IP pública asignada.")
    else:
        lines.append("  1. El puerto responde desde local. Si falla ssh, revisar usuario, clave y OS Login.")
        lines.append("  2. Si el caso es Docker/SAP, el problema ya no parece de firewall básico.")
    return "\n".join(lines)


async def gcloud_instance_network_report(
    instance_name: Annotated[str, "Nombre de la VM."],
    zone: Annotated[str, "Zona. Vacío = auto-resolver si es única."] = "",
    ports: Annotated[str, "Puertos TCP a validar. Ej: 22,3200,50000"] = "22,3200,50000",
    project: Annotated[str, "Proyecto GCP. Vacío = usar config."] = "",
) -> str:
    """Genera un informe operativo de red para una VM, pensando en SSH/SAP/Docker."""
    cfg = _load_gcloud_config()
    effective_project = _normalize_project(project, cfg)
    resolved = await _find_instance(instance_name, zone.strip(), effective_project, cfg)
    summary = _extract_instance_summary(resolved)
    rules = await _list_firewall_rules(effective_project, cfg)
    applicable = [
        rule for rule in rules
        if _short_resource_name(rule.get("network", "")) == summary["network"]
        and _firewall_targets_match(rule, summary)
    ]

    checked_ports = [int(raw.strip()) for raw in ports.split(",") if raw.strip().isdigit()]
    if not checked_ports:
        checked_ports = [22, 3200, 50000]

    lines = [
        f"Network report: {summary['name']}",
        "=" * 70,
        f"project:         {effective_project}",
        f"status:          {summary['status']}",
        f"zone:            {summary['zone']}",
        f"machine_type:    {summary['machine_type']}",
        f"network:         {summary['network']}",
        f"subnetwork:      {summary['subnetwork']}",
        f"internal_ip:     {summary['internal_ip'] or '-'}",
        f"external_ip:     {summary['external_ip'] or '-'}",
        f"tags:            {', '.join(summary['tags']) if summary['tags'] else '-'}",
        f"service_account: {', '.join(summary['service_accounts']) if summary['service_accounts'] else '-'}",
        "",
        f"Firewall rules aplicables: {len(applicable)}",
    ]
    for rule in applicable[:12]:
        lines.append(f"  - {_render_firewall_rule(rule)}")

    lines.append("")
    lines.append("Comprobación TCP desde el equipo local:")
    if summary["status"] != "RUNNING":
        lines.append("  - VM no está RUNNING; no se ejecutan checks TCP.")
    elif not summary["external_ip"]:
        lines.append("  - VM sin IP pública; no se ejecutan checks TCP.")
    else:
        for port in checked_ports:
            tcp_ok, tcp_detail = _tcp_check(summary["external_ip"], port)
            fw_ok = any(_firewall_allows_port(rule, port) for rule in applicable)
            lines.append(
                f"  - {port}/tcp -> {'ABIERTO' if tcp_ok else 'CERRADO'} "
                f"(firewall={'sí' if fw_ok else 'no'}, detalle={tcp_detail})"
            )

    lines.append("")
    lines.append("Interpretación operativa:")
    lines.append(
        "  - firewall=yes + puerto cerrado suele apuntar a servicio caído, bind incorrecto o forwarding local roto."
    )
    lines.append(
        "  - En hosts Docker sobre GCE, si los SYN llegan pero el puerto no responde, revisar net.ipv4.ip_forward y reglas NAT."
    )
    lines.append(
        "  - Si 22 abre y 3200/50000 no, el problema ya no es acceso básico a la VM sino publicación del servicio."
    )
    return "\n".join(lines)


async def gcloud_export_instance_to_host(
    instance_name: Annotated[str, "Nombre de la VM de GCP."],
    alias: Annotated[str, "Alias a guardar en hosts.yaml. Vacío = usar el nombre de la VM."] = "",
    zone: Annotated[str, "Zona. Vacío = auto-resolver si es única."] = "",
    project: Annotated[str, "Proyecto GCP. Vacío = usar config."] = "",
    host_type: Annotated[str, "Tipo a registrar en hosts.yaml. Default linux_ssh."] = "linux_ssh",
    prefer_public_ip: Annotated[bool, "True = guardar IP pública si existe. False = IP interna."] = True,
    user: Annotated[str, "Usuario SSH a persistir. Vacío = usar ssh_user de gcloud config."] = "",
    key_path: Annotated[str, "Ruta a la clave SSH. Vacío = no guardar key_path."] = "",
    tags: Annotated[str, "Tags extra para hosts.yaml, separados por coma."] = "gcp",
    overwrite: Annotated[bool, "True = actualizar entrada existente con el mismo alias."] = False,
) -> str:
    """Exporta una VM de Google Cloud al inventario hosts.yaml para reutilizar SSH/SAP tools."""
    cfg = _load_gcloud_config()
    effective_project = _normalize_project(project, cfg)
    resolved = await _find_instance(instance_name, zone.strip(), effective_project, cfg)
    summary = _extract_instance_summary(resolved)

    effective_alias = (alias or summary["name"]).strip()
    if not effective_alias:
        return "Alias vacío. Indica alias o usa un instance_name válido."
    if host_type not in ("linux_ssh", "windows_ssh"):
        return "host_type inválido. Usa linux_ssh o windows_ssh."

    used_internal_fallback = bool(prefer_public_ip and not summary["external_ip"] and summary["internal_ip"])
    selected_ip = summary["external_ip"] if prefer_public_ip and summary["external_ip"] else summary["internal_ip"]
    if not selected_ip:
        return (
            f"No se pudo determinar IP para {summary['name']}.\n"
            "La VM no tiene IP pública ni interna usable en la respuesta de gcloud."
        )

    hosts = _load_hosts()
    combined_tags = []
    existing_tags = summary["tags"] or []
    extra_tags = _safe_csv_items(tags, "tags") if tags.strip() else []
    for tag in [*existing_tags, *extra_tags, "gcp", summary["zone"]]:
        if tag and tag not in combined_tags:
            combined_tags.append(tag)

    record = {
        "name": summary["name"],
        "alias": effective_alias,
        "type": host_type,
        "ip": selected_ip,
        "port": 22,
        "user": (user or cfg.get("ssh_user") or "").strip(),
        "tags": combined_tags,
        "description": (
            f"GCP VM exportada desde proyecto {effective_project} "
            f"(zone={summary['zone']}, machine_type={summary['machine_type']})"
        ),
        "gcp_project": effective_project,
        "gcp_zone": summary["zone"],
        "gcp_instance": summary["name"],
        "gcp_machine_type": summary["machine_type"],
        "gcp_network": summary["network"],
        "gcp_internal_ip": summary["internal_ip"],
        "gcp_external_ip": summary["external_ip"],
    }
    if key_path.strip():
        record["key_path"] = key_path.strip()

    match_index = None
    for idx, item in enumerate(hosts):
        if item.get("alias") == effective_alias or item.get("name") == effective_alias:
            match_index = idx
            break

    if match_index is not None and not overwrite:
        return (
            f"Ya existe un host con alias '{effective_alias}' en hosts.yaml.\n"
            "Usa overwrite=True si quieres actualizarlo."
        )
    if match_index is not None:
        hosts[match_index] = record
        action = "actualizado"
    else:
        hosts.append(record)
        action = "añadido"

    _save_hosts(hosts)
    return (
        f"✓ Host {action} en hosts.yaml desde Google Cloud\n"
        f"  alias:        {effective_alias}\n"
        f"  vm:           {summary['name']}\n"
        f"  project:      {effective_project}\n"
        f"  zone:         {summary['zone']}\n"
        f"  host_type:    {host_type}\n"
        f"  ip_guardada:  {selected_ip}\n"
        f"  user:         {record.get('user', '-') or '-'}\n"
        f"  tags:         {', '.join(combined_tags) if combined_tags else '-'}\n"
        f"  key_path:     {record.get('key_path', '-')}\n\n"
        + (
            "Aviso: la VM no tenía IP pública visible en este momento, así que se guardó la IP interna.\n\n"
            if used_internal_fallback else ""
        )
        + "Ya puedes usar ssh_connect(alias=...) o test_host_connection(alias=...)."
    )
