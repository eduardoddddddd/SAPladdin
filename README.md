# SAPladdin

**Idioma:** Español | [English](README.en.md)

**SAPladdin** es un servidor **MCP** construido en Python/FastMCP para operación técnica real sobre SAP Basis, administración Linux/Windows, Google Cloud, Joplin y bases de datos empresariales como SAP HANA, Oracle y SQL Server.

Proporciona a clientes de IA compatibles con MCP una capa controlada de herramientas para leer, diagnosticar y operar sistemas reales desde flujos de trabajo en lenguaje natural.

![Infografía SAPladdin MCP](https://github.com/user-attachments/assets/d93150ad-c687-4f04-b59d-18a37fbdb8ec)

## Qué Es MCP

**MCP**, o **Model Context Protocol**, es un protocolo que permite a las aplicaciones de IA conectarse a herramientas externas, fuentes de datos y sistemas reales mediante una interfaz estándar.

Sin MCP, un LLM normalmente está limitado a lo que ya está en la conversación, a un fichero adjunto o a integraciones puntuales hechas a medida. Con MCP, el modelo puede descubrir y llamar herramientas expuestas por un servidor: listar ficheros, consultar una base de datos, inspeccionar un host remoto, leer documentación, crear una nota o ejecutar una comprobación operativa.

En términos prácticos:

- el **cliente de IA** es la aplicación donde el usuario conversa con el modelo, como Codex, Claude Desktop, Cursor, Claude Code o LM Studio;
- el **servidor MCP** es el proceso local o remoto que expone herramientas;
- las **herramientas** son operaciones definidas, como `gcloud_list_instances`, `ssh_execute`, `sap_check_work_processes` o `joplin_search_notes`;
- los **sistemas destino** son los servicios reales detrás de esas herramientas: filesystem, shell, hosts SSH, sistemas SAP, bases de datos, Google Cloud y Joplin.

SAPladdin ocupa el papel de servidor MCP dentro de esa cadena.

## Qué Hace SAPladdin

SAPladdin convierte un asistente de IA en un plano de control operativo para infraestructura y trabajo técnico alrededor de SAP.

Está pensado para usuarios técnicos que necesitan acceso rápido y repetible a contexto operativo sin saltar constantemente entre terminales, clientes de base de datos, checks SAP, consolas cloud y sistemas de documentación.

Flujos típicos:

- comprobar instancias SAP, work processes, colas de dispatcher, kernel, alertas, logs de sistema y short dumps;
- conectar con sistemas Linux o Windows por SSH y ejecutar comandos controlados;
- listar y diagnosticar instancias de Google Compute Engine usando el CLI local `gcloud`;
- consultar HANA Cloud, Oracle y SQL Server para comprobaciones operativas;
- leer, buscar y escribir notas en Joplin mediante la API local de Web Clipper;
- trabajar con ficheros locales, procesos y sesiones de shell desde un único cliente MCP;
- mantener un inventario manual de hosts para sistemas que no se descubren dinámicamente.

## Objetivos De Diseño

SAPladdin es deliberadamente práctico.

| Objetivo | Significado |
|---|---|
| Operación real | Las herramientas están pensadas para tareas que un administrador sí hace: comprobar, diagnosticar, listar, arrancar, parar, consultar, exportar y documentar. |
| MCP nativo | Las capacidades se exponen como herramientas MCP para que los clientes compatibles puedan descubrirlas y usarlas de forma consistente. |
| Local-first | La configuración y las credenciales permanecen en local. Los ficheros sensibles quedan fuera de git. |
| `gcloud`-first para GCP | Las operaciones de Google Cloud reutilizan el CLI `gcloud` ya configurado en el puesto, sin duplicar autenticación en otra capa. |
| Modularidad | SAP, SSH, ficheros, procesos, GCP, Joplin y bases de datos viven en módulos separados. |
| Seguridad conservadora | Las operaciones destructivas requieren confirmación explícita cuando aplica, y los secretos no se suben al repositorio. |

## Arquitectura

```text
Usuario
  |
  v
Cliente de IA compatible con MCP
  |
  v
Servidor MCP SAPladdin
  |
  +-- Filesystem y shell local
  +-- Procesos locales y sesiones interactivas
  +-- Hosts SSH
  +-- Checks SAP Basis por SSH / sapcontrol
  +-- SAP HANA Cloud
  +-- Oracle
  +-- SQL Server
  +-- Google Cloud mediante gcloud
  +-- Joplin mediante Web Clipper
```

El cliente envía llamadas de herramienta a SAPladdin. SAPladdin ejecuta la operación local o remota y devuelve una salida estructurada que el cliente de IA puede resumir, comparar, explicar o usar como siguiente paso de un flujo operativo.

## Capacidades

SAPladdin expone un conjunto amplio de herramientas para administración de sistemas y operación SAP-adjacent.

| Área | Ejemplos | Propósito |
|---|---|---|
| Filesystem | lectura, escritura, edición, búsqueda, listado | Inspeccionar y gestionar ficheros locales dentro del modelo de seguridad configurado. |
| Terminal | ejecución de comandos, salida streaming | Ejecutar PowerShell o shell local desde un cliente MCP. |
| Procesos | listar, arrancar, matar, interactuar, sesiones | Gestionar procesos locales y sesiones interactivas. |
| SSH | conectar, ejecutar, subir, descargar | Operar hosts Linux o Windows por SSH. |
| SAP Basis | instancias, work processes, alertas, logs, dumps | Diagnosticar sistemas SAP NetWeaver desde conversación. |
| SAP HANA Cloud | test, query, DDL, schemas, backup catalog | Consultar e inspeccionar entornos HANA Cloud. |
| Oracle | test, query, schemas, tablespace, backup status | Realizar comprobaciones orientadas a DBA Oracle. |
| SQL Server | test, query, databases, table description, agent jobs | Realizar comprobaciones operativas de SQL Server. |
| Google Cloud | config, list, describe, start, stop, create, firewall, network report | Operar Google Compute Engine mediante `gcloud`. |
| Joplin | status, search, get, create, update, notebooks, permisos | Usar Joplin como base de conocimiento operativa. |
| Inventario de hosts | list, add, remove, test | Mantener alias reutilizables para SSH y bases de datos. |

Para una fotografía operativa más detallada:

- [`docs/CONTEXT.md`](docs/CONTEXT.md)
- [`docs/SAPladdin_MCP_Informe_A4H_20260330.md`](docs/SAPladdin_MCP_Informe_A4H_20260330.md)

## Instalación Resumida

Este README deja la instalación en formato breve. La configuración específica por cliente está en [`docs/CLIENT_SETUP.md`](docs/CLIENT_SETUP.md).

### Opción 1: Instalación Rápida En Windows

```bat
git clone https://github.com/eduardoddddddd/SAPladdin.git C:\Users\Edu\SAPladdin
cd C:\Users\Edu\SAPladdin
scripts\_install.bat
```

### Opción 2: Entorno Virtual Manual

```bat
cd C:\Users\Edu\SAPladdin
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
copy config\hosts.yaml.example config\hosts.yaml
copy config\gcloud_config.yaml.example config\gcloud_config.yaml
copy config\joplin_config.yaml.example config\joplin_config.yaml
```

### Opción 3: Instalación De Desarrollo

```bat
cd C:\Users\Edu\SAPladdin
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Para la configuración completa en Codex, Claude Desktop, Claude Code, Cursor, LM Studio y notas sobre HTTP/SSE:

- [`docs/CLIENT_SETUP.md`](docs/CLIENT_SETUP.md)

## Configuración MCP Mínima

La mayoría de clientes locales usan una configuración MCP por `stdio` similar a esta:

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

Esto es solo la forma mínima. Las rutas exactas y la ubicación del fichero de configuración dependen de cada cliente.

Consulta [`docs/CLIENT_SETUP.md`](docs/CLIENT_SETUP.md) para la guía específica.

## Ficheros De Configuración

SAPladdin usa ficheros de ejemplo en `config/` y mantiene las credenciales reales fuera de git.

| Fichero | Propósito | En git |
|---|---|---|
| `config/hosts.yaml.example` | Ejemplo de inventario manual de hosts | Sí |
| `config/gcloud_config.yaml.example` | Ejemplo de configuración para Google Cloud CLI | Sí |
| `config/hana_config.yaml.example` | Ejemplo de configuración HANA Cloud | Sí |
| `config/joplin_config.yaml.example` | Ejemplo de configuración de Joplin Web Clipper | Sí |
| `config/security_config.yaml` | Reglas de seguridad, comandos y rutas | Sí |
| `config/hosts.yaml` | Inventario local real de hosts | No |
| `config/gcloud_config.yaml` | Configuración local real de GCP | No |
| `config/hana_config.yaml` | Configuración local real de HANA | No |
| `config/joplin_config.yaml` | Token y configuración local real de Joplin | No |

No subas tokens, claves de service account, credenciales de base de datos ni secretos de hosts.

## Modelo Google Cloud

La integración con Google Cloud es deliberadamente `gcloud`-first.

SAPladdin envuelve comandos `gcloud --format=json` porque muchos puestos de operación ya tienen una configuración funcional del CLI de Google Cloud, proyecto activo, autenticación y SSH. Así se evita duplicar flujos de autenticación en Python y se mantiene la fuente de verdad alineada con el entorno local del operador.

Las herramientas de Google Cloud incluyen listado y descripción de instancias, arranque/parada, creación de VMs, inspección de firewall, comprobaciones de SSH, informes de red y exportación de una instancia descubierta al inventario manual de hosts.

Para más contexto operativo, consulta [`docs/CONTEXT.md`](docs/CONTEXT.md).

## Integración Con Joplin

SAPladdin se integra con Joplin mediante la API local de Web Clipper, normalmente disponible en:

```text
http://127.0.0.1:41184
```

Esto permite usar Joplin como base de conocimiento operativa desde un cliente MCP: buscar notas previas, recuperar detalles, crear registros nuevos, actualizar notas existentes y gestionar libretas cuando los permisos lo permiten.

El token real debe vivir solo en configuración local y no debe subirse al repositorio.

## Prompts De Ejemplo

Una vez conectado SAPladdin al cliente MCP, los prompts pueden escribirse como peticiones naturales de operación:

```text
Lista las instancias de Google Cloud en ejecución y resume cualquier cosa rara.
```

```text
Conecta al alias sapapp1, comprueba las instancias SAP y muestra el estado de los work processes.
```

```text
Busca en Joplin notas sobre la última incidencia de A4H y resume la línea temporal.
```

```text
Comprueba el estado de tablespaces Oracle para el alias oraprd y destaca usos críticos.
```

```text
Ejecuta un informe de red para la instancia GCE abap-docker-host en los puertos 22, 3200 y 50000.
```

## Estructura Del Repositorio

```text
SAPladdin/
  config/                 Configuración de ejemplo y reglas de seguridad
  core/
    server.py             Ensamblado del servidor FastMCP
    hosts.py              Helpers del inventario de hosts
    tools/                Módulos de herramientas MCP
  docs/                   Documentación detallada de setup y operación
  scripts/                Scripts de instalación y smoke test
  tests/                  Suite pytest
  main.py                 Punto de entrada
  pyproject.toml          Metadatos del paquete y herramientas
```

## Notas De Seguridad

SAPladdin es una herramienta de operador. Puede tocar sistemas reales, ejecutar comandos y consultar infraestructura real.

Úsalo con el mismo cuidado que aplicarías a una sesión de terminal con privilegios:

- mantén credenciales en ficheros locales ignorados por git;
- revisa permisos antes de habilitar operaciones de escritura o borrado;
- usa usuarios de base de datos de solo lectura cuando sea posible;
- valida comandos antes de ejecutarlos contra hosts de producción;
- mantén las operaciones destructivas detrás de confirmación explícita;
- considera los clientes MCP como parte del perímetro de confianza operativo.

El repositorio ignora deliberadamente los principales ficheros locales con credenciales o configuración sensible.

## Tests

Ejecutar la suite:

```bat
.venv\Scripts\python.exe -m pytest tests\ -q
```

Instalar dependencias de desarrollo si hace falta:

```bat
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Stack Tecnológico

- Python 3.11+
- FastMCP
- Paramiko
- psutil
- PyYAML
- OracleDB Python driver
- pyodbc
- SAP HANA `hdbcli`
- Google Cloud CLI
- Joplin Web Clipper API

## Documentación

| Documento | Descripción |
|---|---|
| [`docs/CLIENT_SETUP.md`](docs/CLIENT_SETUP.md) | Configuración MCP por cliente: Codex, Claude Desktop, Claude Code, Cursor, LM Studio y uso HTTP/SSE. |
| [`docs/CONTEXT.md`](docs/CONTEXT.md) | Contexto operativo, inventario de herramientas, notas de arquitectura y decisiones conocidas. |
| [`docs/SAPladdin_MCP_Informe_A4H_20260330.md`](docs/SAPladdin_MCP_Informe_A4H_20260330.md) | Ejemplo de informe real de capacidades SAP/GCP. |
| [`docs/assets/sapladdin-mcp-infografia.svg`](docs/assets/sapladdin-mcp-infografia.svg) | Asset fuente de la infografía del repositorio. |

## Estado

SAPladdin es un servidor MCP de infraestructura personal en evolución. Conviene entenderlo como una capa de integración operativa, no como un producto SaaS cerrado.

El repositorio público documenta la arquitectura y patrones reutilizables; las credenciales reales y la configuración específica del puesto permanecen en local.

## Licencia

MIT

## Créditos

SAPladdin se basa en ideas y patrones operativos de [DesktopCommanderPy](https://github.com/eduardoddddddd/DesktopCommanderPy), extendidos hacia SAP Basis, administración de bases de datos, Google Cloud y gestión de conocimiento operativo con Joplin.
