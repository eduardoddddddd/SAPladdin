"""
SAPladdin - Terminal execution tools.
Copiado de DesktopCommanderPy — sin cambios funcionales.
"""
import asyncio
import logging
from pathlib import Path
from typing import Annotated

from core.tools.utils import (
    build_subprocess_env, check_command_allowed,
    get_default_timeout, get_shell, load_security_config,
)

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

def _max_output() -> int:
    return _cfg().get("terminal", {}).get("max_output_chars", 500_000)

async def execute_command(
    command: Annotated[str, "Shell command to execute. PowerShell syntax on Windows."],
    working_directory: Annotated[str, "Working directory. Defaults to user home."] = "",
    timeout_seconds: Annotated[int, "Timeout in seconds. 0 = configured default."] = 0,
    environment: Annotated[dict[str, str], "Additional env vars."] = {},
) -> str:
    """Execute a shell command and return combined stdout+stderr output."""
    check_command_allowed(command, _blocked())
    shell_args = get_shell(_cfg())
    timeout = timeout_seconds if timeout_seconds > 0 else get_default_timeout(_cfg())
    cwd = working_directory if working_directory else str(Path.home())
    env = build_subprocess_env(environment or {})
    logger.info("execute_command: %r (cwd=%s, timeout=%ds)", command, cwd, timeout)
    try:
        proc = await asyncio.create_subprocess_exec(
            *shell_args, command,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd, env=env,
        )
        try:
            stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return f"[TIMEOUT] Command exceeded {timeout}s and was killed."
        output = stdout_bytes.decode("utf-8", errors="replace")
        max_chars = _max_output()
        if len(output) > max_chars:
            output = output[:max_chars] + f"\n[TRUNCATED: exceeded {max_chars} chars]"
        exit_note = f"\n[Exit code: {proc.returncode}]" if proc.returncode != 0 else ""
        return output.rstrip() + exit_note
    except FileNotFoundError as exc:
        raise RuntimeError(f"Shell not found: {shell_args[0]}. {exc}") from exc

async def execute_command_streaming(
    command: Annotated[str, "Shell command to execute with streaming output."],
    working_directory: Annotated[str, "Working directory."] = "",
    timeout_seconds: Annotated[int, "Overall timeout in seconds. 0 = configured default."] = 0,
    environment: Annotated[dict[str, str], "Additional env vars."] = {},
) -> str:
    """Execute a long-running command and return output incrementally."""
    check_command_allowed(command, _blocked())
    shell_args = get_shell(_cfg())
    timeout = timeout_seconds if timeout_seconds > 0 else get_default_timeout(_cfg())
    cwd = working_directory if working_directory else str(Path.home())
    env = build_subprocess_env(environment or {})
    lines_collected: list[str] = []
    max_chars = _max_output()
    total_chars = 0
    try:
        proc = await asyncio.create_subprocess_exec(
            *shell_args, command,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd, env=env,
        )
        async def _read_lines() -> None:
            nonlocal total_chars
            assert proc.stdout is not None
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace")
                lines_collected.append(line)
                total_chars += len(line)
                if total_chars >= max_chars:
                    lines_collected.append("[TRUNCATED]\n")
                    proc.kill()
                    break
        try:
            await asyncio.wait_for(_read_lines(), timeout=timeout)
            await proc.wait()
        except asyncio.TimeoutError:
            proc.kill()
            lines_collected.append(f"\n[TIMEOUT] Command exceeded {timeout}s\n")
        output = "".join(lines_collected)
        exit_note = f"\n[Exit code: {proc.returncode}]" if proc.returncode and proc.returncode != 0 else ""
        return output.rstrip() + exit_note
    except Exception as exc:
        logger.error("Streaming command failed: %s", exc)
        raise
