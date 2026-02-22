from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import wave

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _make_wav_file(path: Path, sr: int = 16000, freq_hz: float = 440.0, duration_s: float = 0.5) -> None:
    n = int(sr * duration_s)
    t = np.arange(n, dtype=np.float64) / float(sr)
    signal = 0.25 * np.sin(2.0 * np.pi * freq_hz * t)
    pcm16 = np.clip(signal * 32767.0, -32768, 32767).astype(np.int16)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())


def test_headless_smoke_sine_source_runs_and_exits() -> None:
    cmd = [
        sys.executable,
        "src/main.py",
        "--source",
        "sine",
        "--headless",
        "true",
        "--max-frames",
        "20",
        "--fps",
        "40",
        "--window-ms",
        "200",
        "--width",
        "128",
        "--height",
        "128",
        "--log-every",
        "10",
        "--accum",
        "avg",
        "--point-size-step",
        "7",
        "--point-render-style",
        "square_stamp",
        "--value-mode",
        "flat",
        "--rotation",
        "plus45",
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=40)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert "Reached max-frames=20" in proc.stdout


def test_headless_smoke_wav_source_runs_and_exits(tmp_path: Path) -> None:
    wav_path = tmp_path / "smoke.wav"
    _make_wav_file(wav_path)

    cmd = [
        sys.executable,
        "src/main.py",
        "--source",
        "wav",
        "--wav-path",
        str(wav_path),
        "--headless",
        "true",
        "--max-frames",
        "12",
        "--fps",
        "30",
        "--window-ms",
        "150",
        "--width",
        "96",
        "--height",
        "96",
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=40)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert "Reached max-frames=12" in proc.stdout


def test_loopback_failure_fallbacks_to_sine() -> None:
    cmd = [
        sys.executable,
        "src/main.py",
        "--source",
        "loopback",
        "--device",
        "9999",  # intentionally invalid for deterministic failover
        "--fallback-on-fail",
        "true",
        "--headless",
        "true",
        "--max-frames",
        "8",
        "--fps",
        "20",
        "--window-ms",
        "100",
        "--width",
        "64",
        "--height",
        "64",
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=40)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert "Falling back to sine source." in proc.stdout
    assert "Reached max-frames=8" in proc.stdout
