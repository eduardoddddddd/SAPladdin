# SAPladdin — CONTEXT.md
# Documento de estado del proyecto para continuidad entre sesiones LLM.
# AL EMPEZAR UNA SESIÓN NUEVA: pega el contenido de este fichero como primer mensaje.

## ¿Qué es SAPladdin?
MCP Server definitivo para SAP Basis Admin, Linux Admin, Windows Admin y DBAs.
Basado en DesktopCommanderPy (C:\Users\Edu\DesktopCommanderPy), extendido con:
- SSH a Linux/Windows remotos (paramiko)
- Oracle DB (oracledb thin mode — sin Oracle Client)
- SQL Server (pyodbc)
- SAP HANA Cloud (hdbcli — ya funciona en DCPy)
- Inventario de hosts (config/hosts.yaml)

## Ubicación local
C:\Users\Edu\SAPladdin\

## Repo GitHub
https://github.com/eduardoddddddd/SAPladdin
(repo creado manualmente por el usuario en GitHub)

## Estado actual: SESIÓN 4 COMPLETADA — 2026-03-29
### Ficheros creados y COMPLETOS ✅
- .gitignore
- pyproject.toml
- requirements.txt / requirements-dev.txt
- main.py
- core/__init__.py
- core/tools/__init__.py
- core/server.py          ← FastMCP + registro condicional de todos los módulos
- core/hosts.py           ← gestor de hosts.yaml (get_host_config, _load/_save)
- core/tools/utils.py     ← copiado de DCPy
- core/tools/session_manager.py  ← copiado de DCPy
- core/tools/process.py   ← copiado de DCPy
- core/tools/terminal.py  ← copiado de DCPy
- core/tools/filesystem.py ← copiado de DCPy
- core/tools/process_sessions.py ← copiado de DCPy
- core/tools/hana.py      ← copiado literal de DCPy via PowerShell Copy-Item ✅
- core/tools/ssh.py       ← NUEVO (paramiko, pool de conexiones, ssh_connect/execute/upload/download/list/disconnect)
- core/tools/oracle.py    ← NUEVO (oracledb thin, test/query/list_schemas/describe/system_info)
- core/tools/mssql.py     ← NUEVO (pyodbc, test/query/list_databases/describe_table)
- core/tools/hosts_mgmt.py ← NUEVO (list_hosts/get_host/add_host/remove_host/test_host_connection)
- config/security_config.yaml
- config/hosts.yaml.example
- config/hana_config.yaml.example ← copiado de DCPy
- README.md
- tests/test_filesystem_and_hosts.py
- scripts/_install.bat
- scripts/_git_setup.bat

### Cambios cerrados en sesión 4 ✅
- Repo GitHub creado y `origin/main` publicado: https://github.com/eduardoddddddd/SAPladdin
- `search_files()` corregido:
  - el flag `case_sensitive` antes estaba invertido
  - además trataba `"false"` como truthy en matching por nombre
- `ssh_connect()` ahora acepta de verdad `ssh_connect(alias="...")` sin exigir `host`
- `ssh_connect()` devuelve error claro si no puede resolver alias/host incluso cuando `paramiko` no está instalado
- `add_host()` ahora distingue mejor Oracle `service` de MSSQL `database`
- Añadidos tests iniciales para filesystem/hosts/ssh sin depender de FastMCP ni drivers externos
- Añadidas primeras tools SAP por SSH:
  - `sap_list_instances`
  - `sapcontrol_get_process_list`
  - `sap_check_work_processes`

### Ficheros PENDIENTES ❌
- config/hosts.yaml        ← el usuario debe crearlo desde hosts.yaml.example (NO va al repo)
- tests de integración del servidor (`core.server`) cuando el venv tenga `fastmcp`
- endurecer consultas SQL con identificadores interpolados en HANA/Oracle/MSSQL
- herramientas SAP específicas por SSH/RFC

## Diseño clave: imports condicionales en server.py
SSH/Oracle/MSSQL se importan dentro de try/except ImportError.
Si el módulo no está instalado, el servidor arranca igual sin esas tools.
Esto permite arrancar sin tener todos los drivers instalados.

## Cómo añadir un host (flujo de uso)
1. Copiar config/hosts.yaml.example → config/hosts.yaml
2. Editar con IPs/credenciales reales
3. En Claude: usar tool add_host() o editar el yaml directamente
4. Usar test_host_connection(alias) para verificar conectividad TCP
5. Para SSH: ssh_connect(alias) — usa automáticamente datos de hosts.yaml
6. Para Oracle: oracle_test_connection(alias)
7. Para MSSQL: mssql_test_connection(alias)

## Arquitectura de conexiones
- SSH: pool en memoria (_ssh_pool dict) — conexiones viven mientras el server esté activo
- Oracle: pool en memoria (_oracle_pool dict)
- MSSQL: pool en memoria (_mssql_pool dict)
- HANA: sin pool — conexión por query (igual que en DCPy original)

## Dependencias Python
fastmcp>=2.0.0, pyyaml, psutil, aiofiles, pathspec,
paramiko>=3.4, oracledb>=2.0, pyodbc>=5.0, hdbcli>=2.0

## Instalación desde cero
```
cd C:\Users\Edu\SAPladdin
python -m venv .venv
.venv\Scripts\activate
pip install -e .
# Copiar config/hosts.yaml.example → config/hosts.yaml y rellenar
# Configurar Claude Desktop: ver README.md
python main.py   # stdio para Claude Desktop
```

## Configuración Claude Desktop (claude_desktop_config.json)
```json
{
  "mcpServers": {
    "SAPladdin": {
      "command": "C:\\Users\\Edu\\SAPladdin\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Edu\\SAPladdin\\main.py"],
      "env": {}
    }
  }
}
```

## Verificaciones ejecutadas en sesión 4
- `python main.py --help` → OK
- `python -m compileall core tests main.py` → OK
- comprobación manual de `search_files()` corregido → OK
- comprobación manual de `add_host(... host_type='mssql', database=...)` → OK
- comprobación manual de `ssh_connect(alias='missing-host')` → devuelve mensaje claro
- `python -c "from core.server import get_server"` sigue fallando en este entorno actual porque falta `fastmcp` instalado

## Próxima sesión — tareas pendientes por orden
1. Crear/activar venv e instalar dependencias con `scripts\_install.bat`
2. Verificar import real del servidor: `python -c "from core.server import get_server; print(type(get_server()).__name__)"`
3. Ejecutar `pytest`
4. Añadir smoke tests de `core.server` con `fastmcp` instalado
5. Endurecer SQL interpolado en `core/tools/hana.py`, `core/tools/oracle.py` y `core/tools/mssql.py`
6. Añadir primeras tools SAP por SSH:
   - hechas en sesión 5, falta validación real contra host SAP
7. Evaluar futura integración RFC (`pyrfc`) solo si hay SDK disponible

## Decisiones de diseño tomadas
- oracledb en thin mode (no necesita Oracle Client instalado) ← decisión clave
- paramiko para SSH (puro Python, sin openssh local necesario)
- hosts.yaml en .gitignore siempre (contiene credenciales)
- imports condicionales: el server arranca aunque falte un driver
- confirm_dml=True requerido para INSERT/UPDATE/DELETE/DROP (Oracle y MSSQL)
- pool de conexiones en memoria (dict global por módulo)
- tests iniciales enfocados en módulos sin dependencias pesadas para no bloquear la validación local
