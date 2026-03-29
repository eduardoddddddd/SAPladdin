"""
SAPladdin - Filesystem tools.
Copiado de DesktopCommanderPy — sin cambios funcionales.
"""
import fnmatch, logging, os, re
from pathlib import Path
from typing import Annotated
from core.tools.utils import check_extension_allowed, load_security_config, resolve_and_validate_path

logger = logging.getLogger(__name__)
_security_config: dict | None = None

def _cfg() -> dict:
    global _security_config
    if _security_config is None:
        _cfg_path = Path(__file__).parent.parent.parent / "config" / "security_config.yaml"
        _security_config = load_security_config(_cfg_path)
    return _security_config

def _allowed() -> list[str]: return _cfg()["security"]["allowed_directories"]
def _blocked_ext() -> list[str]: return _cfg()["security"].get("write_blocked_extensions", [])
def _max_lines() -> int: return _cfg()["security"].get("max_read_lines", 2000)

def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024: return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

async def read_file(
    path: Annotated[str, "Absolute path to the file."],
    offset: Annotated[int, "Start line (0-based)."] = 0,
    length: Annotated[int, "Max lines. 0 = configured limit."] = 0,
) -> str:
    """Read a text file with optional pagination."""
    resolved = resolve_and_validate_path(path, _allowed())
    max_lines = length if length > 0 else _max_lines()
    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except IsADirectoryError:
        raise ValueError(f"'{resolved}' is a directory, not a file.")
    total = len(lines)
    chunk = lines[offset: offset + max_lines]
    result = "".join(chunk)
    if offset + max_lines < total:
        result += f"\n[... {total - offset - max_lines} more lines. Use offset={offset + max_lines} ...]"
    return result

async def write_file(
    path: Annotated[str, "Absolute path to write."],
    content: Annotated[str, "Text content."],
    mode: Annotated[str, "'rewrite' (default) or 'append'."] = "rewrite",
) -> str:
    """Write or append text to a file."""
    resolved = resolve_and_validate_path(path, _allowed())
    check_extension_allowed(resolved, _blocked_ext())
    resolved.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "w" if mode == "rewrite" else "a"
    with open(resolved, file_mode, encoding="utf-8") as f:
        f.write(content)
    lines_written = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    action = "Written" if mode == "rewrite" else "Appended"
    return f"{action} {lines_written} lines to '{resolved}'."

async def edit_file_diff(
    path: Annotated[str, "Absolute path to edit."],
    old_string: Annotated[str, "Exact text to find (must be unique)."],
    new_string: Annotated[str, "Replacement text. Empty = delete old_string."],
    expected_replacements: Annotated[int, "Expected occurrences. Default 1."] = 1,
) -> str:
    """Edit a file by replacing an exact text snippet."""
    resolved = resolve_and_validate_path(path, _allowed())
    check_extension_allowed(resolved, _blocked_ext())
    original = resolved.read_text(encoding="utf-8")
    count = original.count(old_string)
    if count == 0:
        raise ValueError(f"old_string not found in '{resolved}'.")
    if count != expected_replacements:
        raise ValueError(f"Expected {expected_replacements} occurrence(s), found {count}.")
    updated = original.replace(old_string, new_string, expected_replacements)
    resolved.write_text(updated, encoding="utf-8")
    return f"Replaced {expected_replacements} occurrence(s) in '{resolved}'."

async def list_directory(
    path: Annotated[str, "Absolute path to directory."],
    recursive: Annotated[str, "'true' for recursive listing."] = "false",
    max_depth: Annotated[int, "Max recursion depth. Default 3."] = 3,
) -> str:
    """List directory contents as a tree."""
    resolved = resolve_and_validate_path(path, _allowed())
    if not resolved.is_dir():
        raise ValueError(f"'{resolved}' is not a directory.")
    recursive_bool = str(recursive).lower() in ("true", "1", "yes")
    lines: list[str] = [f"Directory listing: {resolved}\n"]
    def _walk(current: Path, depth: int, prefix: str) -> None:
        if depth > max_depth:
            lines.append(f"{prefix}[...depth limit]"); return
        try:
            entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            lines.append(f"{prefix}[DENIED]"); return
        for entry in entries:
            if entry.is_dir():
                lines.append(f"{prefix}[DIR]  {entry.name}/")
                if recursive_bool: _walk(entry, depth + 1, prefix + "    ")
            else:
                try: size_str = _human_size(entry.stat().st_size)
                except OSError: size_str = "?"
                lines.append(f"{prefix}[FILE] {entry.name} ({size_str})")
    _walk(resolved, 1, "  ")
    return "\n".join(lines)

