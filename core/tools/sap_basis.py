"""
SAPladdin - SAP Basis tools sobre SSH.

Estas tools reutilizan las conexiones SSH activas para ejecutar comandos
habituales de administración SAP en hosts Linux/Windows con OpenSSH.

Tools disponibles:
  sap_list_instances          - GetSystemInstanceList (todos los SIDs del host)
  sapcontrol_get_process_list - GetProcessList de una instancia
  sap_check_work_processes    - resumen de estados de work processes
  sap_start_instance          - StartSystem / Start de sapcontrol
  sap_stop_instance           - StopSystem / Stop de sapcontrol
  sap_get_alerts              - GetAlertTree (alertas activas)
  sap_check_system_log        - SM21 equivalente via dev_w0/syslog
  sap_kernel_info             - versión de kernel y parches
  sap_dispatcher_queue        - dpmon snapshot de colas del dispatcher
  sap_list_sids               - detectar SIDs en /usr/sap
  sap_abap_short_dumps        - dumps recientes en DIR_HOME/dev_w*
"""

import logging
from typing import Annotated

from core.tools.ssh import ssh_connect, ssh_execute, ssh_list_connections

logger = logging.getLogger(__name__)


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


def _no_conn_msg(connection: str, alias: str, ctx: str) -> str:
    return (
        f"No se pudo obtener conexión SSH para {ctx}.\n"
        f"Pasa connection con sesión activa o alias válido en hosts.yaml.\n"
        f"Valor recibido: {connection or alias or '<vacío>'}"
    )


# ─── TOOLS EXISTENTES (refactorizadas) ────────────────────────────────────

async def sap_list_instances(
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
) -> str:
    """Lista todas las instancias SAP del host (GetSystemInstanceList)."""
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sap_list_instances")
    return await ssh_execute(conn, "sapcontrol -function GetSystemInstanceList")


async def sapcontrol_get_process_list(
    instance_nr: Annotated[str, "Número de instancia. Ej: 00, 01."],
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
) -> str:
    """GetProcessList de sapcontrol para una instancia (disp+work, gwrd, icman...)."""
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sapcontrol_get_process_list")
    return await ssh_execute(conn, f"sapcontrol -nr {instance_nr} -function GetProcessList")


async def sap_check_work_processes(
    instance_nr: Annotated[str, "Número de instancia. Ej: 00, 01."],
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
) -> str:
    """Resumen de estados (GREEN/YELLOW/RED/GRAY) de work processes vía sapcontrol."""
    output = await sapcontrol_get_process_list(instance_nr, connection, alias)
    if output.startswith("[ERROR]") or output.startswith("No se pudo"):
        return output
    counts: dict[str, int] = {}
    for line in output.splitlines():
        for color in ("GREEN", "YELLOW", "GRAY", "RED"):
            if color in line.upper():
                counts[color] = counts.get(color, 0) + 1
    summary = (
        ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        if counts else "No se pudieron detectar estados de color."
    )
    return f"Resumen instancia {instance_nr}: {summary}\n\n{output}"


# ─── TOOLS NUEVAS ────────────────────────────────────────────────────────

async def sap_start_instance(
    instance_nr: Annotated[str, "Número de instancia SAP. Ej: 00, 01."],
    sid: Annotated[str, "SID del sistema SAP. Ej: PRD, DEV, QAS."],
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
    full_system: Annotated[bool, "True = StartSystem (todos los hosts), False = solo esta instancia."] = False,
) -> str:
    """Arranca una instancia SAP vía sapcontrol. Requiere confirm implícito en el LLM.

    Usa StartSystem para arrancar el sistema completo o Start para una instancia.
    El usuario <sid>adm debe estar disponible en el host.
    """
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sap_start_instance")
    func = "StartSystem" if full_system else "Start"
    sid_lower = sid.lower()
    # Ejecutar como <sid>adm
    cmd = f'su - {sid_lower}adm -c "sapcontrol -nr {instance_nr} -function {func}"'
    result = await ssh_execute(conn, cmd)
    return f"[{sid} inst={instance_nr}] {func} ejecutado:\n{result}"


