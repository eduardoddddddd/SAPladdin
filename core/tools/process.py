"""SAPladdin - Process management tools. Copiado de DesktopCommanderPy."""

import logging
from typing import Annotated
import psutil

logger = logging.getLogger(__name__)


async def list_processes(
    filter_name: Annotated[str, "Filter by name (case-insensitive). Empty = all."] = "",
    sort_by: Annotated[str, "Sort by: name, pid, cpu, memory."] = "name",
) -> str:
    """List running processes with PID, name, CPU%, memory."""
    procs: list[dict] = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        try:
            info = proc.info
            name = info.get("name") or ""
            if filter_name and filter_name.lower() not in name.lower():
                continue
            mem_mb = (info.get("memory_info") or psutil._common.pmem(0, 0)).rss / (1024 * 1024)
            procs.append({"pid": info.get("pid", 0), "name": name,
                          "cpu": info.get("cpu_percent") or 0.0,
                          "mem_mb": mem_mb, "status": info.get("status", "?")})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    sort_key = {"name": lambda p: p["name"].lower(), "pid": lambda p: p["pid"],
                "cpu": lambda p: -p["cpu"], "memory": lambda p: -p["mem_mb"]
                }.get(sort_by, lambda p: p["name"].lower())
    procs.sort(key=sort_key)

    if not procs:
        return f"No processes found" + (f" matching '{filter_name}'." if filter_name else ".")

    header = f"{'PID':>7}  {'Name':<35}  {'CPU%':>6}  {'Mem (MB)':>10}  Status"
    rows = [header, "-" * len(header)]
    for p in procs:
        rows.append(f"{p['pid']:>7}  {p['name']:<35}  {p['cpu']:>6.1f}  {p['mem_mb']:>10.1f}  {p['status']}")
    rows.append(f"\nTotal: {len(procs)} process(es)")
    return "\n".join(rows)


async def kill_process(
    pid: Annotated[int, "PID of the process to terminate."],
    force: Annotated[bool, "True = SIGKILL, False = SIGTERM (default)."] = False,
) -> str:
    """Terminate a running process by PID."""
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        if force:
            proc.kill()
            action = "force-killed (SIGKILL)"
        else:
            proc.terminate()
            action = "terminated (SIGTERM)"
        return f"Process {pid} ({name}) {action}."
    except psutil.NoSuchProcess:
        return f"No process with PID {pid}."
    except psutil.AccessDenied:
        return f"Access denied for PID {pid}. Try elevated permissions."
    except Exception as exc:
        raise
