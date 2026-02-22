from __future__ import annotations

import io
from pathlib import Path
import subprocess

import pytest

from gui import AppProcessController


class FakeProc:
    def __init__(self, *, running: bool = True, wait_timeout_once: bool = False) -> None:
        self._running = running
        self._killed = False
        self._terminated = False
        self._wait_timeout_once = wait_timeout_once
        self.stdout = io.StringIO("line-1\nline-2\n")

    def poll(self):
        return None if self._running else 0

    def terminate(self):
        self._terminated = True
        if not self._wait_timeout_once:
            self._running = False

    def kill(self):
        self._killed = True
        self._running = False

    def wait(self, timeout=None):
        if self._wait_timeout_once and self._terminated and not self._killed:
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout)
        self._running = False
        return 0


def test_controller_start_and_collect_output(monkeypatch, tmp_path: Path) -> None:
    fake = FakeProc()

    def fake_popen(*args, **kwargs):
        return fake

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    ctl = AppProcessController(cwd=tmp_path)
    ctl.start(["python", "src/main.py"])

    # allow reader thread to consume stream
    import time

    time.sleep(0.05)
    lines = ctl.poll_lines()
    assert "line-1" in lines
    assert "line-2" in lines


def test_controller_stop_terminate_then_kill(monkeypatch, tmp_path: Path) -> None:
    fake = FakeProc(wait_timeout_once=True)

    def fake_popen(*args, **kwargs):
        return fake

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    ctl = AppProcessController(cwd=tmp_path)
    ctl.start(["python", "src/main.py"])
    ctl.stop(timeout=0.01)

    assert fake._terminated is True
    assert fake._killed is True
    assert ctl.is_running() is False


def test_controller_prevents_double_start(monkeypatch, tmp_path: Path) -> None:
    fake = FakeProc()

    def fake_popen(*args, **kwargs):
        return fake

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    ctl = AppProcessController(cwd=tmp_path)
    ctl.start(["python", "src/main.py"])
    with pytest.raises(RuntimeError):
        ctl.start(["python", "src/main.py"])
