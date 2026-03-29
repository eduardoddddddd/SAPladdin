"""
SAPladdin - Tools MCP para gestión del inventario de hosts.
Expone list_hosts, get_host, add_host, remove_host, test_host_connection.
"""
import logging
import socket
from typing import Annotated
from core.hosts import _load_hosts, _save_hosts, get_host_config

logger = logging.getLogger(__name__)

_VALID_TYPES = ("linux_ssh", "oracle", "mssql", "hana", "windows_ssh")


async def list_hosts(
    filter_type: Annotated[str, "Filtrar por tipo: linux_ssh, oracle, mssql, hana. Vacío = todos."] = "",
    filter_tag: Annotated[str, "Filtrar por tag (ej: production, sap, oracle). Vacío = todos."] = "",
) -> str:
    """Lista todos los hosts configurados en hosts.yaml con sus datos básicos."""
    hosts = _load_hosts()
    if not hosts:
        return (
            "No hay hosts configurados.\n"
            "Usa add_host para registrar sistemas, o edita config/hosts.yaml directamente.\n"
            "Consulta config/hosts.yaml.example para ver la estructura."
        )
    if filter_type:
        hosts = [h for h in hosts if h.get("type", "") == filter_type]
    if filter_tag:
        hosts = [h for h in hosts if filter_tag in h.get("tags", [])]
    if not hosts:
        return f"No hay hosts con los filtros indicados (type={filter_type!r}, tag={filter_tag!r})."

    lines = [f"Hosts configurados ({len(hosts)}):", "=" * 60]
    for h in hosts:
        alias = h.get("alias") or h.get("name", "?")
        htype = h.get("type", "?")
        ip = h.get("ip") or h.get("host", "?")
        port = h.get("port", "")
        tags = ", ".join(h.get("tags", []))
        user = h.get("user", "")
        lines.append(
            f"  [{htype:12s}]  {alias:<20}  {ip}:{port}"
            + (f"  user={user}" if user else "")
            + (f"  tags=[{tags}]" if tags else "")
        )
    return "\n".join(lines)


async def get_host(
    alias: Annotated[str, "Alias o name del host a consultar."],
) -> str:
    """Muestra todos los detalles de un host configurado (sin mostrar passwords)."""
    h = get_host_config(alias)
    if h is None:
        hosts = _load_hosts()
        names = [x.get("alias") or x.get("name") for x in hosts]
        return f"Host '{alias}' no encontrado.\nHosts disponibles: {names}"
    # Ocultar contraseña
    safe = {k: ("***" if k == "password" else v) for k, v in h.items()}
    lines = [f"Host: {alias}", "-" * 40]
    for k, v in safe.items():
        lines.append(f"  {k:<20}: {v}")
    return "\n".join(lines)

async def add_host(
    name: Annotated[str, "Nombre descriptivo. Ej: sap_prod_app."],
    alias: Annotated[str, "Alias corto para usar en tools. Ej: sapapp1."],
    host_type: Annotated[str, "Tipo: linux_ssh | oracle | mssql | hana | windows_ssh."],
    ip: Annotated[str, "IP o hostname."],
    port: Annotated[int, "Puerto. SSH=22, Oracle=1521, MSSQL=1433, HANA=443."] = 0,
    user: Annotated[str, "Usuario."] = "",
    password: Annotated[str, "Contraseña (se guarda en hosts.yaml — no commitar al repo)."] = "",
    key_path: Annotated[str, "Ruta clave SSH (para linux_ssh/windows_ssh)."] = "",
    service: Annotated[str, "Service name Oracle o database name MSSQL."] = "",
    tags: Annotated[str, "Tags separados por coma. Ej: production,sap,oracle."] = "",
    description: Annotated[str, "Descripción libre del sistema."] = "",
) -> str:
    """Registra un nuevo host en hosts.yaml. El alias debe ser único."""
    if host_type not in _VALID_TYPES:
        return f"Tipo inválido '{host_type}'. Válidos: {_VALID_TYPES}"
    hosts = _load_hosts()
    # Verificar unicidad de alias
    for h in hosts:
        if h.get("alias") == alias:
            return f"[ERROR] Ya existe un host con alias '{alias}'. Usa remove_host primero o elige otro alias."
    default_ports = {"linux_ssh": 22, "windows_ssh": 22, "oracle": 1521, "mssql": 1433, "hana": 443}
    new_host: dict = {
        "name": name,
        "alias": alias,
        "type": host_type,
        "ip": ip,
        "port": port or default_ports.get(host_type, 0),
    }
    if user: new_host["user"] = user
    if password: new_host["password"] = password
    if key_path: new_host["key_path"] = key_path
    if service: new_host["service"] = service
    if tags: new_host["tags"] = [t.strip() for t in tags.split(",")]
    if description: new_host["description"] = description
    hosts.append(new_host)
    _save_hosts(hosts)
    return (
        f"✓ Host '{alias}' ({host_type}) añadido a hosts.yaml.\n"
        f"  {ip}:{new_host['port']}"
        + (f"  user={user}" if user else "")
        + (f"\n  Recuerda: NO commitas hosts.yaml al repositorio (está en .gitignore)" if password else "")
    )


async def remove_host(
    alias: Annotated[str, "Alias del host a eliminar."],
    confirm: Annotated[bool, "Pasar True para confirmar la eliminación."] = False,
) -> str:
    """Elimina un host del inventario hosts.yaml."""
    if not confirm:
        return f"⚠ Eliminación no ejecutada. Pasa confirm=True para confirmar borrar '{alias}'."
    hosts = _load_hosts()
    new_hosts = [h for h in hosts if h.get("alias") != alias and h.get("name") != alias]
    if len(new_hosts) == len(hosts):
        return f"Host '{alias}' no encontrado."
    _save_hosts(new_hosts)
    return f"✓ Host '{alias}' eliminado de hosts.yaml."


async def test_host_connection(
    alias: Annotated[str, "Alias del host a probar."],
) -> str:
    """Prueba conectividad básica (ping TCP al puerto) de un host configurado."""
    h = get_host_config(alias)
    if h is None:
        return f"Host '{alias}' no encontrado. Usa list_hosts para ver los disponibles."
    ip = h.get("ip") or h.get("host", "")
    port = h.get("port", 22)
    htype = h.get("type", "?")
    if not ip:
        return f"[ERROR] Host '{alias}' no tiene IP configurada."
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        if result == 0:
            return f"✓ [{alias}] {ip}:{port} ({htype}) — puerto ABIERTO (TCP OK)"
        else:
            return f"✗ [{alias}] {ip}:{port} ({htype}) — puerto CERRADO o no alcanzable"
    except socket.gaierror:
        return f"✗ [{alias}] {ip} — no se puede resolver el hostname"
    except Exception as exc:
        return f"✗ [{alias}] {ip}:{port} — error: {exc}"
