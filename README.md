# SAPladdin

**MCP Server para SAP Basis Admin, Linux Admin, Windows Admin, DBAs y operaciÃ³n prÃ¡ctica sobre Google Cloud.**

Conecta Claude o cualquier cliente MCP compatible a sistemas reales: filesystem local, procesos, SSH, SAP Basis, Oracle, SQL Server, HANA Cloud y ahora Google Compute Engine vÃ­a `gcloud`.

GuÃ­a de conexiÃ³n a clientes MCP y LLM apps:

- [docs/CLIENT_SETUP.md](docs/CLIENT_SETUP.md)

---

## Capacidades - 78 tools

| MÃ³dulo | Tools | DescripciÃ³n |
|---|---|---|
| **Filesystem** (9) | read, write, edit, search, list... | Operaciones locales con sandbox |
| **Terminal** (2) | execute_command, streaming | Shell local PS/bash |
| **Procesos** (7) | list, kill, start, interact... | GestiÃ³n + REPLs interactivos |
| **HANA Cloud** (9) | test, query, ddl, schemas, backup... | SAP HANA Cloud (`hdbcli`) |
| **Google Cloud** (11) | config, list, start, stop, create, firewall, export... | OperaciÃ³n GCE/GCP reutilizando `gcloud` |
| **Joplin** (14) | status, config, permisos, list/search/get/create/update/delete | GestiÃ³n documental de notas/libretas vÃ­a Web Clipper |
| **SSH** (6) | connect, execute, upload, download... | Acceso remoto Linux/Windows |
| **SAP Basis** (11) | instances, processes, alerts, log... | NetWeaver vÃ­a SSH |
| **Oracle** (7) | test, query, schemas, tablespace, rman... | Oracle DB thin mode |
| **SQL Server** (5) | test, query, databases, agent jobs... | SQL Server on-premise/Azure |
| **Hosts** (5) | list, add, remove, test... | Inventario manual de sistemas |

---

## Google Cloud

La integraciÃ³n nueva es deliberadamente `gcloud-first`.

No usa el SDK Python de GCP. Usa wrappers MCP sobre `gcloud --format=json` porque en este entorno ya estaban validados:

- `gcloud` instalado en Windows
- proyecto activo `project-0bbed615-3203-4957-a27`
- service account funcional con JSON local
- operaciones reales de create/start/stop/list sobre VMs
- troubleshooting de SSH, firewall, IP pÃºblica y red Docker en GCE

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

La idea no es solo aprovisionar VMs, sino poder diagnosticar rÃ¡pido lo que suele romperse en la prÃ¡ctica: IP pÃºblica, reglas de firewall, puertos, tags y sÃ­ntomas tÃ­picos de red en hosts Docker sobre GCE.

---

## Joplin (Web Clipper)

IntegraciÃ³n MCP nativa para que cualquier LLM cliente use Joplin de forma consistente:

- lectura: `joplin_list_notes`, `joplin_get_note`, `joplin_list_notebooks`
- bÃºsqueda profunda: `joplin_search_notes` (soporta sintaxis avanzada de Joplin: `tag:`, `notebook:`, `any:`...)
- escritura: `joplin_create_note`, `joplin_update_note`, `joplin_delete_note`
- libretas: `joplin_create_notebook`, `joplin_rename_notebook`, `joplin_delete_notebook`
- control operativo: `joplin_status`, `joplin_get_config`, `joplin_set_config`, `joplin_set_permissions`

Config local opcional en `config/joplin_config.yaml` (ignorado por git), ejemplo en `config/joplin_config.yaml.example`.

---

## InstalaciÃ³n rÃ¡pida

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

## ConfiguraciÃ³n Claude Desktop

AÃ±adir a `%APPDATA%\Claude\claude_desktop_config.json`:

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

## ConfiguraciÃ³n Google Cloud

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

El fichero real estÃ¡ en `.gitignore`, asÃ­ que se puede guardar la ruta local del JSON sin contaminar el repo.

---

## Uso bÃ¡sico

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

`hosts.yaml` sigue siendo el inventario manual para SSH/DB. Google Cloud no depende de ese fichero, porque el inventario de VMs sale dinÃ¡micamente del proyecto GCP.

---

## Seguridad

### Modelo de acceso

SAPladdin usa el perfil de **administrador de sistemas con acceso total**, pensado para uso personal en un entorno controlado. La configuraciÃ³n estÃ¡ en `config/security_config.yaml`.

**Filesystem:**  
`allowed_directories: []` â€” acceso a todo el sistema de archivos, sin restricciÃ³n de ruta. Equivalente al modo sin sandbox de Desktop Commander. Esto permite operar sobre cualquier ruta del disco (C:\, D:\, rutas de programa, config de sistema) sin tener que declarar cada directorio.

**Comandos bloqueados** (solo lo irreversiblemente catastrÃ³fico):

| Comando | RazÃ³n |
|---|---|
| `format c/d/e:` | DestrucciÃ³n de particiÃ³n |
| `diskpart` / `fdisk` | ManipulaciÃ³n de tabla de particiones |
| `mimikatz` | Credential dumping / ataque |
| `shutdown /s` / `halt` / `poweroff` | Apagado accidental del sistema |

Todo lo demÃ¡s estÃ¡ disponible: `icacls`, `takeown`, `reg add/delete`, `netsh`, `net user`, `net localgroup`, `iptables`, `gcloud`...

**Ficheros de credenciales** (en `.gitignore`, nunca al repo):
- `config/hosts.yaml`
- `config/hana_config.yaml`
- `config/gcloud_config.yaml`
- `config/joplin_config.yaml`
- `config/security_config.yaml`

**Confirmaciones explÃ­citas requeridas:**
- DML en Oracle/MSSQL â†’ `confirm_dml=True`
- DDL en HANA â†’ `confirm=True`
- Delete de notas Joplin â†’ `confirm=True`



## Tests

```bat
.venv\Scripts\python.exe -m pytest tests\ -q
```

Suite actual esperada tras la ampliaciÃ³n Google Cloud: `30 passed`.

---

## Stack

Python 3.11+ Â· fastmcp Â· paramiko Â· oracledb Â· pyodbc Â· hdbcli Â· psutil Â· gcloud CLI

---

## Basado en

[DesktopCommanderPy](https://github.com/eduardoddddddd/DesktopCommanderPy)

## Licencia

MIT
