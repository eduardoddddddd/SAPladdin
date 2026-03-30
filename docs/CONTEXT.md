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

Local:

- `C:\Users\Edu\SAPladdin`

Base:

- `C:\Users\Edu\DesktopCommanderPy`

---

## Estado actual

Sesión de ampliación Google Cloud completada el `2026-03-30`.

La nueva capacidad no usa el SDK Python de GCP. Usa wrappers sobre `gcloud --format=json` para reutilizar exactamente el flujo que ya estaba validado en Windows:

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

Suite esperada tras la ampliación:

- `29 passed`

Ficheros de test:

- `tests/test_filesystem_and_hosts.py`
- `tests/test_sap_basis.py`
- `tests/test_gcloud.py`

---

## Tools disponibles: 64 total

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

---

## Estructura relevante

```text
SAPladdin/
├── config/
│   ├── hosts.yaml
│   ├── hosts.yaml.example
│   ├── hana_config.yaml.example
│   ├── gcloud_config.yaml.example
│   └── gcloud_config.yaml
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
│       └── hosts_mgmt.py
└── tests/
    ├── test_filesystem_and_hosts.py
    ├── test_sap_basis.py
    └── test_gcloud.py
```

---

## Decisiones de arquitectura

- `hosts.yaml` sigue siendo inventario manual para SSH/DB.
- Google Cloud no se mete como inventario estático principal en `hosts.yaml`.
- La fuente de verdad para VMs GCP es dinámica: `gcloud compute instances list`.
- La configuración GCP vive en `config/gcloud_config.yaml`.
- La integración MCP de Google Cloud es `gcloud-first`, no `google-cloud-python-first`.
- El valor operativo no está solo en crear/parar VMs: también en diagnosticar red, firewall, tags e IP pública.

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

Notas:

- `config/gcloud_config.yaml` está en `.gitignore`
- el JSON local se reutiliza como credencial operativa
- `gcloud.cmd` es el binario previsto en Windows

---

## Uso recomendado

Para inventario:

- `gcloud_list_instances()`
- `gcloud_describe_instance(instance_name="abap-docker-host")`

Para operación:

- `gcloud_start_instance(instance_name="sap-abap-trial")`
- `gcloud_stop_instance(instance_name="codex-test-vm")`
- `gcloud_create_instance(instance_name="test-vm", machine_type="e2-micro")`

Para troubleshooting:

- `gcloud_list_firewall_rules(port=22)`
- `gcloud_check_ssh_access(instance_name="abap-docker-host")`
- `gcloud_instance_network_report(instance_name="abap-docker-host", ports="22,3200,50000")`

Para encadenar con SSH/SAP ya existente:

- `gcloud_export_instance_to_host(instance_name="abap-docker-host", alias="a4hgcp", key_path="C:/Users/Edu/.ssh/google_compute_engine")`

---

## Conocimiento operativo importante heredado de la sesión anterior

- El firewall GCP abierto no garantiza servicio accesible.
- SSH puede estar bien y aun así SAP o Docker no salir a internet.
- En Docker sobre GCE, un caso real ya validado fue `net.ipv4.ip_forward = 0`.
- Si `22/tcp` abre pero `3200` o `50000` no, el problema ya no es acceso base a la VM sino publicación del servicio o forwarding local.
- La nueva tool `gcloud_instance_network_report` está pensada exactamente para ese tipo de diagnóstico.

---

## Próximos pasos sugeridos

1. Añadir una tool opcional para exportar una VM GCP al inventario `hosts.yaml`.
2. Añadir una tool de `gcloud compute ssh` si quieres un wrapper nativo aparte del SSH manual actual.
3. Añadir operaciones de discos estáticos e IPs reservadas si el laboratorio crece.
