# SAPladdin Client Setup

Guía práctica para conectar `SAPladdin` a distintos clientes MCP y herramientas locales.

Ruta base usada en este documento:

- `C:\Users\Edu\SAPladdin`

Comando MCP local de `SAPladdin`:

- Command: `C:\Users\Edu\SAPladdin\.venv\Scripts\python.exe`
- Args: `C:\Users\Edu\SAPladdin\main.py`

## Resumen rápido

`SAPladdin` hoy expone dos transportes:

- `stdio`
- `SSE` vía `python main.py --http`

Recomendación:

- usa `stdio` siempre que el cliente lo soporte
- usa `SSE` solo si el cliente acepta ese transporte

## Matriz de compatibilidad práctica

| Cliente | Conexión directa hoy | Transporte recomendado | Nota |
|---|---|---|---|
| Codex App / Codex CLI | Sí | `stdio` | Configuración global en `~/.codex/config.toml` |
| Claude Desktop | Sí | `stdio` | `claude_desktop_config.json` |
| Claude Code | Sí | `stdio` | Puede añadirse con `claude mcp add` |
| Cursor | Sí | `stdio` | `mcp.json` |
| LM Studio | Sí | `stdio` | `mcp.json` compatible con MCP |
| Open WebUI | No directo con esta build | Requiere bridge o soporte `streamable-http` | `SAPladdin` hoy no expone `streamable-http` |

## 1. Codex App / Codex CLI

### Opción recomendada: CLI

```powershell
codex mcp add sapladdin -- "C:\Users\Edu\SAPladdin\.venv\Scripts\python.exe" "C:\Users\Edu\SAPladdin\main.py"
```

Verificar:

```powershell
codex mcp list
```

### Configuración manual

Fichero:

- `C:\Users\Edu\.codex\config.toml`

Bloque:

```toml
[mcp_servers.sapladdin]
command = 'C:\Users\Edu\SAPladdin\.venv\Scripts\python.exe'
args = ['C:\Users\Edu\SAPladdin\main.py']
```

## 2. Claude Desktop

Fichero:

- `%APPDATA%\Claude\claude_desktop_config.json`

Bloque:

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

## 3. Claude Code

### Añadir por CLI

```powershell
claude mcp add sapladdin -- "C:\Users\Edu\SAPladdin\.venv\Scripts\python.exe" "C:\Users\Edu\SAPladdin\main.py"
```

### Alternativa JSON

```json
{
  "type": "stdio",
  "command": "C:\\Users\\Edu\\SAPladdin\\.venv\\Scripts\\python.exe",
  "args": ["C:\\Users\\Edu\\SAPladdin\\main.py"]
}
```

## 4. Cursor

Fichero habitual:

- `C:\Users\Edu\.cursor\mcp.json`

Bloque:

```json
{
  "mcpServers": {
    "sapladdin": {
      "type": "stdio",
      "command": "C:\\Users\\Edu\\SAPladdin\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Edu\\SAPladdin\\main.py"]
    }
  }
}
```

Si ya existe el fichero, añade solo la entrada `sapladdin`.

## 5. LM Studio

LM Studio soporta MCP mediante `mcp.json`.

Fichero recomendado:

- `C:\Users\Edu\.lmstudio\mcp.json`

Bloque:

```json
{
  "mcpServers": {
    "sapladdin": {
      "type": "stdio",
      "command": "C:\\Users\\Edu\\SAPladdin\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Edu\\SAPladdin\\main.py"]
    }
  }
}
```

Si LM Studio te muestra una UI para instalar servidores MCP, usa exactamente estos mismos valores:

- Name: `sapladdin`
- Type: `stdio`
- Command: `C:\Users\Edu\SAPladdin\.venv\Scripts\python.exe`
- Args: `C:\Users\Edu\SAPladdin\main.py`

## 6. Open WebUI

Con la implementación actual de `SAPladdin`, no recomiendo documentar una conexión directa como si ya estuviera soportada.

Motivo:

- `SAPladdin` expone `stdio` y `SSE`
- Open WebUI suele esperar `streamable-http` para MCP directo

Opciones si quieres llegar ahí:

1. añadir soporte `streamable-http` a `SAPladdin`
2. poner un bridge/proxy delante
3. usar otro cliente MCP para la parte operativa y Open WebUI solo como frontend sin MCP directo

## 7. Modo HTTP/SSE de SAPladdin

Arranque:

```powershell
C:\Users\Edu\SAPladdin\.venv\Scripts\python.exe C:\Users\Edu\SAPladdin\main.py --http --host 127.0.0.1 --port 8080
```

URL local:

- `http://127.0.0.1:8080`

Esto solo sirve si el cliente soporta el transporte que realmente emite FastMCP en este modo.

## 8. Comprobación mínima después de conectar

Prompt recomendado:

```text
Usa el MCP SAPladdin y ejecuta:
1. gcloud_get_config()
2. gcloud_list_instances()
3. list_hosts()
Resume el resultado de cada uno.
```

## 9. Problemas típicos

### El cliente no encuentra Python

Usa la ruta completa:

- `C:\Users\Edu\SAPladdin\.venv\Scripts\python.exe`

### El cliente ve el servidor pero no arranca

Comprueba:

```powershell
C:\Users\Edu\SAPladdin\.venv\Scripts\python.exe C:\Users\Edu\SAPladdin\main.py
```

Si eso falla, el problema no es el cliente sino el entorno Python o dependencias.

### El cliente soporta MCP pero no `stdio`

Con esta build actual, necesitarás:

- otro cliente
- o añadir otro transporte al servidor

## 10. Fuentes oficiales recomendadas

- OpenAI Codex MCP: <https://developers.openai.com/codex/mcp>
- OpenAI Docs MCP quickstart: <https://developers.openai.com/learn/docs-mcp>
- Claude Code MCP: <https://docs.anthropic.com/fr/docs/claude-code/mcp>
- Cursor MCP: <https://docs.cursor.com/es/context/mcp>

Recomendación práctica:

- para operación real hoy: `Codex`, `Claude Desktop`, `Claude Code`, `Cursor` y `LM Studio`
- para `Open WebUI`: esperar a exponer un transporte adicional o meter un bridge
