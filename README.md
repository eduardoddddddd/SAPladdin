# SAPladdin 🔧

**MCP Server definitivo para SAP Basis Admin, Linux Admin, Windows Admin y DBAs.**

Conecta Claude (o cualquier LLM compatible con MCP) a tus sistemas reales:
servidores Linux vía SSH, Oracle DB, SQL Server, SAP HANA Cloud y filesystem/procesos locales.

## Capacidades

| Módulo | Tools | Descripción |
|---|---|---|
| **SSH** | `ssh_connect`, `ssh_execute`, `ssh_upload`, `ssh_download`, `ssh_list_connections`, `ssh_disconnect` | Acceso remoto a Linux/Windows |
| **SAP Basis** | `sap_list_instances`, `sapcontrol_get_process_list`, `sap_check_work_processes` | Atajos SAP por SSH sobre `sapcontrol` |
| **Oracle** | `oracle_test_connection`, `oracle_execute_query`, `oracle_list_schemas`, `oracle_describe_table`, `oracle_get_system_info` | Oracle DB (thin mode, sin Oracle Client) |
| **SQL Server** | `mssql_test_connection`, `mssql_execute_query`, `mssql_list_databases`, `mssql_describe_table` | SQL Server on-premise y Azure SQL |
| **HANA Cloud** | `hana_test_connection`, `hana_execute_query`, `hana_execute_ddl`, `hana_list_schemas`, `hana_list_tables`, `hana_describe_table`, `hana_get_row_count`, `hana_get_system_info` | SAP HANA Cloud (BTP) |
| **Hosts** | `list_hosts`, `get_host`, `add_host`, `remove_host`, `test_host_connection` | Inventario de sistemas |
| **Filesystem** | `read_file`, `write_file`, `edit_file_diff`, `list_directory`, `search_files`, `get_file_info`, `create_directory`, `move_file`, `read_multiple_files` | Operaciones de ficheros locales |
| **Terminal** | `execute_command`, `execute_command_streaming` | Shell local (PowerShell/bash) |
| **Procesos** | `list_processes`, `kill_process`, `start_process`, `interact_with_process`, `read_process_output`, `list_sessions`, `force_terminate` | Gestión de procesos e interactivos |

## Instalación rápida

```bash
cd C:\Users\Edu\SAPladdin
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]

# Configurar sistemas
copy config\hosts.yaml.example config\hosts.yaml
# Editar hosts.yaml con tus IPs/credenciales
```

O bien en Windows:

```bat
scripts\_install.bat
```

## Configuración Claude Desktop

Añadir a `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "SAPladdin": {
      "command": "C:\\Users\\Edu\\SAPladdin\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Edu\\SAPladdin\\main.py"]
    }
  }
}
```

## Uso básico

```
# Ver sistemas configurados
list_hosts()

# Conectar a Linux por SSH
ssh_connect(alias="sapapp1")
ssh_execute(connection="sapapp1", command="df -h")
ssh_execute(connection="sapapp1", command="sapcontrol -nr 00 -function GetProcessList")

# SAP Basis directo
sap_list_instances(alias="sapapp1")
sapcontrol_get_process_list(alias="sapapp1", instance_nr="00")
sap_check_work_processes(alias="sapapp1", instance_nr="00")

# Consultar Oracle
oracle_test_connection(alias="oraprd")
oracle_execute_query(alias="oraprd", sql="SELECT * FROM V$DATABASE")

# Consultar SQL Server
mssql_test_connection(alias="sqlprd")
mssql_execute_query(alias="sqlprd", sql="SELECT name FROM sys.databases")
```

## Seguridad

- `config/hosts.yaml` está en `.gitignore` — **nunca lo subas al repo**
- DML en Oracle/MSSQL requiere `confirm_dml=True` explícito
- DDL en HANA requiere `confirm=True` explícito
- Comandos locales filtrados por `config/security_config.yaml`

## Tests y estado

- Hay tests iniciales en `tests/test_filesystem_and_hosts.py`
- Cubren utilidades locales que no dependen de `fastmcp` ni drivers de BBDD
- Para ejecutarlos: `pytest`
- Si no tienes dependencias instaladas aún, usa primero `scripts\_install.bat`

## Limitaciones actuales

- `fastmcp`, `paramiko`, `oracledb`, `pyodbc` y `hdbcli` no vienen con Python base; deben instalarse en el venv
- HANA sigue heredado casi literal de DesktopCommanderPy y merece una ronda posterior de endurecimiento
- Oracle, MSSQL y HANA aún interpolan algunos identificadores SQL; conviene endurecerlos antes de exponer el servidor a uso amplio

## Basado en

[DesktopCommanderPy](https://github.com/eduardoddddddd/DesktopCommanderPy) — MCP Server Python base.

## Licencia
MIT
