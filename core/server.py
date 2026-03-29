"""
SAPladdin - MCP Server: inicialización y registro de tools.

Estructura de módulos:
  filesystem   → operaciones de ficheros locales
  terminal     → ejecución de comandos locales
  process      → gestión de procesos locales
  process_sess → procesos interactivos con estado (REPLs, shells)
  hana         → SAP HANA Cloud
  ssh          → SSH a servidores Linux/Windows remotos
  oracle       → Oracle Database (oracledb thin mode)
  mssql        → SQL Server (pyodbc)
  hosts_mgmt   → gestión del inventario de hosts (hosts.yaml)
"""

import logging
import platform
from pathlib import Path

from fastmcp import FastMCP

from core.tools.filesystem import (
    read_file, write_file, search_files, edit_file_diff,
    list_directory, get_file_info, create_directory,
    move_file, read_multiple_files,
)
from core.tools.process_sessions import (
    start_process, read_process_output, interact_with_process,
    list_sessions, force_terminate,
)
from core.tools.hana import (
    hana_test_connection, hana_execute_query, hana_execute_ddl,
    hana_list_schemas, hana_list_tables, hana_describe_table,
    hana_get_row_count, hana_get_system_info,
)
from core.tools.terminal import execute_command, execute_command_streaming
from core.tools.process import list_processes, kill_process
from core.tools.utils import load_security_config

# Imports condicionales — los módulos nuevos pueden no tener deps instaladas
try:
    from core.tools.ssh import (
        ssh_connect, ssh_execute, ssh_upload, ssh_download,
        ssh_list_connections, ssh_disconnect,
    )
    _SSH_AVAILABLE = True
except ImportError:
    _SSH_AVAILABLE = False

try:
    from core.tools.oracle import (
        oracle_test_connection, oracle_execute_query,
        oracle_list_schemas, oracle_describe_table, oracle_get_system_info,
    )
    _ORACLE_AVAILABLE = True
except ImportError:
    _ORACLE_AVAILABLE = False

try:
    from core.tools.mssql import (
        mssql_test_connection, mssql_execute_query,
        mssql_list_databases, mssql_describe_table,
    )
    _MSSQL_AVAILABLE = True
except ImportError:
    _MSSQL_AVAILABLE = False

from core.tools.hosts_mgmt import (
    list_hosts, get_host, add_host, remove_host, test_host_connection,
)

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "security_config.yaml"
security_config = load_security_config(_CONFIG_PATH)

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="SAPladdin",
    instructions=(
        "MCP Server para SAP Basis, Linux Admin, Windows Admin y DBAs. "
        "Proporciona acceso a sistemas Linux vía SSH, bases de datos Oracle, "
        "SQL Server, SAP HANA Cloud, y herramientas de ficheros y procesos locales. "
        "Usa list_hosts para ver los sistemas configurados. "
        "Platform: " + platform.system()
    ),
)

# ---------------------------------------------------------------------------
# Registro: filesystem
# ---------------------------------------------------------------------------
mcp.tool()(read_file)
mcp.tool()(write_file)
mcp.tool()(search_files)
mcp.tool()(edit_file_diff)
mcp.tool()(list_directory)
mcp.tool()(get_file_info)
mcp.tool()(create_directory)
mcp.tool()(move_file)
mcp.tool()(read_multiple_files)

# ---------------------------------------------------------------------------
# Registro: terminal + procesos
# ---------------------------------------------------------------------------
mcp.tool()(execute_command)
mcp.tool()(execute_command_streaming)
mcp.tool()(list_processes)
mcp.tool()(kill_process)
mcp.tool()(start_process)
mcp.tool()(read_process_output)
mcp.tool()(interact_with_process)
mcp.tool()(list_sessions)
mcp.tool()(force_terminate)

# ---------------------------------------------------------------------------
# Registro: SAP HANA Cloud
# ---------------------------------------------------------------------------
mcp.tool()(hana_test_connection)
mcp.tool()(hana_execute_query)
mcp.tool()(hana_execute_ddl)
mcp.tool()(hana_list_schemas)
mcp.tool()(hana_list_tables)
mcp.tool()(hana_describe_table)
mcp.tool()(hana_get_row_count)
mcp.tool()(hana_get_system_info)

# ---------------------------------------------------------------------------
# Registro: SSH (si paramiko está instalado)
# ---------------------------------------------------------------------------
if _SSH_AVAILABLE:
    mcp.tool()(ssh_connect)
    mcp.tool()(ssh_execute)
    mcp.tool()(ssh_upload)
    mcp.tool()(ssh_download)
    mcp.tool()(ssh_list_connections)
    mcp.tool()(ssh_disconnect)

# ---------------------------------------------------------------------------
# Registro: Oracle DB (si oracledb está instalado)
# ---------------------------------------------------------------------------
if _ORACLE_AVAILABLE:
    mcp.tool()(oracle_test_connection)
    mcp.tool()(oracle_execute_query)
    mcp.tool()(oracle_list_schemas)
    mcp.tool()(oracle_describe_table)
    mcp.tool()(oracle_get_system_info)

# ---------------------------------------------------------------------------
# Registro: SQL Server (si pyodbc está instalado)
# ---------------------------------------------------------------------------
if _MSSQL_AVAILABLE:
    mcp.tool()(mssql_test_connection)
    mcp.tool()(mssql_execute_query)
    mcp.tool()(mssql_list_databases)
    mcp.tool()(mssql_describe_table)

# ---------------------------------------------------------------------------
# Registro: gestión de inventario de hosts (siempre disponible)
# ---------------------------------------------------------------------------
mcp.tool()(list_hosts)
mcp.tool()(get_host)
mcp.tool()(add_host)
mcp.tool()(remove_host)
mcp.tool()(test_host_connection)


def get_server() -> FastMCP:
    """Devuelve la instancia configurada del servidor MCP."""
    return mcp
