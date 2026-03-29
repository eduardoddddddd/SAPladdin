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

## Estado actual: SESIÓN 3 COMPLETADA — 2026-03-29
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

### Ficheros PENDIENTES ❌
- README.md                ← pendiente (mínimo necesario para el repo)
- tests/test_basic.py      ← pendiente (smoke tests)
- scripts/_git_setup.bat   ← pendiente
- scripts/_install.bat     ← pendiente
- config/hosts.yaml        ← el usuario debe crearlo desde hosts.yaml.example (NO va al repo)

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

## Próxima sesión — tareas pendientes por orden
1. README.md (descripción, instalación, uso, lista de tools)
2. tests/test_basic.py (smoke tests: importar server, list_hosts vacío, test_host_connection)
3. scripts/_install.bat (crear venv, pip install -e ., copiar example)
4. Verificar que el servidor arranca: python main.py --help
5. Instalar dependencias y probar: python -c "from core.server import get_server; print('OK')"
6. Implementar integración SSH↔hosts.yaml más robusta (actualmente usa try/except en ssh_connect)
7. Añadir herramientas SAP-específicas futuras:
   - sap_rfc_call (pyrfc — requiere SAP NW RFC SDK, no puro Python)
   - sap_check_work_processes (via SSH + dpmon)
   - sap_list_instances (via SSH + sapcontrol)
   - oracle_check_tablespace_sap (query específica para tablas SAP)

## Decisiones de diseño tomadas
- oracledb en thin mode (no necesita Oracle Client instalado) ← decisión clave
- paramiko para SSH (puro Python, sin openssh local necesario)
- hosts.yaml en .gitignore siempre (contiene credenciales)
- imports condicionales: el server arranca aunque falte un driver
- confirm_dml=True requerido para INSERT/UPDATE/DELETE/DROP (Oracle y MSSQL)
- pool de conexiones en memoria (dict global por módulo)
