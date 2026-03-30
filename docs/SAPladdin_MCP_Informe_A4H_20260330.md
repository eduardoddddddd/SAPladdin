# SAPladdin MCP — Informe de Capacidades y Estado del Sistema A4H

> **Sistema:** A4H (sapdocker / GCP) | **Fecha:** 30 marzo 2026 | **Autor:** Eduardo Abdul Malik Arias

---

## 1. ¿Qué es SAPladdin MCP?

SAPladdin es un servidor **MCP (Model Context Protocol)** desarrollado en Python + FastMCP que permite a modelos de lenguaje como Claude interactuar directamente con sistemas SAP, bases de datos HANA/Oracle/SQL Server y servidores Linux vía SSH — todo desde conversación en lenguaje natural.

| Campo | Valor |
|---|---|
| Tecnología | Python + FastMCP |
| Protocolo | MCP sobre stdio / SSE |
| Autenticación | SSH clave privada (pool de conexiones) |
| BBDDs | SAP HANA Cloud, Oracle, SQL Server |
| GitHub | github.com/eduardoddddddd |

---

## 2. Inventario de Hosts

| Alias | Tipo | IP:Puerto | Estado |
|---|---|---|---|
| `hana` | HANA Cloud | 20178d0a-...hanacloud.ondemand.com:443 | Activo |
| `gcptest` | linux_ssh | 34.76.12.188:22 | Activo |
| `saptrial` | linux_ssh | 35.195.187.144:22 | Offline |
| `sapdocker` | linux_ssh | 34.79.100.46:22 | Activo |

---

## 3. Sistema A4H — sapdocker (30/03/2026 20:19h)

### Entorno

| Parámetro | Valor |
|---|---|
| SID ABAP | A4H |
| SID HANA | HDB inst 02 |
| Host | 34.79.100.46 (GCP Ubuntu 22.04) |
| Arquitectura | Docker container `a4h` (SAP CAL ABAP on HANA) |
| Hostname SAP | vhcala4hci |
| Kernel ABAP | Release 777, Patch 500, CL 2142737 (01/07/2022) |

> sapcontrol no en PATH del host. Patrón: `sudo docker exec a4h /usr/sap/hostctrl/exe/sapcontrol`

### Procesos ABAP D00 — todos GREEN (19:59h)

| Proceso | Estado |
|---|---|
| disp+work | GREEN |
| igswd_mt | GREEN |
| gwrd | GREEN |
| icman | GREEN |

### Procesos HANA HDB02 — todos GREEN (19:49h)

| Proceso | Estado |
|---|---|
| hdbnameserver | GREEN |
| hdbindexserver | GREEN |
| hdbxsengine | GREEN |
| hdbwebdispatcher | GREEN |
| hdbcompileserver | GREEN |
| hdbpreprocessor | GREEN |
| hdbdiserver | GREEN |
| hdbdaemon | GREEN |

### Colas Dispatcher — 0 pendientes

| Cola | Actual | Pico |
|---|---|---|
| ABAP/DIA | 0 | 40 |
| ABAP/NOWP | 0 | 4 |
| ABAP/BTC | 0 | 3 |
| ABAP/SPO | 0 | 2 |
| ICM/Intern | 0 | 1 |

### Alertas CCMS

- RED: Transaction canceled 00/179 (20:15) — normal post-restart ABAP
- RED: OS Load avg 4.18 > 3.0 (19:12) — durante arranque HANA, normalizado
- GREEN: Filesystems — 83 GB libres (57% uso)

### Short Dumps (ST22)

3 entradas `Short dump after soft cancel (SAP Note 3169611)` — dumps esperados del stop controlado.

### Recursos

| Recurso | Total | Libre |
|---|---|---|
| Disco | 194 GB | 83 GB |
| RAM | 31 GB | 15 GB |
| Swap | — | Sin swap (Docker) |

---

## 4. Capacidades de LECTURA

