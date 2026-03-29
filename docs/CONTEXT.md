# SAPladdin — CONTEXT.md
# Documento de estado para continuidad entre sesiones LLM.
# AL EMPEZAR UNA SESIÓN NUEVA: pega el contenido de este fichero como primer mensaje.

## ¿Qué es SAPladdin?
MCP Server para SAP Basis Admin, Linux Admin, Windows Admin y DBAs.
Basado en DesktopCommanderPy, extendido con SSH, Oracle, SQL Server, HANA y gestión de hosts.

## Ubicación local
C:\Users\Edu\SAPladdin\

## Repo GitHub
https://github.com/eduardoddddddd/SAPladdin

## Estado: SESIÓN 4 COMPLETADA — 2026-03-29
### Desarrollo hecho en colaboración Claude + ChatGPT

## Ficheros — TODOS COMPLETOS ✅
core/server.py           — FastMCP, registro condicional de todos los módulos
core/hosts.py            — _load_hosts, _save_hosts, get_host_config
core/tools/utils.py      — seguridad, paths, shell, subprocess env
core/tools/session_manager.py
core/tools/process.py
core/tools/terminal.py
core/tools/filesystem.py
core/tools/process_sessions.py
core/tools/hana.py       — MEJORADO: _candidate_config_paths, _safe_identifier,
                           _escape_like, queries parametrizadas, fallback a DCPy config
core/tools/ssh.py        — MEJORADO: manejo explícito host no resuelto, mensaje claro
core/tools/oracle.py     — MEJORADO: _safe_identifier, _escape_like, queries parametrizadas
core/tools/mssql.py      — MEJORADO: _safe_identifier, queries con placeholders ?
core/tools/hosts_mgmt.py — MEJORADO: add_host tiene param database para MSSQL
core/tools/sap_basis.py  — NUEVO: sap_list_instances, sapcontrol_get_process_list,
                           sap_check_work_processes (sobre SSH)
config/security_config.yaml
config/hosts.yaml.example
config/hosts.yaml         — EXISTE (creado por usuario, NO va al repo)
config/hana_config.yaml.example
docs/CONTEXT.md           — este fichero
README.md
main.py
pyproject.toml
requirements.txt / requirements-dev.txt
scripts/_install.bat
scripts/_git_setup.bat
tests/conftest.py
tests/test_filesystem_and_hosts.py  — 11 tests, todos pasan ✅

## Tests: 11/11 GREEN
python -m pytest tests\ --tb=line -q   →   11 passed in 0.09s

## Arquitectura de conexiones (pools en memoria)
SSH:    _ssh_pool    dict en ssh.py    — paramiko.SSHClient por alias
Oracle: _oracle_pool dict en oracle.py — oracledb.Connection por alias
MSSQL:  _mssql_pool  dict en mssql.py  — pyodbc.Connection por alias
HANA:   sin pool    — conexión nueva por query (hdbcli)

## Tools disponibles (37 total)
filesystem (9): read_file, write_file, edit_file_diff, list_directory, search_files,
                get_file_info, create_directory, move_file, read_multiple_files
terminal (2):   execute_command, execute_command_streaming
process (7):    list_processes, kill_process, start_process, read_process_output,
                interact_with_process, list_sessions, force_terminate
hana (8):       hana_test_connection, hana_execute_query, hana_execute_ddl,
                hana_list_schemas, hana_list_tables, hana_describe_table,
                hana_get_row_count, hana_get_system_info
ssh (6):        ssh_connect, ssh_execute, ssh_upload, ssh_download,
                ssh_list_connections, ssh_disconnect
sap_basis (3):  sap_list_instances, sapcontrol_get_process_list, sap_check_work_processes
oracle (5):     oracle_test_connection, oracle_execute_query, oracle_list_schemas,
                oracle_describe_table, oracle_get_system_info
mssql (4):      mssql_test_connection, mssql_execute_query,
                mssql_list_databases, mssql_describe_table
hosts (5):      list_hosts, get_host, add_host, remove_host, test_host_connection

## Dependencias
fastmcp>=2.0.0, pyyaml, psutil, aiofiles, pathspec,
paramiko>=3.4, oracledb>=2.0, pyodbc>=5.0, hdbcli>=2.0

## Instalación
cd C:\Users\Edu\SAPladdin
scripts\_install.bat           # crea venv, instala, copia hosts.yaml.example

## Claude Desktop config
{
  "mcpServers": {
    "SAPladdin": {
      "command": "C:\\Users\\Edu\\SAPladdin\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Edu\\SAPladdin\\main.py"]
    }
  }
}

## Próximas mejoras posibles
1. Instalar deps reales y probar conexiones live (paramiko, oracledb, pyodbc, hdbcli)
2. sap_basis: añadir sap_start_instance, sap_stop_instance vía sapcontrol
3. sap_basis: añadir sap_check_system_log (SM21 vía SSH + grep)
4. oracle: añadir oracle_check_tablespace_sap (query específica para landscape SAP)
5. Tests de integración con mocks de BD reales
6. Modo HTTP/SSE para acceso remoto al MCP desde otros hosts
7. pyrfc: RFC/BAPI nativos (requiere SAP NW RFC SDK — no puro Python)
