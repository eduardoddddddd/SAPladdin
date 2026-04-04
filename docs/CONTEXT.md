# SAPladdin - CONTEXT.md

## Proyecto

MCP Server para SAP Basis Admin, Linux Admin, Windows Admin, DBAs y ahora también operación práctica sobre Google Cloud.

Conecta Claude o cualquier cliente MCP compatible a:

- filesystem local
- shell y procesos locales
- Linux y Windows por SSH
- SAP Basis sobre SSH
- Oracle
- SQL Server
- SAP HANA Cloud
- Google Compute Engine vía `gcloud`
- Joplin (Web Clipper local `127.0.0.1:41184`)

Local:

- `C:\Users\Edu\SAPladdin`

Base:

- `C:\Users\Edu\DesktopCommanderPy`

---

## Estado actual

### Sesión 2026-04-04 — Integración Joplin + LM Studio

Cambios realizados en esta sesión:

**Joplin Web Clipper integrado en SAPladdin:**
- `config/joplin_config.yaml` configurado con `base_url: http://127.0.0.1:41184` y token real del Web Clipper local.
- El fichero está en `.gitignore` — el token no se sube a GitHub.
- Validado: `joplin_status`, `joplin_create_note`, `joplin_get_note` funcionan correctamente desde LM Studio con Nemotron.

**SAPladdin conectado a LM Studio:**
- `C:\Users\Edu\.lmstudio\mcp.json` actualizado con `"timeout": 60000` para evitar timeouts con modelos razonadores.
- SAPladdin cargado y validado en LM Studio 0.4.9 con `nvidia/nemotron-3-nano-4b`.

**Fix Prompt Template Gemma 4 26B en LM Studio:**
- Creado `C:\Users\Edu\.lmstudio\.internal\user-concrete-model-default-config\lmstudio-community\gemma-4-26B-A4B-it-GGUF\gemma-4-26B-A4B-it-Q4_K_M.json`
- Formato correcto: clave `llm.prediction.promptTemplate` con estructura `preset/operation/load/prediction`.
- Parches aplicados al template Jinja del Gemma 4:
  - 3 líneas defensivas al inicio: `tools`, `messages`, `add_generation_prompt` con defaults.
  - Guards `is defined and is string` en los if/elif de `value['type'] | upper`.
  - Línea de output final protegida para tipos array o undefined.
- Error resuelto: `Cannot apply filter "upper" to type: UndefinedValue`.

---

### Sesión 2026-03-30 — Ampliación Google Cloud

La nueva capacidad no usa el SDK Python de GCP. Usa wrappers sobre `gcloud --format=json`:

- `gcloud` instalado localmente
- project activo: `project-0bbed615-3203-4957-a27`
- autenticación por service account con JSON local
- create/start/stop/list de VMs ya probado
- troubleshooting real de SSH, firewall, IP pública y red Docker en GCE ya documentado

---

## Tests

```bat
.venv\Scripts\python.exe -m pytest tests\ -q
```

Suite esperada:

- `29 passed`

Ficheros de test:

- `tests/test_filesystem_and_hosts.py`
- `tests/test_sap_basis.py`
- `tests/test_gcloud.py`

---

## Tools disponibles: 64 total + Joplin (12)

### Filesystem (9)

`read_file`, `write_file`, `edit_file_diff`, `list_directory`, `search_files`, `get_file_info`, `create_directory`, `move_file`, `read_multiple_files`

### Terminal + Procesos (9)

`execute_command`, `execute_command_streaming`, `list_processes`, `kill_process`, `start_process`, `read_process_output`, `interact_with_process`, `list_sessions`, `force_terminate`

### SAP HANA Cloud (9)

`hana_test_connection`, `hana_execute_query`, `hana_execute_ddl`, `hana_list_schemas`, `hana_list_tables`, `hana_describe_table`, `hana_get_row_count`, `hana_get_system_info`, `hana_backup_catalog`

### Google Cloud (11)

`gcloud_get_config`, `gcloud_set_defaults`, `gcloud_list_instances`, `gcloud_describe_instance`, `gcloud_start_instance`, `gcloud_stop_instance`, `gcloud_create_instance`, `gcloud_list_firewall_rules`, `gcloud_check_ssh_access`, `gcloud_instance_network_report`, `gcloud_export_instance_to_host`

### SSH (6)

`ssh_connect`, `ssh_execute`, `ssh_upload`, `ssh_download`, `ssh_list_connections`, `ssh_disconnect`

### SAP Basis / NetWeaver (11)

`sap_list_sids`, `sap_list_instances`, `sapcontrol_get_process_list`, `sap_check_work_processes`, `sap_start_instance`, `sap_stop_instance`, `sap_get_alerts`, `sap_kernel_info`, `sap_check_system_log`, `sap_dispatcher_queue`, `sap_abap_short_dumps`

