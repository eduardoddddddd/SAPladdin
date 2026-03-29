# SAPladdin — CONTEXT.md
# AL EMPEZAR UNA SESIÓN NUEVA: pega el contenido de este fichero como primer mensaje.

## Proyecto
MCP Server para SAP Basis Admin, Linux Admin, Windows Admin y DBAs.
Local: C:\Users\Edu\SAPladdin\
GitHub: https://github.com/eduardoddddddd/SAPladdin

## Estado: SESIÓN 6 COMPLETADA — 2026-03-29

## Stack instalado en .venv ✅
paramiko 4.0.0 | oracledb 3.4.2 | pyodbc 5.3.0 | hdbcli 2.28.19
fastmcp 3.1.1  | psutil 7.2.2   | pyyaml 6.0.3

## Tests: 23/23 GREEN
.venv\Scripts\python.exe -m pytest tests\ -q   →   23 passed

## Tools disponibles (53 total)

### Filesystem (9): read_file, write_file, edit_file_diff, list_directory,
  search_files, get_file_info, create_directory, move_file, read_multiple_files

### Terminal + Procesos (9): execute_command, execute_command_streaming,
  list_processes, kill_process, start_process, read_process_output,
  interact_with_process, list_sessions, force_terminate

### SAP HANA Cloud (9): hana_test_connection, hana_execute_query, hana_execute_ddl,
  hana_list_schemas, hana_list_tables, hana_describe_table,
  hana_get_row_count, hana_get_system_info, hana_backup_catalog ← NUEVO

### SSH (6): ssh_connect, ssh_execute, ssh_upload, ssh_download,
  ssh_list_connections, ssh_disconnect

### SAP Basis / NetWeaver (11): sap_list_sids, sap_list_instances,
  sapcontrol_get_process_list, sap_check_work_processes,
  sap_start_instance, sap_stop_instance, sap_get_alerts,
  sap_kernel_info, sap_check_system_log, sap_dispatcher_queue,
  sap_abap_short_dumps

### Oracle DB (7): oracle_test_connection, oracle_execute_query,
  oracle_list_schemas, oracle_describe_table, oracle_get_system_info,
  oracle_check_tablespace_sap, oracle_backup_status ← NUEVO

### SQL Server (5): mssql_test_connection, mssql_execute_query,
  mssql_list_databases, mssql_describe_table, mssql_check_agent_jobs ← NUEVO

### Hosts (5): list_hosts, get_host, add_host, remove_host, test_host_connection

## Ficheros clave
core/server.py             — FastMCP, registro de todas las tools
core/hosts.py              — _load_hosts, _save_hosts, get_host_config
core/tools/sap_basis.py    — 11 tools SAP Basis sobre SSH
core/tools/oracle.py       — 7 tools Oracle (incluye RMAN backup)
core/tools/mssql.py        — 5 tools SQL Server (incluye Agent Jobs)
core/tools/hana.py         — 9 tools HANA Cloud (incluye backup catalog)
core/tools/ssh.py          — 6 tools SSH con pool paramiko
core/tools/hosts_mgmt.py   — gestión inventario hosts.yaml
tests/test_sap_basis.py    — 12 tests con FakeSSHClient (mock)
tests/test_filesystem_and_hosts.py — 11 tests
scripts/smoke_test.py      — test conectividad completo de todos los hosts

## Arquitectura de conexiones
SSH:    _ssh_pool    (paramiko.SSHClient)   — pool en memoria
Oracle: _oracle_pool (oracledb.Connection)  — pool en memoria
MSSQL:  _mssql_pool  (pyodbc.Connection)    — pool en memoria
HANA:   sin pool, conexión por query        — hdbcli

## Claude Desktop config
{
  "mcpServers": {
    "SAPladdin": {
      "command": "C:\\Users\\Edu\\SAPladdin\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Edu\\SAPladdin\\main.py"]
    }
  }
}

## Smoke test
cd C:\Users\Edu\SAPladdin
.venv\Scripts\python.exe scripts\smoke_test.py           # todos los hosts
.venv\Scripts\python.exe scripts\smoke_test.py --fast    # solo TCP
.venv\Scripts\python.exe scripts\smoke_test.py --alias sapapp1

## Próximos pasos
1. ← PRIORITARIO: Registrar en Claude Desktop y probar con hosts reales
2. sap_basis: sap_transport_buffer (tp showbuffer / stms equivalente vía SSH)
3. sap_basis: sap_icm_cache_flush (sapcontrol -function CacheFlush)
4. oracle: oracle_check_invalid_objects (objetos inválidos en schema SAP)
5. mssql: mssql_check_blocking (sys.dm_exec_requests con blocking)
6. Modo HTTP/SSE para acceso remoto al MCP desde Linux o CI/CD
7. Publicar en PyPI / npm como herramienta instalable
