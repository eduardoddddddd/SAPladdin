# SAPladdin — CONTEXT.md
# AL EMPEZAR UNA SESIÓN NUEVA: pega el contenido de este fichero como primer mensaje.

## Proyecto
MCP Server para SAP Basis Admin, Linux Admin, Windows Admin y DBAs.
Local: C:\Users\Edu\SAPladdin\
GitHub: https://github.com/eduardoddddddd/SAPladdin

## Estado: SESIÓN 5 COMPLETADA — 2026-03-29

## Stack instalado en .venv ✅
paramiko 4.0.0 | oracledb 3.4.2 | pyodbc 5.3.0 | hdbcli 2.28.19
fastmcp 3.1.1  | psutil 7.2.2   | pyyaml 6.0.3

## Tests: 11/11 GREEN
.venv\Scripts\python.exe -m pytest tests\ -q   →   11 passed

## Tools disponibles (48 total)

### Filesystem (9)
read_file, write_file, edit_file_diff, list_directory, search_files,
get_file_info, create_directory, move_file, read_multiple_files

### Terminal + Procesos (9)
execute_command, execute_command_streaming,
list_processes, kill_process,
start_process, read_process_output, interact_with_process, list_sessions, force_terminate

### SAP HANA Cloud (8)
hana_test_connection, hana_execute_query, hana_execute_ddl,
hana_list_schemas, hana_list_tables, hana_describe_table,
hana_get_row_count, hana_get_system_info

### SSH (6)
ssh_connect, ssh_execute, ssh_upload, ssh_download,
ssh_list_connections, ssh_disconnect

### SAP Basis / NetWeaver (11) ← NUEVO EN SESIÓN 5
sap_list_sids              - detecta SIDs en /usr/sap del host
sap_list_instances         - GetSystemInstanceList
sapcontrol_get_process_list - GetProcessList de una instancia
sap_check_work_processes   - resumen GREEN/YELLOW/RED/GRAY
sap_start_instance         - Start / StartSystem via sapcontrol
sap_stop_instance          - Stop / StopSystem via sapcontrol
sap_get_alerts             - GetAlertTree (CCMS/RZ20 equivalente)
sap_kernel_info            - versión kernel + disp+work -v
sap_check_system_log       - SM21 equivalente via SYSLOG + dev_w*
sap_dispatcher_queue       - dpmon / GetQueueStatistic (SM50/SM66)
sap_abap_short_dumps       - ST22 equivalente via grep en dev_w*

### Oracle DB (6) ← +1 en sesión 5
oracle_test_connection, oracle_execute_query, oracle_list_schemas,
oracle_describe_table, oracle_get_system_info,
oracle_check_tablespace_sap  - tablespaces con alertas threshold, top segmentos SAP

### SQL Server (4)
mssql_test_connection, mssql_execute_query,
mssql_list_databases, mssql_describe_table

### Hosts (5)
list_hosts, get_host, add_host, remove_host, test_host_connection

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

## Próximos pasos sugeridos
1. Registrar SAPladdin en Claude Desktop y probar con hosts reales
2. Añadir tests para sap_basis (mocks de ssh_execute)
3. Añadir oracle_backup_status (RMAN query v$rman_backup_job_details)
4. Añadir sap_hana_backup_catalog (hdbcli query M_BACKUP_CATALOG)
5. Añadir mssql_check_agent_jobs (msdb.dbo.sysjobhistory)
6. Considerar modo HTTP para acceso remoto al MCP desde otros hosts
7. Script de smoke test que conecte a todos los hosts y reporte estado
