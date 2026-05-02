# SAPladdin

**SAPladdin** is a Python/FastMCP server for real technical operations across SAP Basis, Linux/Windows administration, Google Cloud, Joplin and enterprise databases such as SAP HANA, Oracle and SQL Server.

It gives MCP-compatible AI clients a controlled tool layer for reading, diagnosing and operating real systems from natural-language workflows.

![SAPladdin MCP infographic](https://github.com/user-attachments/assets/d93150ad-c687-4f04-b59d-18a37fbdb8ec)

## What Is MCP?

**MCP**, or **Model Context Protocol**, is a protocol that lets AI applications connect to external tools, data sources and systems through a standard interface.

Without MCP, an LLM is usually limited to what is already in the conversation, a file upload, or custom one-off integrations. With MCP, the model can discover and call tools exposed by a server: list files, query a database, inspect a remote host, read documentation, create a note, or run an operational check.

In practical terms:

- the **AI client** is the application where the user talks to the model, such as Codex, Claude Desktop, Cursor, Claude Code or LM Studio;
- the **MCP server** is the local or remote process that exposes tools;
- the **tools** are strongly defined operations such as `gcloud_list_instances`, `ssh_execute`, `sap_check_work_processes` or `joplin_search_notes`;
- the **target systems** are the real services behind those tools: filesystems, shells, SSH hosts, SAP systems, databases, Google Cloud and Joplin.

SAPladdin is the MCP server in that chain.

## What SAPladdin Does

SAPladdin turns an AI assistant into an operator-facing control plane for infrastructure and SAP-adjacent work.

It is designed for technical users who need fast, repeatable access to operational context without manually switching between terminals, database clients, SAP checks, cloud consoles and documentation systems.

Typical workflows include:

- checking SAP instances, work processes, dispatcher queues, kernel information, alerts, system logs and short dumps;
- connecting to Linux or Windows systems over SSH and executing controlled commands;
- listing and diagnosing Google Compute Engine instances through the local `gcloud` CLI;
- querying HANA Cloud, Oracle and SQL Server for operational checks;
- reading, searching and writing Joplin notes through the local Web Clipper API;
- working with local files, processes and shell sessions from a single MCP-compatible client;
- maintaining a manual host inventory for systems that are not discovered dynamically.

## Design Goals

SAPladdin is intentionally practical rather than theoretical.

| Goal | Meaning |
|---|---|
| Real operations | Tools are built around tasks that administrators actually perform: check, diagnose, list, start, stop, query, export and document. |
| MCP-native | Capabilities are exposed as MCP tools, so compatible clients can discover and call them consistently. |
| Local-first | Configuration and credentials stay local. Sensitive files are excluded from git. |
| `gcloud`-first for GCP | Google Cloud operations reuse the already configured `gcloud` CLI instead of requiring a separate SDK-first setup. |
| Modular tools | SAP, SSH, files, processes, GCP, Joplin and databases live in separate modules. |
| Conservative safety | Destructive operations require explicit confirmation where implemented, and secrets are kept out of the repository. |

## Architecture

```text
User
  |
  v
MCP-compatible AI client
  |
  v
SAPladdin MCP server
  |
  +-- Filesystem and local shell
  +-- Local processes and interactive sessions
  +-- SSH targets
  +-- SAP Basis checks over SSH / sapcontrol
  +-- SAP HANA Cloud
  +-- Oracle
  +-- SQL Server
  +-- Google Cloud through gcloud
  +-- Joplin through Web Clipper
```

The client sends tool calls to SAPladdin. SAPladdin performs the actual local or remote operation and returns structured output that the AI client can summarize, compare, explain or use as the next step in a workflow.

## Capabilities

SAPladdin currently exposes a broad toolset for system administration and SAP-related operations.

| Area | Examples | Purpose |
|---|---|---|
| Filesystem | read, write, edit, search, list | Inspect and manage local files within the configured safety model. |
| Terminal | command execution, streaming output | Run local PowerShell or shell commands from an MCP client. |
| Processes | list, start, kill, interact, sessions | Manage local processes and interactive sessions. |
| SSH | connect, execute, upload, download | Operate Linux or Windows targets over SSH. |
| SAP Basis | instances, work processes, alerts, logs, dumps | Diagnose SAP NetWeaver-style systems from conversation. |
| SAP HANA Cloud | test, query, DDL, schemas, backup catalog | Query and inspect HANA Cloud environments. |
| Oracle | test, query, schemas, tablespace, backup status | Perform Oracle DBA-oriented checks. |
| SQL Server | test, query, databases, table description, agent jobs | Perform SQL Server operational checks. |
| Google Cloud | config, list, describe, start, stop, create, firewall, network report | Operate Google Compute Engine through `gcloud`. |
| Joplin | status, search, get, create, update, notebooks, permissions | Use Joplin as an operational knowledge base. |
| Hosts inventory | list, add, remove, test | Maintain reusable system aliases for SSH and database work. |

For a deeper operational snapshot, see:

- [`docs/CONTEXT.md`](docs/CONTEXT.md)
- [`docs/SAPladdin_MCP_Informe_A4H_20260330.md`](docs/SAPladdin_MCP_Informe_A4H_20260330.md)

## Installation Overview

This README keeps installation intentionally short. Client-specific setup belongs in [`docs/CLIENT_SETUP.md`](docs/CLIENT_SETUP.md).

### Option 1: Quick Windows Install

```bat
git clone https://github.com/eduardoddddddd/SAPladdin.git C:\Users\Edu\SAPladdin
cd C:\Users\Edu\SAPladdin
scripts\_install.bat
```

### Option 2: Manual Virtual Environment

```bat
cd C:\Users\Edu\SAPladdin
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
copy config\hosts.yaml.example config\hosts.yaml
copy config\gcloud_config.yaml.example config\gcloud_config.yaml
copy config\joplin_config.yaml.example config\joplin_config.yaml
```

### Option 3: Development Install

```bat
cd C:\Users\Edu\SAPladdin
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

For full client configuration, including Codex, Claude Desktop, Claude Code, Cursor, LM Studio and HTTP/SSE notes, use:

- [`docs/CLIENT_SETUP.md`](docs/CLIENT_SETUP.md)

## Minimal MCP Client Configuration

Most local clients use a `stdio` MCP configuration similar to this:

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

This is only the minimal shape. Exact file paths and configuration locations depend on the client.

See [`docs/CLIENT_SETUP.md`](docs/CLIENT_SETUP.md) for the dedicated setup guide.

## Configuration Files

SAPladdin uses example configuration files in `config/` and keeps real credentials out of git.

| File | Purpose | In git |
|---|---|---|
| `config/hosts.yaml.example` | Example manual host inventory | Yes |
| `config/gcloud_config.yaml.example` | Example Google Cloud CLI configuration | Yes |
| `config/hana_config.yaml.example` | Example HANA Cloud configuration | Yes |
| `config/joplin_config.yaml.example` | Example Joplin Web Clipper configuration | Yes |
| `config/security_config.yaml` | Safety and command/path rules | Yes |
| `config/hosts.yaml` | Real local host inventory | No |
| `config/gcloud_config.yaml` | Real local GCP settings | No |
| `config/hana_config.yaml` | Real local HANA settings | No |
| `config/joplin_config.yaml` | Real local Joplin token/settings | No |

Do not commit real tokens, service account keys, database credentials or host secrets.

## Google Cloud Model

The Google Cloud integration is deliberately `gcloud`-first.

SAPladdin wraps `gcloud --format=json` commands because many operator workstations already have a working Google Cloud CLI configuration, active project, authentication and SSH setup. This avoids duplicating authentication flows in Python and keeps the source of truth aligned with the local operator environment.

Google Cloud tools include instance listing, description, start/stop operations, VM creation, firewall inspection, SSH access checks, network reports and exporting a discovered instance into the manual host inventory.

For detailed operational context, see [`docs/CONTEXT.md`](docs/CONTEXT.md).

## Joplin Integration

SAPladdin integrates with Joplin through the local Web Clipper API, typically available at:

```text
http://127.0.0.1:41184
```

This allows an MCP client to use Joplin as a working operational knowledge base: search previous notes, retrieve details, create new records, update existing notes and manage notebooks when permissions allow it.

The real token belongs in local config only and must not be committed.

## Example Prompts

Once SAPladdin is connected to an MCP client, prompts can stay close to how an operator would ask for work:

```text
List running Google Cloud instances and summarize anything unusual.
```

```text
Connect to host alias sapapp1, check SAP instances and show work process status.
```

```text
Search Joplin for notes about the last A4H incident and summarize the timeline.
```

```text
Check Oracle tablespace status for alias oraprd and highlight critical usage.
```

```text
Run a network report for the GCE instance abap-docker-host on ports 22, 3200 and 50000.
```

## Repository Layout

```text
SAPladdin/
  config/                 Example configuration and safety settings
  core/
    server.py             FastMCP server assembly
    hosts.py              Host inventory helpers
    tools/                MCP tool modules
  docs/                   Detailed setup and operational documentation
  scripts/                Installation and smoke-test scripts
  tests/                  Pytest suite
  main.py                 Entry point
  pyproject.toml          Package metadata and tool configuration
```

## Security Notes

SAPladdin is an operator tool. It can touch real systems, execute commands and query real infrastructure.

Use it with the same care you would apply to a privileged terminal session:

- keep credentials in local ignored config files;
- review permissions before enabling write/delete operations;
- prefer read-only database users where possible;
- validate commands before running them against production hosts;
- keep destructive operations behind explicit confirmation;
- treat MCP clients as part of your operational trust boundary.

The repository intentionally ignores the main local credential/config files. Keep it that way.

## Testing

Run the test suite with:

```bat
.venv\Scripts\python.exe -m pytest tests\ -q
```

Install development dependencies first if needed:

```bat
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Technology Stack

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

## Documentation

| Document | Description |
|---|---|
| [`docs/CLIENT_SETUP.md`](docs/CLIENT_SETUP.md) | Client-specific MCP setup for Codex, Claude Desktop, Claude Code, Cursor, LM Studio and HTTP/SSE usage. |
| [`docs/CONTEXT.md`](docs/CONTEXT.md) | Operational context, tool inventory, architecture notes and known decisions. |
| [`docs/SAPladdin_MCP_Informe_A4H_20260330.md`](docs/SAPladdin_MCP_Informe_A4H_20260330.md) | Example real-world SAP/GCP capability report. |
| [`docs/assets/sapladdin-mcp-infografia.svg`](docs/assets/sapladdin-mcp-infografia.svg) | Repository infographic source asset. |

## Status

SAPladdin is an evolving personal infrastructure MCP server. It is best understood as an operator-grade integration layer rather than a polished SaaS product.

The public repository documents the architecture and reusable patterns, while real credentials and workstation-specific configuration remain local.

## License

MIT

## Credits

SAPladdin is based on operational ideas and patterns from [DesktopCommanderPy](https://github.com/eduardoddddddd/DesktopCommanderPy), extended toward SAP Basis, database administration, Google Cloud and Joplin-backed operational knowledge management.
