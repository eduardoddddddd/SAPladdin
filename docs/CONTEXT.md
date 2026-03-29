# SAPladdin — CONTEXT.md
# ─────────────────────────────────────────────────────────────────────────
# AL EMPEZAR UNA SESIÓN NUEVA: pega este fichero completo como primer mensaje.
# ─────────────────────────────────────────────────────────────────────────

## Proyecto
MCP Server para SAP Basis Admin, Linux Admin, Windows Admin y DBAs.
Conecta Claude (o cualquier LLM compatible con MCP) a sistemas reales:
Linux vía SSH, Oracle DB, SQL Server, SAP HANA Cloud, filesystem y procesos locales.

**Local:**  C:\Users\Edu\SAPladdin\
**GitHub:** https://github.com/eduardoddddddd/SAPladdin
**Base:**   DesktopCommanderPy (C:\Users\Edu\DesktopCommanderPy)

---

## Estado actual — SESIÓN 6 COMPLETADA (2026-03-29)
Proyecto funcional y completo en su versión inicial.
Desarrollado en colaboración Claude + ChatGPT.

---

## Stack Python (.venv) ✅
| Paquete    | Versión | Rol                      |
|------------|---------|--------------------------|
| fastmcp    | 3.1.1   | Framework MCP            |
| paramiko   | 4.0.0   | SSH                      |
| oracledb   | 3.4.2   | Oracle DB (thin mode)    |
| pyodbc     | 5.3.0   | SQL Server               |
| hdbcli     | 2.28.19 | SAP HANA Cloud           |
| psutil     | 7.2.2   | Procesos locales         |
| pyyaml     | 6.0.3   | Config YAML              |

---

## Tests: 23/23 GREEN ✅
```
.venv\Scripts\python.exe -m pytest tests\ -q   →   23 passed in 0.13s
```
- `tests/test_filesystem_and_hosts.py` — 11 tests (filesystem, hosts, SSH error, safe_identifier)
- `tests/test_sap_basis.py`            — 12 tests (FakeSSHClient, sapcontrol, work processes)

---

## Tools disponibles: 53 total

### Filesystem (9)
read_file, write_file, edit_file_diff, list_directory, search_files,
get_file_info, create_directory, move_file, read_multiple_files

### Terminal + Procesos (9)
execute_command, execute_command_streaming, list_processes, kill_process,
start_process, read_process_output, interact_with_process, list_sessions, force_terminate

### SAP HANA Cloud (9)
hana_test_connection, hana_execute_query, hana_execute_ddl,
hana_list_schemas, hana_list_tables, hana_describe_table,
hana_get_row_count, hana_get_system_info, hana_backup_catalog

### SSH (6)
ssh_connect, ssh_execute, ssh_upload, ssh_download,
ssh_list_connections, ssh_disconnect

### SAP Basis / NetWeaver (11)
sap_list_sids, sap_list_instances, sapcontrol_get_process_list,
sap_check_work_processes, sap_start_instance, sap_stop_instance,
sap_get_alerts, sap_kernel_info, sap_check_system_log,
sap_dispatcher_queue, sap_abap_short_dumps

### Oracle DB (7)
oracle_test_connection, oracle_execute_query, oracle_list_schemas,
oracle_describe_table, oracle_get_system_info,
oracle_check_tablespace_sap, oracle_backup_status

### SQL Server (5)
mssql_test_connection, mssql_execute_query,
mssql_list_databases, mssql_describe_table, mssql_check_agent_jobs

### Hosts (5)
list_hosts, get_host, add_host, remove_host, test_host_connection

---

## Estructura de ficheros

