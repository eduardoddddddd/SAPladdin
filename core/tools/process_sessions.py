"""
SAPladdin - Tools de procesos con estado (sesiones interactivas).
Copiado de DesktopCommanderPy — sin cambios.
"""
import asyncio, logging, os
from pathlib import Path
from typing import Annotated, Optional
from core.tools.session_manager import ProcessSession, sessions
from core.tools.utils import check_command_allowed, get_default_timeout, get_shell, load_security_config

logger = logging.getLogger(__name__)
_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "security_config.yaml"
_security_config: dict | None = None

def _cfg() -> dict:
    global _security_config
    if _security_config is None:
        _security_config = load_security_config(_CONFIG_PATH)
    return _security_config

def _blocked() -> list[str]:
    return _cfg()["security"].get("blocked_commands", [])

async def start_process(
    command: Annotated[str, "Command to run (can be interactive: python -i, bash, etc.)."],
    working_directory: Annotated[str, "Working directory. Default user home."] = "",
    timeout_seconds: Annotated[int, "Seconds to wait for initial output. 0 = default."] = 10,
) -> str:
    """Start a background process and return its PID. Use read_process_output/interact_with_process to work with it."""
    check_command_allowed(command, _blocked())
    shell_args = get_shell(_cfg())
    cwd = working_directory or str(Path.home())
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = await asyncio.create_subprocess_exec(
        *shell_args, command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd, env=env,
    )
    session = ProcessSession(pid=proc.pid, command=command, process=proc)
    task = asyncio.create_task(sessions.drain_output(session))
    session._drain_task = task
    sessions.register(session)
    t = timeout_seconds if timeout_seconds > 0 else get_default_timeout(_cfg())
    initial_lines, finished = await sessions.read_output(session, timeout_seconds=min(t, 5))
    output = "".join(initial_lines)
    status = "finished" if finished else "running"
    result = f"[PID {proc.pid}] Process started ({status})\nCommand: {command}\nCWD: {cwd}\n"
    result += f"\n--- Initial output ---\n{output.rstrip()}" if output else "\n(no initial output yet)"
    return result

async def read_process_output(
    pid: Annotated[int, "PID from start_process."],
    timeout_seconds: Annotated[float, "Max seconds waiting for new output. Default 5."] = 5.0,
    max_lines: Annotated[int, "Max lines to return. Default 200."] = 200,
) -> str:
    """Read accumulated output from a running process."""
    session = sessions.get(pid)
    if session is None:
        return f"[ERROR] No session with PID {pid}. Use list_sessions to see active PIDs."
    lines, finished = await sessions.read_output(session, timeout_seconds=timeout_seconds, max_lines=max_lines)
    output = "".join(lines)
    status = f"finished (exit={session.exit_code})" if finished else "running"
    result = f"[PID {pid}] Status: {status}  |  Lines: {len(lines)}  |  Total: {session.total_lines}\n"
    result += f"\n{output.rstrip()}" if output else "\n(no new output)"
    if finished: result += f"\n\n[Process finished, exit code {session.exit_code}]"
    return result

async def interact_with_process(
    pid: Annotated[int, "PID from start_process."],
    input_text: Annotated[str, "Text to send to stdin. \\n added automatically."],
    timeout_seconds: Annotated[float, "Seconds waiting for response. Default 8."] = 8.0,
    max_lines: Annotated[int, "Max response lines. Default 200."] = 200,
) -> str:
    """Send input to a running process and return its response. Ideal for REPLs and interactive shells."""
    session = sessions.get(pid)
    if session is None: return f"[ERROR] No session with PID {pid}."
    if session.finished or session.process.returncode is not None:
        return f"[ERROR] PID {pid} already finished (exit={session.exit_code})."
    if session.process.stdin is None: return f"[ERROR] PID {pid} has no stdin."
    text = input_text if input_text.endswith("\n") else input_text + "\n"
    try:
        session.process.stdin.write(text.encode("utf-8"))
        await session.process.stdin.drain()
    except (BrokenPipeError, ConnectionResetError) as exc:
        return f"[ERROR] Could not write to stdin of PID {pid}: {exc}"
    lines, finished = await sessions.read_output(session, timeout_seconds=timeout_seconds, max_lines=max_lines)
    output = "".join(lines)
    status = f"finished (exit={session.exit_code})" if finished else "running"
    result = f"[PID {pid}] Sent: {input_text!r}  |  Status: {status}\n"
    result += f"\n{output.rstrip()}" if output else "\n(no output after input)"
    return result

async def list_sessions() -> str:
    """List all active process sessions started with start_process."""
    all_sessions = sessions.all()
    if not all_sessions: return "No active sessions. Use start_process to start one."
    for s in list(all_sessions):
        if s.finished and s.age_seconds() > 60: sessions.remove(s.pid)
    all_sessions = sessions.all()
    if not all_sessions: return "No active sessions (finished ones cleaned up)."
    header = f"{'PID':>7}  {'Status':<22}  {'Age':>8}  {'Lines':>7}  Command"
    rows = [header, "-" * 65]
    for s in sorted(all_sessions, key=lambda x: x.pid):
        rows.append(f"{s.pid:>7}  {s.status():<22}  {s.age_seconds():>7.0f}s  {s.total_lines:>7}  {s.command[:40]}")
    rows.append(f"\nTotal: {len(all_sessions)} session(s)")
    return "\n".join(rows)

async def force_terminate(pid: Annotated[int, "PID to kill immediately."]) -> str:
    """Kill a process immediately (SIGKILL). Use kill_process for graceful SIGTERM."""
    import psutil
    session = sessions.get(pid)
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        proc.kill()
        if session: session.finished = True; sessions.remove(pid)
        return f"Process {pid} ({name}) force-killed."
    except psutil.NoSuchProcess:
        if session: sessions.remove(pid)
        return f"PID {pid} not found (already finished)."
    except psutil.AccessDenied:
        return f"Access denied for PID {pid}. Needs elevated permissions."
