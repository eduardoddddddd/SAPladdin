"""
SAPladdin - MCP Server: inicialización y registro de tools.
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
    hana_get_row_count, hana_get_system_info, hana_backup_catalog,
)
from core.tools.terminal import execute_command, execute_command_streaming
from core.tools.process import list_processes, kill_process
from core.tools.utils import load_security_config

try:
    from core.tools.ssh import (
        ssh_connect, ssh_execute, ssh_upload, ssh_download,
        ssh_list_connections, ssh_disconnect,
    )
    from core.tools.sap_basis import (
        sap_list_instances, sapcontrol_get_process_list, sap_check_work_processes,
        sap_start_instance, sap_stop_instance, sap_get_alerts,
        sap_kernel_info, sap_list_sids, sap_check_system_log,
        sap_dispatcher_queue, sap_abap_short_dumps,
    )
    _SSH_AVAILABLE = True
except ImportError:
    _SSH_AVAILABLE = False

try:
    from core.tools.oracle import (
        oracle_test_connection, oracle_execute_query,
        oracle_list_schemas, oracle_describe_table,
        oracle_get_system_info, oracle_check_tablespace_sap,
        oracle_backup_status,
    )
    _ORACLE_AVAILABLE = True
except ImportError:
    _ORACLE_AVAILABLE = False

try:
    from core.tools.mssql import (
        mssql_test_connection, mssql_execute_query,
        mssql_list_databases, mssql_describe_table,
        mssql_check_agent_jobs,
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

mcp = FastMCP(
    name="SAPladdin",
    instructions=(
        "MCP Server para SAP Basis, Linux Admin, Windows Admin y DBAs. "
        "Acceso a Linux vía SSH, Oracle, SQL Server, SAP HANA Cloud, "
        "filesystem y procesos locales. "
        "Usa list_hosts para ver sistemas configurados. "
        "Platform: " + platform.system()
    ),
)

# Filesystem
for _t in [read_file, write_file, search_files, edit_file_diff,
           list_directory, get_file_info, create_directory,
           move_file, read_multiple_files]:
    mcp.tool()(_t)

# Terminal + Procesos
for _t in [execute_command, execute_command_streaming,
           list_processes, kill_process,
           start_process, read_process_output,
           interact_with_process, list_sessions, force_terminate]:
    mcp.tool()(_t)

# SAP HANA Cloud (9)
for _t in [hana_test_connection, hana_execute_query, hana_execute_ddl,
           hana_list_schemas, hana_list_tables, hana_describe_table,
           hana_get_row_count, hana_get_system_info, hana_backup_catalog]:
    mcp.tool()(_t)

# SSH + SAP Basis
if _SSH_AVAILABLE:
    for _t in [ssh_connect, ssh_execute, ssh_upload, ssh_download,
               ssh_list_connections, ssh_disconnect,
               sap_list_sids, sap_list_instances,
               sapcontrol_get_process_list, sap_check_work_processes,
               sap_start_instance, sap_stop_instance,
               sap_get_alerts, sap_kernel_info,
               sap_check_system_log, sap_dispatcher_queue,
               sap_abap_short_dumps]:
        mcp.tool()(_t)

# Oracle DB (7)
if _ORACLE_AVAILABLE:
    for _t in [oracle_test_connection, oracle_execute_query,
               oracle_list_schemas, oracle_describe_table,
               oracle_get_system_info, oracle_check_tablespace_sap,
               oracle_backup_status]:
        mcp.tool()(_t)

# SQL Server (5)
if _MSSQL_AVAILABLE:
    for _t in [mssql_test_connection, mssql_execute_query,
               mssql_list_databases, mssql_describe_table,
               mssql_check_agent_jobs]:
        mcp.tool()(_t)

# Hosts (5)
for _t in [list_hosts, get_host, add_host, remove_host, test_host_connection]:
    mcp.tool()(_t)


def get_server() -> FastMCP:
    return mcp