async def search_files(
    root: Annotated[str, "Absolute path to search in."],
    pattern: Annotated[str, "Glob pattern or substring to match in filenames."],
    content_search: Annotated[str, "Text to search inside files. Empty = skip."] = "",
    case_sensitive: Annotated[str, "'true' for case-sensitive."] = "false",
    max_results: Annotated[int, "Max results. Default 100."] = 100,
) -> str:
    """Search files by name pattern and/or content."""
    resolved = resolve_and_validate_path(root, _allowed())
    if not resolved.is_dir():
        raise ValueError(f"'{resolved}' is not a directory.")
    flag = 0 if str(case_sensitive).lower() not in ("true", "1", "yes") else re.IGNORECASE
    results: list[str] = []
    content_re = re.compile(re.escape(content_search), flag) if content_search else None
    for file_path in resolved.rglob("*"):
        if len(results) >= max_results: break
        if not file_path.is_file(): continue
        name = file_path.name
        if any(c in pattern for c in "*?["):
            name_match = fnmatch.fnmatch(name.lower(), pattern.lower()) if not case_sensitive else fnmatch.fnmatch(name, pattern)
        else:
            name_match = pattern.lower() in name.lower() if not case_sensitive else pattern in name
        if not name_match: continue
        if content_re is None:
            results.append(str(file_path))
        else:
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                matches = content_re.findall(text)
                if matches: results.append(f"{file_path}  [{len(matches)} match(es)]")
            except OSError: pass
    if not results:
        return f"No files matching '{pattern}'" + (f" with '{content_search}'" if content_search else "") + f" under '{resolved}'."
    return f"Found {len(results)} file(s):\n" + "\n".join(results)

async def get_file_info(path: Annotated[str, "Absolute path to file or directory."]) -> str:
    """Return metadata about a file or directory."""
    import datetime
    resolved = resolve_and_validate_path(path, _allowed())
    try: stat = resolved.stat()
    except FileNotFoundError: raise FileNotFoundError(f"'{resolved}' does not exist.")
    kind = "Directory" if resolved.is_dir() else "File"
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    info_lines = [f"Path: {resolved}", f"Type: {kind}",
                  f"Size: {_human_size(stat.st_size)} ({stat.st_size} bytes)", f"Modified: {mtime}"]
    if resolved.is_file():
        info_lines.append(f"Extension: {resolved.suffix or '(none)'}")
        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                preview = "".join(f.readline() for _ in range(10)).rstrip()
            info_lines.append(f"\n--- Preview (10 lines) ---\n{preview}")
        except Exception: info_lines.append("(binary file)")
    return "\n".join(info_lines)

async def create_directory(path: Annotated[str, "Absolute path of directory to create."]) -> str:
    """Create a directory (mkdir -p). Fails silently if exists."""
    resolved = resolve_and_validate_path(path, _allowed())
    resolved.mkdir(parents=True, exist_ok=True)
    return f"Directory created: '{resolved}'"

async def move_file(
    source: Annotated[str, "Absolute source path."],
    destination: Annotated[str, "Absolute destination path."],
) -> str:
    """Move or rename a file or directory."""
    import shutil
    src = resolve_and_validate_path(source, _allowed())
    dst = resolve_and_validate_path(destination, _allowed())
    if not src.exists(): raise FileNotFoundError(f"Source not found: '{src}'")
    result_path = shutil.move(str(src), str(dst))
    return f"Moved: '{src}' → '{result_path}'"

async def read_multiple_files(
    paths: Annotated[list[str], "List of absolute paths to read."],
    max_lines_each: Annotated[int, "Max lines per file. Default 200."] = 200,
) -> str:
    """Read multiple text files in one call."""
    results: list[str] = []
    for p in paths:
        try:
            resolved = resolve_and_validate_path(p, _allowed())
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            total = len(lines)
            content = "".join(lines[:max_lines_each])
            truncated = f"\n[... {total - max_lines_each} more lines ...]" if total > max_lines_each else ""
            results.append(f"{'='*60}\n# {resolved}\n{'='*60}\n{content.rstrip()}{truncated}")
        except PermissionError as e:
            results.append(f"{'='*60}\n# {p}\n{'='*60}\n[DENIED: {e}]")
        except FileNotFoundError:
            results.append(f"{'='*60}\n# {p}\n{'='*60}\n[NOT FOUND]")
        except Exception as e:
            results.append(f"{'='*60}\n# {p}\n{'='*60}\n[ERROR: {e}]")
    return "\n\n".join(results)