### Oracle DB (7)

`oracle_test_connection`, `oracle_execute_query`, `oracle_list_schemas`, `oracle_describe_table`, `oracle_get_system_info`, `oracle_check_tablespace_sap`, `oracle_backup_status`

### SQL Server (5)

`mssql_test_connection`, `mssql_execute_query`, `mssql_list_databases`, `mssql_describe_table`, `mssql_check_agent_jobs`

### Hosts (5)

`list_hosts`, `get_host`, `add_host`, `remove_host`, `test_host_connection`

### Joplin (12) — nuevo 2026-04-04

`joplin_status`, `joplin_get_config`, `joplin_set_config`, `joplin_set_permissions`, `joplin_list_notebooks`, `joplin_list_notes`, `joplin_get_note`, `joplin_search_notes`, `joplin_create_note`, `joplin_update_note`, `joplin_delete_note`, `joplin_create_notebook`, `joplin_rename_notebook`, `joplin_delete_notebook`

---

## Estructura relevante

```text
SAPladdin/
├── config/
│   ├── hosts.yaml
│   ├── hosts.yaml.example
│   ├── hana_config.yaml.example
│   ├── gcloud_config.yaml.example
│   ├── gcloud_config.yaml          ← gitignore
│   └── joplin_config.yaml          ← gitignore (contiene token)
├── core/
│   ├── server.py
│   ├── hosts.py
│   └── tools/
│       ├── hana.py
│       ├── gcloud.py
│       ├── ssh.py
│       ├── sap_basis.py
│       ├── oracle.py
│       ├── mssql.py
│       ├── hosts_mgmt.py
│       └── joplin.py               ← nuevo
└── tests/
    ├── test_filesystem_and_hosts.py
    ├── test_sap_basis.py
    └── test_gcloud.py
```

---

## Configuración Joplin

`config/joplin_config.yaml` (gitignore):

```yaml
joplin:
  base_url: http://127.0.0.1:41184
  token: 'TU_TOKEN_AQUI'
  permissions:
    allow_create: true
    allow_update: true
    allow_delete: false
    allow_manage_notebooks: false
```

El token se obtiene en Joplin Desktop → Tools → Options → Web Clipper.

---

## Configuración LM Studio (externa al repo)

Ficheros relevantes en `C:\Users\Edu\.lmstudio\`:

- `mcp.json` — SAPladdin registrado con `timeout: 60000`
- `.internal\user-concrete-model-default-config\lmstudio-community\gemma-4-26B-A4B-it-GGUF\` — template Jinja parchado

---

## Decisiones de arquitectura

- `hosts.yaml` sigue siendo inventario manual para SSH/DB.
- Google Cloud no se mete como inventario estático principal en `hosts.yaml`.
- La fuente de verdad para VMs GCP es dinámica: `gcloud compute instances list`.
- La configuración GCP vive en `config/gcloud_config.yaml`.
- La integración MCP de Google Cloud es `gcloud-first`, no `google-cloud-python-first`.
- Joplin se integra vía Web Clipper local (no remoto) desde SAPladdin; el MCP remoto SSE sigue siendo el canal de Claude web.
- El token de Joplin nunca va a GitHub — `.gitignore` incluye `config/joplin_config.yaml`.

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

---

## Uso recomendado

### Joplin

```python
joplin_status()
joplin_search_notes(query="KeplerDB")
joplin_create_note(title="Sesión 2026-04-04", body="...", notebook="Bitácora")
joplin_update_note(note_id="abc123", body="contenido actualizado")
```

### Google Cloud

```python
gcloud_list_instances()
gcloud_describe_instance(instance_name="abap-docker-host")
gcloud_start_instance(instance_name="sap-abap-trial")
gcloud_export_instance_to_host(instance_name="abap-docker-host", alias="a4hgcp", key_path="C:/Users/Edu/.ssh/google_compute_engine")
```

---

## Conocimiento operativo importante

- El firewall GCP abierto no garantiza servicio accesible.
- SSH puede estar bien y aun así SAP o Docker no salir a internet.
- En Docker sobre GCE, un caso real ya validado fue `net.ipv4.ip_forward = 0`.
- LM Studio tiene timeout corto para MCPs (~10-15s) — con modelos razonadores (Nemotron, Gemma) usar `"timeout": 60000` en `mcp.json`.
- El template Jinja de Gemma 4 (lmstudio-community) tiene un bug con `value['type'] | upper` cuando el parámetro no tiene campo `type` definido — solucionado con override local.

---

## Próximos pasos

1. Refactorización profunda de Joplin MCP (sesión pendiente).
2. Añadir tool `gcloud compute ssh` wrapper nativo.
3. Añadir operaciones de discos estáticos e IPs reservadas.