async def sap_stop_instance(
    instance_nr: Annotated[str, "Número de instancia SAP. Ej: 00, 01."],
    sid: Annotated[str, "SID del sistema SAP. Ej: PRD, DEV, QAS."],
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
    full_system: Annotated[bool, "True = StopSystem (todos los hosts), False = solo esta instancia."] = False,
    soft_timeout: Annotated[int, "Timeout soft shutdown en segundos. Default 300."] = 300,
) -> str:
    """Para una instancia SAP vía sapcontrol.

    ⚠ ATENCIÓN: Para producción usa siempre full_system=False primero
    para verificar el estado antes de un StopSystem completo.
    """
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sap_stop_instance")
    func = "StopSystem" if full_system else "Stop"
    sid_lower = sid.lower()
    timeout_arg = f" {soft_timeout}" if full_system else ""
    cmd = f'su - {sid_lower}adm -c "sapcontrol -nr {instance_nr} -function {func}{timeout_arg}"'
    result = await ssh_execute(conn, cmd, timeout=soft_timeout + 30)
    return f"[{sid} inst={instance_nr}] {func} ejecutado:\n{result}"


async def sap_get_alerts(
    instance_nr: Annotated[str, "Número de instancia SAP."],
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
) -> str:
    """Obtiene alertas activas vía sapcontrol GetAlertTree. Equivalente a CCMS/RZ20."""
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sap_get_alerts")
    return await ssh_execute(conn, f"sapcontrol -nr {instance_nr} -function GetAlertTree")


async def sap_kernel_info(
    instance_nr: Annotated[str, "Número de instancia SAP."],
    sid: Annotated[str, "SID del sistema. Ej: PRD."],
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
) -> str:
    """Versión de kernel SAP, nivel de parche y release. Equivalente a SM51 > kernel info."""
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sap_kernel_info")
    sid_lower = sid.lower()
    # disp+work -v da info completa del kernel
    cmd = f'su - {sid_lower}adm -c "disp+work -v 2>&1 | head -30"'
    result = await ssh_execute(conn, cmd)
    # También sapcontrol GetVersionInfo
    version_info = await ssh_execute(conn, f"sapcontrol -nr {instance_nr} -function GetVersionInfo")
    return f"=== disp+work -v ===\n{result}\n\n=== GetVersionInfo ===\n{version_info}"


async def sap_list_sids(
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
) -> str:
    """Detecta todos los SIDs SAP instalados en el host (/usr/sap y /etc/sap/services)."""
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sap_list_sids")
    cmds = [
        "ls /usr/sap/ 2>/dev/null | grep -v trans | grep -v tmp | grep -E '^[A-Z][A-Z0-9]{2}$'",
        "cat /usr/sap/sapservices 2>/dev/null || echo '(no sapservices)'",
        "ps aux 2>/dev/null | grep -i 'sapstart\\|disp+work' | grep -v grep | head -10",
    ]
    sections = []
    for cmd in cmds:
        out = await ssh_execute(conn, cmd)
        sections.append(out)
    return (
        "=== SIDs en /usr/sap ===\n" + sections[0] +
        "\n\n=== sapservices ===\n" + sections[1] +
        "\n\n=== Procesos SAP activos ===\n" + sections[2]
    )


