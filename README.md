# SAPladdin

**MCP Server para SAP Basis Admin, Linux Admin, Windows Admin, DBAs y operación práctica sobre Google Cloud.**

Conecta Claude o cualquier cliente MCP compatible a sistemas reales: filesystem local, procesos, SSH, SAP Basis, Oracle, SQL Server, HANA Cloud y ahora Google Compute Engine vía `gcloud`.

Guía de conexión a clientes MCP y LLM apps:

- [docs/CLIENT_SETUP.md](docs/CLIENT_SETUP.md)

---

## Capacidades - 78 tools

| Módulo | Tools | Descripción |
|---|---|---|
| **Filesystem** (9) | read, write, edit, search, list... | Operaciones locales con sandbox |
| **Terminal** (2) | execute_command, streaming | Shell local PS/bash |
| **Procesos** (7) | list, kill, start, interact... | Gestión + REPLs interactivos |
| **HANA Cloud** (9) | test, query, ddl, schemas, backup... | SAP HANA Cloud (`hdbcli`) |
| **Google Cloud** (11) | config, list, start, stop, create, firewall, export... | Operación GCE/GCP reutilizando `gcloud` |
| **Joplin** (14) | status, config, permisos, list/search/get/create/update/delete | Gestión documental de notas/libretas vía Web Clipper |
| **SSH** (6) | connect, execute, upload, download... | Acceso remoto Linux/Windows |
| **SAP Basis** (11) | instances, processes, alerts, log... | NetWeaver vía SSH |
| **Oracle** (7) | test, query, schemas, tablespace, rman... | Oracle DB thin mode |
| **SQL Server** (5) | test, query, databases, agent jobs... | SQL Server on-premise/Azure |
| **Hosts** (5) | list, add, remove, test... | Inventario manual de sistemas |

---

## Google Cloud

La integración nueva es deliberadamente `gcloud-first`.

No usa el SDK Python de GCP. Usa wrappers MCP sobre `gcloud --format=json` porque en este entorno ya estaban validados:

- `gcloud` instalado en Windows
- proyecto activo `project-0bbed615-3203-4957-a27`
- service account funcional con JSON local
- operaciones reales de create/start/stop/list sobre VMs
- troubleshooting de SSH, firewall, IP pública y red Docker en GCE

Tools incluidas:

- `gcloud_get_config`
- `gcloud_set_defaults`
- `gcloud_list_instances`
- `gcloud_describe_instance`
- `gcloud_start_instance`
- `gcloud_stop_instance`
- `gcloud_create_instance`
- `gcloud_list_firewall_rules`
- `gcloud_check_ssh_access`
- `gcloud_instance_network_report`
- `gcloud_export_instance_to_host`

La idea no es solo aprovisionar VMs, sino poder diagnosticar rápido lo que suele romperse en la práctica: IP pública, reglas de firewall, puertos, tags y síntomas típicos de red en hosts Docker sobre GCE.

---

## Joplin (Web Clipper)

Integración MCP nativa para que cualquier LLM cliente use Joplin de forma consistente:

- lectura: `joplin_list_notes`, `joplin_get_note`, `joplin_list_notebooks`
- búsqueda profunda: `joplin_search_notes` (soporta sintaxis avanzada de Joplin: `tag:`, `notebook:`, `any:`...)
- escritura: `joplin_create_note`, `joplin_update_note`, `joplin_delete_note`
- libretas: `joplin_create_notebook`, `joplin_rename_notebook`, `joplin_delete_notebook`
- control operativo: `joplin_status`, `joplin_get_config`, `joplin_set_config`, `joplin_set_permissions`

Config local opcional en `config/joplin_config.yaml` (ignorado por git), ejemplo en `config/joplin_config.yaml.example`.

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
copy config\gcloud_config.yaml.example config\gcloud_config.yaml
```

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

## Configuración Google Cloud

`config/gcloud_config.yaml`:

```yaml
gcloud:
  project: "project-0bbed615-3203-4957-a27"
  default_zone: "europe-west1-b"
  default_region: "europe-west1"
  ssh_user: "Edu"
  service_account_key_file: "C:/Users/Edu/Downloads/project-0bbed615-3203-4957-a27-677a9255cbd7.json"
  gcloud_bin: "C:/Users/Edu/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
  command_timeout_seconds: 60
```

El fichero real está en `.gitignore`, así que se puede guardar la ruta local del JSON sin contaminar el repo.

---

## Uso básico

```text
# Hosts manuales
list_hosts()

# SAP Basis por SSH
ssh_connect(alias="sapapp1")
sap_list_instances(connection="sapapp1")
sap_check_work_processes(instance_nr="00", connection="sapapp1")

# Oracle / SQL Server / HANA
oracle_test_connection(alias="oraprd")
mssql_check_agent_jobs(alias="sqlprd", only_failed=True)
hana_backup_catalog(days_back=3)

# Google Cloud
gcloud_get_config()
gcloud_list_instances(status_filter="RUNNING")
gcloud_describe_instance(instance_name="abap-docker-host")
gcloud_check_ssh_access(instance_name="abap-docker-host")
gcloud_instance_network_report(instance_name="abap-docker-host", ports="22,3200,50000")
gcloud_export_instance_to_host(instance_name="abap-docker-host", alias="a4hgcp", key_path="C:/Users/Edu/.ssh/google_compute_engine")
```

---

## Hosts soportados (`config/hosts.yaml`)

```yaml
hosts:
  - name: sap_prod_app
    alias: sapapp1
    type: linux_ssh
    ip: 192.168.1.10
    port: 22
    user: root
    key_path: ~/.ssh/id_rsa
    tags: [sap, production, abap]
```

`hosts.yaml` sigue siendo el inventario manual para SSH/DB. Google Cloud no depende de ese fichero, porque el inventario de VMs sale dinámicamente del proyecto GCP.

---

## Seguridad

- `config/hosts.yaml` en `.gitignore`
- `config/hana_config.yaml` en `.gitignore`
- `config/gcloud_config.yaml` en `.gitignore`
- DML en Oracle/MSSQL requiere `confirm_dml=True`
- DDL en HANA requiere `confirm=True`
- `_safe_identifier()` y validaciones de entrada en los módulos de datos
- comandos locales filtrados por `security_config.yaml`

---

## Tests

```bat
.venv\Scripts\python.exe -m pytest tests\ -q
```

Suite actual esperada tras la ampliación Google Cloud: `30 passed`.

---

## Stack

Python 3.11+ · fastmcp · paramiko · oracledb · pyodbc · hdbcli · psutil · gcloud CLI

---

## Basado en

[DesktopCommanderPy](https://github.com/eduardoddddddd/DesktopCommanderPy)

## Licencia

MIT
