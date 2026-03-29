# SAPladdin 🔧

**MCP Server definitivo para SAP Basis Admin, Linux Admin, Windows Admin y DBAs.**

Conecta Claude (o cualquier LLM compatible con MCP) a tus sistemas reales.

---

## Capacidades — 53 tools

| Módulo | Tools | Descripción |
|---|---|---|
| **Filesystem** (9) | read, write, edit, search, list... | Operaciones locales con sandbox |
| **Terminal** (2) | execute_command, streaming | Shell local PS/bash |
| **Procesos** (7) | list, kill, start, interact... | Gestión + REPLs interactivos |
| **HANA Cloud** (9) | test, query, ddl, schemas, backup... | SAP HANA Cloud (hdbcli) |
| **SSH** (6) | connect, execute, upload, download... | Acceso remoto Linux/Windows |
| **SAP Basis** (11) | instances, processes, alerts, log... | NetWeaver vía SSH |
| **Oracle** (7) | test, query, schemas, tablespace, rman... | Oracle DB thin mode |
| **SQL Server** (5) | test, query, databases, agent jobs... | SQL Server on-premise/Azure |
| **Hosts** (5) | list, add, remove, test... | Inventario de sistemas |

---

## SAP Basis tools (detalle)

| Tool | Equivalente SAP | Descripción |
|---|---|---|
| `sap_list_sids` | — | Detecta SIDs en /usr/sap |
| `sap_list_instances` | SM51 | GetSystemInstanceList |
| `sapcontrol_get_process_list` | SM50 | GetProcessList por instancia |
| `sap_check_work_processes` | SM50 | Resumen GREEN/YELLOW/RED/GRAY |
| `sap_start_instance` | MMMC | Start / StartSystem |
| `sap_stop_instance` | MMMC | Stop / StopSystem |
| `sap_get_alerts` | RZ20/CCMS | GetAlertTree |
| `sap_kernel_info` | SM51 kernel | disp+work -v + GetVersionInfo |
| `sap_check_system_log` | SM21 | SYSLOG + dev_w* |
| `sap_dispatcher_queue` | SM50/SM66 | dpmon / GetQueueStatistic |
| `sap_abap_short_dumps` | ST22 | grep en dev_w* |

---

## Instalación rápida

```bat
cd C:\Users\Edu\SAPladdin
scripts\_install.bat
```

O manual:
```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
copy config\hosts.yaml.example config\hosts.yaml
```

Edita `config\hosts.yaml` con tus sistemas reales.

---

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

---

## Uso básico

```
# Ver sistemas configurados
list_hosts()

# Conectar a servidor Linux SAP y ver instancias
ssh_connect(alias="sapapp1")
sap_list_instances(connection="sapapp1")
sap_check_work_processes(instance_nr="00", connection="sapapp1")

# Ver alertas CCMS
sap_get_alerts(instance_nr="00", connection="sapapp1")

# Consultar Oracle DB
oracle_test_connection(alias="oraprd")
oracle_check_tablespace_sap(alias="oraprd", threshold_pct=85)
oracle_backup_status(alias="oraprd")

# Verificar jobs SQL Server
mssql_test_connection(alias="sqlprd")
mssql_check_agent_jobs(alias="sqlprd", only_failed=True)

# HANA Cloud backups
hana_test_connection()
hana_backup_catalog(days_back=3)
```

---

## Smoke test de conectividad

```bat
.venv\Scripts\python.exe scripts\smoke_test.py           # todos
.venv\Scripts\python.exe scripts\smoke_test.py --fast    # solo TCP
.venv\Scripts\python.exe scripts\smoke_test.py --alias sapapp1
.venv\Scripts\python.exe scripts\smoke_test.py --type oracle
```

---

## Hosts soportados (`config/hosts.yaml`)

```yaml
hosts:
  - name: sap_prod_app
    alias: sapapp1
    type: linux_ssh        # linux_ssh | windows_ssh | oracle | mssql | hana
    ip: 192.168.1.10
    port: 22
    user: root
    key_path: ~/.ssh/id_rsa
    tags: [sap, production, abap]
```

---

## Seguridad

- `config/hosts.yaml` en `.gitignore` — **nunca al repo**
- DML en Oracle/MSSQL requiere `confirm_dml=True`
- DDL en HANA requiere `confirm=True`
- `_safe_identifier()` en todos los módulos DB (anti SQL injection)
- Comandos locales filtrados por `security_config.yaml`
- imports condicionales: el servidor arranca aunque falte un driver

---

## Tests

```bat
.venv\Scripts\python.exe -m pytest tests\ -q
# 23 passed
```

---

## Stack

Python 3.11+ · fastmcp · paramiko · oracledb (thin) · pyodbc · hdbcli · psutil

---

## Basado en

[DesktopCommanderPy](https://github.com/eduardoddddddd/DesktopCommanderPy) — base MCP Python.

## Licencia

MIT
