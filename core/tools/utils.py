"""
SAPladdin - Security helpers y path utilities.
Copiado de DesktopCommanderPy/core/tools/utils.py — sin cambios funcionales.
"""

import logging
import os
import platform
import re
import sys
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def load_security_config(config_path: Path) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "security": {
            "allowed_directories": [],
            "blocked_commands": [],
            "max_file_size_bytes": 10 * 1024 * 1024,
            "max_read_lines": 2000,
            "write_blocked_extensions": [".exe", ".dll", ".sys"],
        },
        "terminal": {
            "windows_shell": "powershell.exe",
            "linux_shell": "/bin/bash",
            "macos_shell": "/bin/zsh",
            "default_timeout_seconds": 30,
            "max_output_chars": 500_000,
        },
        "logging": {"level": "INFO"},
    }
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        _deep_merge(defaults, loaded or {})
        logger.info("Security config loaded from %s", config_path)
    except FileNotFoundError:
        logger.warning("Config not found at %s — using defaults", config_path)
    except yaml.YAMLError as exc:
        logger.error("YAML parse error in config: %s — using defaults", exc)
    return defaults

def _deep_merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def resolve_and_validate_path(path: str | Path, allowed_dirs: list[str]) -> Path:
    if not path:
        raise ValueError("Path must not be empty.")
    resolved = Path(path).resolve()
    if not allowed_dirs:
        return resolved
    for allowed in allowed_dirs:
        allowed_resolved = Path(allowed).resolve()
        try:
            resolved.relative_to(allowed_resolved)
            return resolved
        except ValueError:
            continue
    raise PermissionError(
        f"Access denied: '{resolved}' is outside all allowed directories.\n"
        f"Allowed: {allowed_dirs}"
    )


def check_extension_allowed(path: Path, blocked_extensions: list[str]) -> None:
    ext = path.suffix.lower()
    blocked_lower = [e.lower() for e in blocked_extensions]
    if ext in blocked_lower:
        raise ValueError(f"Write blocked: extension '{ext}' not allowed.")


def check_command_allowed(command: str, blocked_commands: list[str]) -> None:
    cmd_lower = command.lower()
    for blocked in blocked_commands:
        pattern = r"\b" + re.escape(blocked.lower()) + r"\b"
        if re.search(pattern, cmd_lower):
            raise PermissionError(f"Command blocked: matched '{blocked}'.")


def get_shell(config: dict) -> list[str]:
    system = platform.system()
    terminal_cfg = config.get("terminal", {})
    if system == "Windows":
        shell = terminal_cfg.get("windows_shell", "powershell.exe")
        return [shell, "-Command"]
    elif system == "Darwin":
        return [terminal_cfg.get("macos_shell", "/bin/zsh"), "-c"]
    else:
        return [terminal_cfg.get("linux_shell", "/bin/bash"), "-c"]


def get_default_timeout(config: dict) -> int:
    return config.get("terminal", {}).get("default_timeout_seconds", 30)


def build_subprocess_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    python_dirs: list[str] = []
    venv_scripts = Path(sys.executable).parent
    python_dirs.append(str(venv_scripts))
    try:
        base_scripts = Path(sys.base_prefix) / "Scripts"
        if base_scripts != venv_scripts:
            python_dirs.append(str(base_scripts))
    except Exception:
        pass
    current_path = env.get("PATH", "")
    path_lower = current_path.lower()
    for d in reversed(python_dirs):
        if d.lower() not in path_lower:
            current_path = d + os.pathsep + current_path
            path_lower = current_path.lower()
    env["PATH"] = current_path
    if extra:
        env.update(extra)
    return env
