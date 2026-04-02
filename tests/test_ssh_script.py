"""Tests for ssh_run_bash_script (stdin bash -s)."""

import pytest

from core.tools import ssh


class _FakeChannel:
    def shutdown_write(self) -> None:
        pass

    def recv_exit_status(self) -> int:
        return 0


class _FakeStdin:
    def __init__(self) -> None:
        self.written = b""
        self.channel = _FakeChannel()

    def write(self, data: bytes) -> None:
        self.written += data


class _FakeStdout:
    def __init__(self, payload: bytes = b"hello\n") -> None:
        self._payload = payload
        self.channel = self

    def read(self) -> bytes:
        return self._payload

    def recv_exit_status(self) -> int:
        return 0


class _FakeSSHClient:
    def __init__(self) -> None:
        self.last_command: str = ""
        self.stdin: _FakeStdin | None = None

    def exec_command(self, command: str, timeout: int = 60, get_pty: bool = False):
        del timeout, get_pty
        self.last_command = command
        self.stdin = _FakeStdin()
        return self.stdin, _FakeStdout(b"ok\n"), _FakeStdout(b"")


@pytest.mark.asyncio
async def test_ssh_run_bash_script_uses_bash_s_and_sends_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeSSHClient()
    monkeypatch.setattr(ssh, "_ssh_pool", {"host1": fake})

    result = await ssh.ssh_run_bash_script(
        connection="host1",
        script="echo 1\r\necho 2\n",
    )

    assert fake.last_command == "bash -s"
    assert fake.stdin is not None
    assert fake.stdin.written == b"echo 1\necho 2\n"
    assert "ok" in result


def test_normalize_remote_script_crlf() -> None:
    assert ssh._normalize_remote_script("a\r\nb\rc") == "a\nb\nc"