| Herramienta MCP | Equiv. SAP | Descripción |
|---|---|---|
| `GetProcessList` (sapcontrol) | SM51/SM50 | Estado procesos ABAP y HANA |
| `GetVersionInfo` (sapcontrol) | SM51 kernel | Versión kernel, patch, changelist |
| `GetAlertTree` (sapcontrol) | RZ20/CCMS | Árbol alertas sistema, FS, OS |
| `GetQueueStatistic` (sapcontrol) | SM50 colas | Colas DIA, BTC, SPO, UPD, NOWP |
| `sap_check_system_log` | SM21 | SYSLOG, filtro E/W |
| `sap_abap_short_dumps` | ST22 | Short dumps en dev_w* |
| `sap_list_sids` | — | SIDs en /usr/sap y sapservices |
| `sap_list_instances` | SM51 | Instancias SAP del host |
| `sap_kernel_info` | SM51 | Versión completa kernel |
| `sap_dispatcher_queue` | SM50 | Colas dispatcher dpmon |
| `hana_get_system_info` | HANA Studio | CPU, mem, alertas HANA Cloud |
| `hana_list_schemas` | HANA DB | Schemas del usuario |
| `hana_list_tables` | HANA DB | Tablas, vistas, Calc Views |
| `hana_execute_query` | HANA SQL | Queries SELECT |
| `hana_backup_catalog` | HANA Backup | M_BACKUP_CATALOG |
| `hana_describe_table` | HANA DB | Columnas, tipos, PK |
| `list_hosts` / `get_host` | — | Inventario hosts.yaml |
| `test_host_connection` | — | Ping TCP al puerto |
| `ssh_execute` (lectura) | — | df, ps, top, tail logs |
| `list_processes` | — | Procesos PID/CPU/mem |

---

## 5. Capacidades de EJECUCIÓN

> AVISO: ejecutan cambios reales. Usar usuarios solo lectura en producción.

| Herramienta MCP | Equiv. SAP | Descripción |
|---|---|---|
| `sap_start_instance` | SM51/STMS | Arrancar instancia SAP |
| `sap_stop_instance` | SM51/shutdown | Parar instancia SAP |
| `hana_execute_ddl` | HANA SQL | CREATE / ALTER / DROP / GRANT |
| `ssh_execute` (escritura) | Shell | Restart, editar ficheros, scripts |
| `ssh_upload` / `ssh_download` | SFTP | Transferencia de ficheros |
| `add_host` / `remove_host` | — | Gestionar inventario |
| `write_file` / `create_directory` | — | Ficheros en servidor remoto |
| `start_process` / `kill_process` | — | Gestión de procesos |
| `oracle_execute_ddl` | Oracle | DDL Oracle |
| `mssql_execute_query` DML | SQL Server | DML SQL Server |

---

## 6. Nota Técnica: Docker exec wrapper

El sistema A4H corre dentro del contenedor `a4h`. Patrón requerido:

```bash
sudo docker exec a4h /usr/sap/hostctrl/exe/sapcontrol -nr 00 -function GetProcessList
sudo docker exec a4h /usr/sap/hostctrl/exe/sapcontrol -nr 02 -function GetProcessList
sudo docker exec a4h tail -100 /usr/sap/A4H/D00/log/SYSLOG
sudo docker exec -u hdbadm a4h hdbsql -n vhcala4hci -i 02 -u SYSTEM -d SYSTEMDB "SELECT * FROM M_DATABASE"
```

**Mejora pendiente:** `docker_exec_wrapper` por host — si `tags` incluye `docker`, las herramientas nativas envuelven automáticamente con `docker exec`.

---

## 7. Resumen Ejecutivo

```
SISTEMA A4H — 30/03/2026 20:19h
OK  HANA HDB02: 8 procesos GREEN — arranque limpio 19:49h
OK  ABAP D00:   4 procesos GREEN — disp+work, gwrd, icman, IGS
OK  Colas:      0 pendientes en todas las colas
OK  Disco:      83 GB libres | RAM: 15 GB disponibles
OJO 2 alertas RED CCMS: del propio arranque, normalizadas
INFO 3 short dumps soft cancel: esperados del restart
```

SAPladdin MCP demostró en esta sesión:
- Conectar hosts remotos GCP vía SSH en segundos
- Detectar SIDs, contenedores Docker y procesos SAP
- Ejecutar checks SM50, SM51, RZ20, ST22, SM21 sin acceso GUI
- Consultar recursos y colas del dispatcher
- Presentar información estructurada en lenguaje natural

> La integración IA + MCP + SAP Basis permite monitorización y diagnóstico en conversación natural, con contexto histórico y razonamiento.

---
*Generado por Claude (Anthropic) vía SAPladdin MCP — 30 marzo 2026*