async def sap_check_system_log(
    sid: Annotated[str, "SID del sistema SAP. Ej: PRD."],
    instance_nr: Annotated[str, "Número de instancia. Ej: 00."],
    lines: Annotated[int, "Últimas N líneas del log. Default 50."] = 50,
    filter_severity: Annotated[str, "Filtro: E (error), W (warning), vacío = todo."] = "",
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
) -> str:
    """Lee el system log SAP (SM21 equivalente) desde el fichero syslog del host.

    Lee de /usr/sap/<SID>/D<NR>/log/SYSLOG o equivalente según versión.
    Para SAP NetWeaver >= 7.40 usa también el trabajo dev_w0.
    """
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sap_check_system_log")
    sid_upper = sid.upper()
    # Rutas comunes del syslog SAP
    syslog_paths = [
        f"/usr/sap/{sid_upper}/D{instance_nr.zfill(2)}/log/SYSLOG",
        f"/usr/sap/{sid_upper}/ASCS{instance_nr.zfill(2)}/log/SYSLOG",
        f"/usr/sap/{sid_upper}/D{instance_nr.zfill(2)}/work/dev_disp",
    ]
    grep_filter = f" | grep -i ' {filter_severity} '" if filter_severity else ""
    results = []
    for path in syslog_paths:
        cmd = f"test -f {path} && tail -{lines} {path}{grep_filter} 2>/dev/null || echo 'not found: {path}'"
        out = await ssh_execute(conn, cmd)
        results.append(f"--- {path} ---\n{out}")
    # También dev_w0 work dir
    work_cmd = (
        f"find /usr/sap/{sid_upper}/D{instance_nr.zfill(2)}/work/ "
        f"-name 'dev_w*' 2>/dev/null | head -5 | "
        f"xargs -I{{}} sh -c 'echo \"=== {{}} ===\"; tail -20 {{}}' 2>/dev/null"
    )
    dev_out = await ssh_execute(conn, work_cmd)
    return "\n\n".join(results) + f"\n\n=== dev_w* (últimas 20 líneas) ===\n{dev_out}"


async def sap_dispatcher_queue(
    sid: Annotated[str, "SID del sistema SAP."],
    instance_nr: Annotated[str, "Número de instancia."],
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
) -> str:
    """Snapshot de colas del dispatcher SAP (dpmon equivalente a SM50/SM66).

    Muestra estado de colas DIA, BTC, SPO, UPD, etc.
    """
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sap_dispatcher_queue")
    sid_lower = sid.lower()
    # dpmon en modo batch snapshot
    cmd = (
        f'su - {sid_lower}adm -c '
        f'"echo q | dpmon pf=/usr/sap/{sid.upper()}/SYS/profile/'
        f'{sid.upper()}_{instance_nr.zfill(2)}_$(hostname) 2>/dev/null || '
        f'sapcontrol -nr {instance_nr} -function GetQueueStatistic"'
    )
    return await ssh_execute(conn, cmd, timeout=30)


async def sap_abap_short_dumps(
    sid: Annotated[str, "SID del sistema SAP."],
    instance_nr: Annotated[str, "Número de instancia."],
    connection: Annotated[str, "Conexión SSH activa."] = "",
    alias: Annotated[str, "Alias de hosts.yaml."] = "",
    last_minutes: Annotated[int, "Buscar dumps modificados en los últimos N minutos. Default 60."] = 60,
) -> str:
    """Lista ABAP short dumps recientes (ST22 equivalente) buscando en ficheros dev_w*.

    Los dumps ABAP aparecen en los ficheros dev_w* del work directory.
    Para dumps completos se necesita acceso a la BD (tabla SNAP).
    """
    conn = await _ensure_connection(connection, alias)
    if not conn:
        return _no_conn_msg(connection, alias, "sap_abap_short_dumps")
    sid_upper = sid.upper()
    work_dir = f"/usr/sap/{sid_upper}/D{instance_nr.zfill(2)}/work"
    cmd = (
        f"find {work_dir} -name 'dev_w*' -mmin -{last_minutes} 2>/dev/null | "
        f"xargs grep -l 'ABAP runtime error\\|Short dump\\|SNAP' 2>/dev/null | "
        f"head -10"
    )
    files_with_dumps = await ssh_execute(conn, cmd)
    if "not found" in files_with_dumps.lower() or not files_with_dumps.strip():
        return f"No se encontraron dumps ABAP en los últimos {last_minutes} minutos en {work_dir}."
    # Extracto de cada fichero con dumps
    detail_cmd = (
        f"find {work_dir} -name 'dev_w*' -mmin -{last_minutes} 2>/dev/null | "
        f"xargs grep -h 'ABAP runtime error\\|Error in Module\\|Short text:' 2>/dev/null | "
        f"sort | uniq -c | sort -rn | head -20"
    )
    detail = await ssh_execute(conn, detail_cmd)
    return (
        f"=== Ficheros con dumps (últimos {last_minutes} min) ===\n{files_with_dumps}\n\n"
        f"=== Resumen de errores ===\n{detail}"
    )
