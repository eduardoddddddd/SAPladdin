"""
SAPladdin - Gestor de sesiones de procesos con estado.
Copiado de DesktopCommanderPy — sin cambios.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ProcessSession:
    pid: int
    command: str
    process: asyncio.subprocess.Process
    output_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    started_at: float = field(default_factory=time.time)
    total_lines: int = 0
    finished: bool = False
    exit_code: Optional[int] = None
    _drain_task: Optional[asyncio.Task] = field(default=None, repr=False)

    def age_seconds(self) -> float:
        return time.time() - self.started_at

    def status(self) -> str:
        if self.finished:
            return f"finished (exit={self.exit_code})"
        if self.process.returncode is not None:
            return f"exited (exit={self.process.returncode})"
        return "running"


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[int, ProcessSession] = {}

    def register(self, session: ProcessSession) -> None:
        self._sessions[session.pid] = session

    def get(self, pid: int) -> Optional[ProcessSession]:
        return self._sessions.get(pid)

    def remove(self, pid: int) -> None:
        if pid in self._sessions:
            del self._sessions[pid]

    def all(self) -> list[ProcessSession]:
        return list(self._sessions.values())

    async def drain_output(self, session: ProcessSession) -> None:
        try:
            assert session.process.stdout is not None
            async for raw in session.process.stdout:
                line = raw.decode("utf-8", errors="replace")
                await session.output_queue.put(line)
                session.total_lines += 1
        except Exception as exc:
            logger.debug("drain_output ended PID=%d: %s", session.pid, exc)
        finally:
            await session.output_queue.put(None)
            session.exit_code = await session.process.wait()
            session.finished = True

    async def read_output(
        self,
        session: ProcessSession,
        timeout_seconds: float = 5.0,
        max_lines: int = 200,
    ) -> tuple[list[str], bool]:
        lines: list[str] = []
        deadline = time.monotonic() + timeout_seconds
        while len(lines) < max_lines:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                item = await asyncio.wait_for(
                    session.output_queue.get(), timeout=min(remaining, 0.5)
                )
                if item is None:
                    return lines, True
                lines.append(item)
                deadline = time.monotonic() + min(timeout_seconds, 2.0)
            except asyncio.TimeoutError:
                if session.finished or session.process.returncode is not None:
                    return lines, True
                break
        finished = session.finished or session.process.returncode is not None
        return lines, finished


sessions = SessionManager()
