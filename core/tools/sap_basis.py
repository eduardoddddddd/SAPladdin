"""
SAPladdin - SAP Basis tools sobre SSH.

Estas tools reutilizan las conexiones SSH activas para ejecutar comandos
habituales de administración SAP en hosts Linux/Windows con OpenSSH.
"""

from typing import Annotated

from core.tools.ssh import ssh_connect, ssh_execute, ssh_list_connections


def _build_connection_name(connection: str, alias: str) -> str:
    return connection or alias


async def _ensure_connection(connection: str, alias: str) -> str:
    connection_name = _build_connection_name(connection, alias)
    if not connection_name:
        return ""

    active_connections = await ssh_list_connections()
    if connection_name in active_connections:
        return connection_name

    connect_result = await ssh_connect(alias=connection_name)
    if connect_result.startswith("✓"):
        return connection_name
    return ""


async def sap_list_instances(
    connection: Annotated[str, "Conexión SSH activa. Vacío si quieres resolver por alias."] = "",
    alias: Annotated[str, "Alias de hosts.yaml para autoconectar si no existe conexión activa."] = "",
) -> str:
    """Lista instancias SAP visibles en el host usando sapcontrol."""
    connection_name = await _ensure_connection(connection, alias)
    if not connection_name:
        requested = connection or alias or "<vacío>"
        return (
            "No se pudo obtener conexión SSH para listar instancias SAP.\n"
            "Pasa connection con una sesión activa o alias con un host válido.\n"
            f"Valor recibido: {requested}"
        )
    return await ssh_execute(
        connection_name,
        "sapcontrol -function GetSystemInstanceList",
    )


async def sapcontrol_get_process_list(
    instance_nr: Annotated[str, "Número de instancia SAP. Ej: 00, 01, 10."],
    connection: Annotated[str, "Conexión SSH activa. Vacío si quieres resolver por alias."] = "",
    alias: Annotated[str, "Alias de hosts.yaml para autoconectar si no existe conexión activa."] = "",
) -> str:
    """Devuelve GetProcessList de sapcontrol para una instancia concreta."""
    connection_name = await _ensure_connection(connection, alias)
    if not connection_name:
        requested = connection or alias or "<vacío>"
        return (
            "No se pudo obtener conexión SSH para sapcontrol GetProcessList.\n"
            "Pasa connection con una sesión activa o alias con un host válido.\n"
            f"Valor recibido: {requested}"
        )
    command = f"sapcontrol -nr {instance_nr} -function GetProcessList"
    return await ssh_execute(connection_name, command)


async def sap_check_work_processes(
    instance_nr: Annotated[str, "Número de instancia SAP. Ej: 00, 01, 10."],
    connection: Annotated[str, "Conexión SSH activa. Vacío si quieres resolver por alias."] = "",
    alias: Annotated[str, "Alias de hosts.yaml para autoconectar si no existe conexión activa."] = "",
) -> str:
    """Resumen rápido de estado de work processes basado en sapcontrol."""
    process_output = await sapcontrol_get_process_list(
        instance_nr=instance_nr,
        connection=connection,
        alias=alias,
    )
    if process_output.startswith("[ERROR]") or process_output.startswith("No se pudo"):
        return process_output

    lines = process_output.splitlines()
    status_counts: dict[str, int] = {}
    for line in lines:
        upper_line = line.upper()
        if " GREEN" in upper_line or upper_line.endswith("GREEN"):
            status_counts["GREEN"] = status_counts.get("GREEN", 0) + 1
        if " YELLOW" in upper_line or upper_line.endswith("YELLOW"):
            status_counts["YELLOW"] = status_counts.get("YELLOW", 0) + 1
        if " GRAY" in upper_line or upper_line.endswith("GRAY"):
            status_counts["GRAY"] = status_counts.get("GRAY", 0) + 1
        if " RED" in upper_line or upper_line.endswith("RED"):
            status_counts["RED"] = status_counts.get("RED", 0) + 1

    if not status_counts:
        summary = "No se pudieron inferir colores de estado desde la salida."
    else:
        ordered = ", ".join(f"{key}={status_counts[key]}" for key in sorted(status_counts))
        summary = f"Resumen de estados: {ordered}"

    return f"{summary}\n\n{process_output}"