```
SAPladdin/
├── main.py                        # Entry point (stdio / HTTP-SSE)
├── pyproject.toml                 # Build + deps
├── requirements.txt
├── config/
│   ├── security_config.yaml       # Dirs permitidos, comandos bloqueados
│   ├── hosts.yaml                 # ← TU INVENTARIO (no va al repo)
│   ├── hosts.yaml.example         # Plantilla con todos los tipos
│   └── hana_config.yaml.example
├── core/
│   ├── server.py                  # FastMCP + registro de las 53 tools
│   ├── hosts.py                   # _load/_save_hosts, get_host_config
│   └── tools/
│       ├── filesystem.py          # Operaciones ficheros locales
│       ├── terminal.py            # Shell local (PS/bash)
│       ├── process.py             # list/kill procesos
│       ├── process_sessions.py    # Procesos interactivos (REPLs)
│       ├── session_manager.py     # Pool de sesiones asyncio
│       ├── utils.py               # Seguridad, paths, shell
│       ├── hana.py                # HANA Cloud (hdbcli)
│       ├── ssh.py                 # SSH con pool paramiko
│       ├── sap_basis.py           # 11 tools SAP Basis sobre SSH
│       ├── oracle.py              # Oracle (oracledb thin)
│       ├── mssql.py               # SQL Server (pyodbc)
│       └── hosts_mgmt.py         # Gestión inventario hosts.yaml
├── tests/
│   ├── conftest.py
│   ├── test_filesystem_and_hosts.py
│   └── test_sap_basis.py          # FakeSSHClient + mocks
├── scripts/
│   ├── smoke_test.py              # Test conectividad todos los hosts
│   ├── _install.bat               # Crea venv, instala deps, copia example
│   └── _git_setup.bat
└── docs/
    └── CONTEXT.md                 # Este fichero
```

---

## Arquitectura de conexiones (pools en memoria)
| Tipo         | Pool               | Lib       | Nota                         |
|--------------|--------------------|-----------|------------------------------|
| SSH          | `_ssh_pool` dict   | paramiko  | Por alias, persiste sesión   |
| Oracle       | `_oracle_pool` dict| oracledb  | thin mode, sin Oracle Client |
| SQL Server   | `_mssql_pool` dict | pyodbc    | ODBC Driver 17/18            |
| HANA Cloud   | sin pool           | hdbcli    | Conexión nueva por query     |

---

## Instalación

```bat
cd C:\Users\Edu\SAPladdin
scripts\_install.bat
```

O manual:
```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
copy config\hosts.yaml.example config\hosts.yaml
REM editar hosts.yaml con tus IPs/credenciales
```

## Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json`)
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

## Smoke test
```bat
.venv\Scripts\python.exe scripts\smoke_test.py            # todos los hosts
.venv\Scripts\python.exe scripts\smoke_test.py --fast     # solo TCP
.venv\Scripts\python.exe scripts\smoke_test.py --alias sapapp1
.venv\Scripts\python.exe scripts\smoke_test.py --type oracle
```

---

## Diseño y decisiones clave
- **imports condicionales** en server.py: SSH/Oracle/MSSQL en try/except ImportError
  → el servidor arranca aunque falte un driver
- **oracledb thin mode**: no requiere Oracle Client instalado
- **_safe_identifier()** en oracle/mssql/hana: protección contra SQL injection
- **confirm_dml=True** requerido para INSERT/UPDATE/DELETE/DROP
- **confirm=True** requerido para DDL en HANA
- **hosts.yaml** en .gitignore siempre (contiene credenciales)
- **sap_basis.py** sobre SSH: no necesita RFC SDK ni librería SAP

---

## Historial de commits
```
5a1198c feat_backup_monitoring_smoke_test_23tests
dc1a8c6 feat_sap_basis_extended_oracle_tablespace
df74f35 feat_sap_basis_safe_identifier_tests
253b823 feat: add SAP Basis SSH tools and project hardening
63ffe1f feat_initial_sapladdin
```

---

## Próximos pasos sugeridos
1. **PRIORITARIO**: Registrar en Claude Desktop + probar con hosts reales
2. sap_basis: `sap_transport_buffer` (tp showbuffer / STMS equivalente)
3. sap_basis: `sap_icm_cache_flush` (sapcontrol CacheFlush)
4. oracle: `oracle_check_invalid_objects` (objetos inválidos schema SAP)
5. mssql: `mssql_check_blocking` (sys.dm_exec_requests blocking_session_id)
6. Modo HTTP/SSE para acceso remoto al MCP desde Linux o CI/CD
7. Publicar en PyPI como `sapladdin`
