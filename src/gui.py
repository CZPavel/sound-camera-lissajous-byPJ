from __future__ import annotations

import argparse
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from audio_capture import list_audio_devices
from gui_state import load_ui_state, save_ui_state


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_SCRIPT_REL = "src/main.py"


def _bool_to_cli(value: bool) -> str:
    return "true" if bool(value) else "false"


def _state_value(state: dict[str, Any], key: str, fallback: str = "") -> str:
    val = state.get(key, fallback)
    return str(val) if val is not None else ""


def build_main_command_from_state(
    state: dict[str, Any],
    python_executable: str | None = None,
) -> list[str]:
    py = python_executable or sys.executable
    cmd: list[str] = [py, MAIN_SCRIPT_REL]

    cmd.extend(["--source", _state_value(state, "source", "loopback")])
    cmd.extend(["--device", _state_value(state, "device", "default")])
    cmd.extend(["--tau", _state_value(state, "tau", "5")])
    cmd.extend(["--fps", _state_value(state, "fps", "10")])
    cmd.extend(["--window-ms", _state_value(state, "window_ms", "200")])
    cmd.extend(["--width", _state_value(state, "width", "512")])
    cmd.extend(["--height", _state_value(state, "height", "512")])
    cmd.extend(["--accum", _state_value(state, "accum", "none")])
    cmd.extend(["--point-size-step", _state_value(state, "point_size_step", "1")])
    cmd.extend(["--point-render-style", _state_value(state, "point_render_style", "classic")])
    cmd.extend(["--value-mode", _state_value(state, "value_mode", "radial")])
    cmd.extend(["--rotation", _state_value(state, "rotation", "none")])
    cmd.extend(["--fallback-on-fail", _bool_to_cli(bool(state.get("fallback_on_fail", True)))])
    cmd.extend(["--headless", _bool_to_cli(bool(state.get("headless", False)))])
    cmd.extend(["--max-frames", _state_value(state, "max_frames", "0")])
    cmd.extend(["--log-every", _state_value(state, "log_every", "30")])
    cmd.extend(["--sine-freq", _state_value(state, "sine_freq", "440")])

    wav_path = _state_value(state, "wav_path", "").strip()
    if state.get("source") == "wav" and wav_path:
        cmd.extend(["--wav-path", wav_path])
    elif wav_path:
        # keep fallback behavior from main.py
        cmd.extend(["--wav-path", wav_path])

    save_dir = _state_value(state, "save_dir", "").strip()
    if save_dir:
        cmd.extend(["--save-dir", save_dir])

    sample_rate = _state_value(state, "sample_rate", "").strip()
    if sample_rate:
        cmd.extend(["--sample-rate", sample_rate])

    channels = _state_value(state, "channels", "").strip()
    if channels:
        cmd.extend(["--channels", channels])

    return cmd


def build_smoke_state(base_state: dict[str, Any]) -> dict[str, Any]:
    """
    Build temporary smoke-test settings without mutating user configuration.
    Smoke is intentionally short and headless.
    """
    state = dict(base_state)
    state["source"] = "sine"
    state["headless"] = True
    state["max_frames"] = "20"
    state["fps"] = "30"
    state["accum"] = "avg"
    state["point_size_step"] = "7"
    state["point_render_style"] = "square_stamp"
    state["value_mode"] = "flat"
    state["rotation"] = "plus45"
    return state


class AppProcessController:
    def __init__(self, cwd: Path) -> None:
        self.cwd = Path(cwd)
        self.proc: subprocess.Popen[str] | None = None
        self._queue: queue.Queue[str] = queue.Queue()
        self._reader_thread: threading.Thread | None = None

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, cmd: list[str]) -> None:
        if self.is_running():
            raise RuntimeError("Application process is already running.")

        self.proc = subprocess.Popen(
            cmd,
            cwd=str(self.cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        if self.proc is None or self.proc.stdout is None:
            return
        try:
            for line in self.proc.stdout:
                self._queue.put(line.rstrip("\n"))
        except Exception as exc:
            self._queue.put(f"[GUI] Log reader error: {exc}")

    def stop(self, timeout: float = 2.0) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is not None:
            return

        self.proc.terminate()
        try:
            self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=timeout)

    def poll_lines(self) -> list[str]:
        lines: list[str] = []
        while True:
            try:
                lines.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return lines


class SoundLauncherGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Sound Loopback Lissajous - Launcher")
        self.geometry("980x760")
        self.minsize(900, 700)

        self._state = load_ui_state()
        self._device_map: dict[str, str] = {}
        self._controller = AppProcessController(cwd=PROJECT_ROOT)
        self._last_exit_reported = False

        self._build_vars()
        self._build_layout()
        self._load_state_into_controls()
        self._refresh_devices()
        self._set_status("Ready")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self._pump_output)

    def _build_vars(self) -> None:
        self.var_source = tk.StringVar(value="loopback")
        self.var_device = tk.StringVar(value="default")
        self.var_tau = tk.StringVar(value="5")
        self.var_fps = tk.StringVar(value="10")
        self.var_window_ms = tk.StringVar(value="200")
        self.var_width = tk.StringVar(value="512")
        self.var_height = tk.StringVar(value="512")
        self.var_accum = tk.StringVar(value="none")
        self.var_point_size_step = tk.StringVar(value="1")
        self.var_point_render_style = tk.StringVar(value="classic")
        self.var_value_mode = tk.StringVar(value="radial")
        self.var_rotation = tk.StringVar(value="none")
        self.var_wav_path = tk.StringVar(value="")
        self.var_save_dir = tk.StringVar(value="")
        self.var_fallback = tk.BooleanVar(value=True)
        self.var_headless = tk.BooleanVar(value=False)
        self.var_max_frames = tk.StringVar(value="0")
        self.var_log_every = tk.StringVar(value="30")
        self.var_sample_rate = tk.StringVar(value="")
        self.var_channels = tk.StringVar(value="")
        self.var_sine_freq = tk.StringVar(value="440")
        self.var_status = tk.StringVar(value="")

    def _build_layout(self) -> None:
        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        frm_src = ttk.LabelFrame(main, text="Source & device", padding=8)
        frm_src.pack(fill="x", padx=2, pady=4)
        frm_core = ttk.LabelFrame(main, text="Core settings", padding=8)
        frm_core.pack(fill="x", padx=2, pady=4)
        frm_opt = ttk.LabelFrame(main, text="Optional settings", padding=8)
        frm_opt.pack(fill="x", padx=2, pady=4)
        frm_run = ttk.LabelFrame(main, text="Run controls", padding=8)
        frm_run.pack(fill="x", padx=2, pady=4)
        frm_log = ttk.LabelFrame(main, text="Status & log", padding=8)
        frm_log.pack(fill="both", expand=True, padx=2, pady=4)

        # Source/device
        ttk.Label(frm_src, text="Source").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        source_cb = ttk.Combobox(frm_src, textvariable=self.var_source, values=["loopback", "wav", "sine"], state="readonly", width=12)
        source_cb.grid(row=0, column=1, sticky="w", padx=4, pady=3)

        ttk.Label(frm_src, text="Device").grid(row=0, column=2, sticky="w", padx=4, pady=3)
        self.device_cb = ttk.Combobox(frm_src, textvariable=self.var_device, width=60)
        self.device_cb.grid(row=0, column=3, sticky="ew", padx=4, pady=3)
        ttk.Button(frm_src, text="Refresh devices", command=self._refresh_devices).grid(row=0, column=4, sticky="e", padx=4, pady=3)
        frm_src.columnconfigure(3, weight=1)

        # Core
        self._add_labeled_entry(frm_core, "Tau", self.var_tau, 0, 0, width=10, combo_values=["1", "5", "10", "20", "50", "both"])
        self._add_labeled_entry(frm_core, "FPS", self.var_fps, 0, 2, width=10)
        self._add_labeled_entry(frm_core, "Window ms", self.var_window_ms, 0, 4, width=10)
        self._add_labeled_entry(frm_core, "Width", self.var_width, 1, 0, width=10)
        self._add_labeled_entry(frm_core, "Height", self.var_height, 1, 2, width=10)
        self._add_labeled_entry(frm_core, "Accum", self.var_accum, 1, 4, width=10, combo_values=["none", "max", "sum", "avg"])
        self._add_labeled_entry(
            frm_core,
            "Point size step",
            self.var_point_size_step,
            2,
            0,
            width=10,
            combo_values=["1", "2", "3", "4", "5", "6", "7"],
        )
        self._add_labeled_entry(
            frm_core,
            "Point render style",
            self.var_point_render_style,
            2,
            2,
            width=14,
            combo_values=["classic", "sharp_stamp", "square_stamp"],
        )
        self._add_labeled_entry(
            frm_core,
            "Value mode",
            self.var_value_mode,
            2,
            4,
            width=10,
            combo_values=["radial", "flat"],
        )
        self._add_labeled_entry(
            frm_core,
            "Rotation",
            self.var_rotation,
            3,
            0,
            width=10,
            combo_values=["none", "plus45", "minus45"],
        )

        # Optional
        self._add_path_row(frm_opt, "WAV path", self.var_wav_path, row=0, browse_file=True)
        self._add_path_row(frm_opt, "Save dir", self.var_save_dir, row=1, browse_dir=True)

        self._add_labeled_entry(frm_opt, "Sample rate", self.var_sample_rate, 2, 0, width=12)
        self._add_labeled_entry(frm_opt, "Channels", self.var_channels, 2, 2, width=12)
        self._add_labeled_entry(frm_opt, "Sine freq", self.var_sine_freq, 2, 4, width=12)

        ttk.Checkbutton(frm_opt, text="Fallback on fail", variable=self.var_fallback).grid(row=3, column=0, sticky="w", padx=4, pady=4)
        ttk.Checkbutton(frm_opt, text="Headless", variable=self.var_headless).grid(row=3, column=2, sticky="w", padx=4, pady=4)
        self._add_labeled_entry(frm_opt, "Max frames", self.var_max_frames, 3, 4, width=12)
        self._add_labeled_entry(frm_opt, "Log every", self.var_log_every, 3, 6, width=12)

        # Run controls
        self.btn_start = ttk.Button(frm_run, text="Start", command=self._start_clicked)
        self.btn_start.grid(row=0, column=0, padx=4, pady=4, sticky="w")
        self.btn_stop = ttk.Button(frm_run, text="Stop", command=self._stop_clicked)
        self.btn_stop.grid(row=0, column=1, padx=4, pady=4, sticky="w")
        self.btn_smoke = ttk.Button(frm_run, text="Run smoke (sine)", command=self._run_smoke_clicked)
        self.btn_smoke.grid(row=0, column=2, padx=4, pady=4, sticky="w")
        ttk.Button(frm_run, text="Save settings", command=self._save_state_from_controls).grid(row=0, column=3, padx=4, pady=4, sticky="w")

        # Log/status
        ttk.Label(frm_log, text="Status:").pack(anchor="w")
        ttk.Label(frm_log, textvariable=self.var_status).pack(anchor="w", pady=(0, 6))
        self.txt_log = tk.Text(frm_log, height=20, wrap="word")
        self.txt_log.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(frm_log, orient="vertical", command=self.txt_log.yview)
        scroll.pack(side="right", fill="y")
        self.txt_log.configure(yscrollcommand=scroll.set, state="disabled")

    def _add_labeled_entry(
        self,
        parent: ttk.LabelFrame,
        label: str,
        var: tk.Variable,
        row: int,
        col: int,
        *,
        width: int = 12,
        combo_values: list[str] | None = None,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=4, pady=3)
        if combo_values:
            widget = ttk.Combobox(parent, textvariable=var, values=combo_values, state="readonly", width=width)
        else:
            widget = ttk.Entry(parent, textvariable=var, width=width)
        widget.grid(row=row, column=col + 1, sticky="w", padx=4, pady=3)

    def _add_path_row(
        self,
        parent: ttk.LabelFrame,
        label: str,
        var: tk.StringVar,
        *,
        row: int,
        browse_file: bool = False,
        browse_dir: bool = False,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=3)
        entry = ttk.Entry(parent, textvariable=var, width=80)
        entry.grid(row=row, column=1, columnspan=5, sticky="ew", padx=4, pady=3)
        parent.columnconfigure(1, weight=1)
        if browse_file:
            ttk.Button(parent, text="Browse", command=self._browse_wav).grid(row=row, column=6, sticky="e", padx=4, pady=3)
        if browse_dir:
            ttk.Button(parent, text="Browse", command=self._browse_save_dir).grid(row=row, column=6, sticky="e", padx=4, pady=3)

    def _browse_wav(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select WAV file",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")],
        )
        if file_path:
            self.var_wav_path.set(file_path)

    def _browse_save_dir(self) -> None:
        dir_path = filedialog.askdirectory(title="Select save directory")
        if dir_path:
            self.var_save_dir.set(dir_path)

    def _load_state_into_controls(self) -> None:
        s = self._state
        self.var_source.set(str(s.get("source", "loopback")))
        self.var_device.set(str(s.get("device", "default")))
        self.var_tau.set(str(s.get("tau", "5")))
        self.var_fps.set(str(s.get("fps", "10")))
        self.var_window_ms.set(str(s.get("window_ms", "200")))
        self.var_width.set(str(s.get("width", "512")))
        self.var_height.set(str(s.get("height", "512")))
        self.var_accum.set(str(s.get("accum", "none")))
        self.var_point_size_step.set(str(s.get("point_size_step", "1")))
        self.var_point_render_style.set(str(s.get("point_render_style", "classic")))
        self.var_value_mode.set(str(s.get("value_mode", "radial")))
        self.var_rotation.set(str(s.get("rotation", "none")))
        self.var_wav_path.set(str(s.get("wav_path", "")))
        self.var_save_dir.set(str(s.get("save_dir", "")))
        self.var_fallback.set(bool(s.get("fallback_on_fail", True)))
        self.var_headless.set(bool(s.get("headless", False)))
        self.var_max_frames.set(str(s.get("max_frames", "0")))
        self.var_log_every.set(str(s.get("log_every", "30")))
        self.var_sample_rate.set(str(s.get("sample_rate", "")))
        self.var_channels.set(str(s.get("channels", "")))
        self.var_sine_freq.set(str(s.get("sine_freq", "440")))

    def _collect_state_from_controls(self) -> dict[str, Any]:
        device_selection = self.var_device.get().strip() or "default"
        device_value = self._device_map.get(device_selection, device_selection)

        return {
            "source": self.var_source.get().strip() or "loopback",
            "device": device_value,
            "tau": self.var_tau.get().strip() or "5",
            "fps": self.var_fps.get().strip() or "10",
            "window_ms": self.var_window_ms.get().strip() or "200",
            "width": self.var_width.get().strip() or "512",
            "height": self.var_height.get().strip() or "512",
            "accum": self.var_accum.get().strip() or "none",
            "point_size_step": self.var_point_size_step.get().strip() or "1",
            "point_render_style": self.var_point_render_style.get().strip() or "classic",
            "value_mode": self.var_value_mode.get().strip() or "radial",
            "rotation": self.var_rotation.get().strip() or "none",
            "wav_path": self.var_wav_path.get().strip(),
            "save_dir": self.var_save_dir.get().strip(),
            "fallback_on_fail": bool(self.var_fallback.get()),
            "headless": bool(self.var_headless.get()),
            "max_frames": self.var_max_frames.get().strip() or "0",
            "log_every": self.var_log_every.get().strip() or "30",
            "sample_rate": self.var_sample_rate.get().strip(),
            "channels": self.var_channels.get().strip(),
            "sine_freq": self.var_sine_freq.get().strip() or "440",
        }

    def _save_state_from_controls(self) -> None:
        state = self._collect_state_from_controls()
        save_ui_state(state)
        self._append_log("[GUI] Settings saved.")

    def _refresh_devices(self) -> None:
        try:
            rows = list_audio_devices()
        except Exception as exc:
            self._append_log(f"[GUI] Device refresh failed: {exc}")
            return

        values = ["default"]
        self._device_map = {"default": "default"}

        for row in rows:
            idx = row["index"]
            name = row["name"]
            host = row["hostapi_name"]
            mark = "*" if row.get("is_default_output") else " "
            display = f"[{idx:02d}] {mark} {host} | {name}"
            values.append(display)
            self._device_map[display] = str(idx)

        self.device_cb["values"] = values
        current = self.var_device.get().strip()
        if current in self._device_map:
            self.var_device.set(current)
        elif current.isdigit():
            # resolve saved numeric device to display label if possible
            pattern = re.compile(rf"^\[{int(current):02d}\]")
            matches = [v for v in values if pattern.search(v)]
            self.var_device.set(matches[0] if matches else "default")
        else:
            self.var_device.set("default")

        self._append_log(f"[GUI] Devices refreshed ({len(rows)} entries).")

    def _append_log(self, line: str) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", line + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _set_status(self, text: str) -> None:
        self.var_status.set(text)

    def _validate_numeric_fields(self) -> bool:
        checks = [
            ("FPS", self.var_fps.get()),
            ("Window ms", self.var_window_ms.get()),
            ("Width", self.var_width.get()),
            ("Height", self.var_height.get()),
            ("Point size step", self.var_point_size_step.get()),
            ("Max frames", self.var_max_frames.get()),
            ("Log every", self.var_log_every.get()),
            ("Sine freq", self.var_sine_freq.get()),
        ]
        for label, raw in checks:
            value = raw.strip()
            if value == "":
                continue
            try:
                float(value)
            except ValueError:
                messagebox.showerror("Invalid input", f"{label} must be numeric.")
                return False

        raw_step = self.var_point_size_step.get().strip() or "1"
        if not raw_step.isdigit():
            messagebox.showerror("Invalid input", "Point size step must be an integer in range 1..7.")
            return False
        point_step = int(raw_step)
        if not (1 <= point_step <= 7):
            messagebox.showerror("Invalid input", "Point size step must be in range 1..7.")
            return False

        if self.var_point_render_style.get() not in {"classic", "sharp_stamp", "square_stamp"}:
            messagebox.showerror("Invalid input", "Point render style must be classic, sharp_stamp, or square_stamp.")
            return False

        if self.var_value_mode.get() not in {"radial", "flat"}:
            messagebox.showerror("Invalid input", "Value mode must be radial or flat.")
            return False

        if self.var_rotation.get() not in {"none", "plus45", "minus45"}:
            messagebox.showerror("Invalid input", "Rotation must be none, plus45, or minus45.")
            return False

        return True

    def _start_clicked(self, state_override: dict[str, Any] | None = None, *, save_state: bool = True) -> None:
        if not self._validate_numeric_fields():
            return
        if self._controller.is_running():
            messagebox.showwarning("Already running", "Application process is already running.")
            return

        state = state_override or self._collect_state_from_controls()
        if save_state:
            save_ui_state(state)

        if state.get("source") == "wav" and not str(state.get("wav_path", "")).strip():
            messagebox.showerror("Missing WAV path", "For source='wav' please set WAV path first.")
            return

        cmd = build_main_command_from_state(state)
        self._append_log("[GUI] Starting: " + " ".join(cmd))
        self._controller.start(cmd)
        self._set_status("Running")
        self._last_exit_reported = False

    def _run_smoke_clicked(self) -> None:
        if self._controller.is_running():
            messagebox.showwarning("Already running", "Stop current process before smoke run.")
            return

        base_state = self._collect_state_from_controls()
        smoke_state = build_smoke_state(base_state)
        self._append_log(
            "[GUI] Running temporary smoke settings (sine, headless, max-frames=20, accum=avg, point-size=7, square_stamp, flat, +45)."
        )
        self._start_clicked(state_override=smoke_state, save_state=False)

    def _stop_clicked(self) -> None:
        if not self._controller.is_running():
            self._append_log("[GUI] No running process.")
            return
        self._append_log("[GUI] Stopping process ...")
        self._controller.stop(timeout=2.0)
        self._set_status("Stopped")

    def _pump_output(self) -> None:
        for line in self._controller.poll_lines():
            self._append_log(line)

        if self._controller.proc is not None:
            rc = self._controller.proc.poll()
            if rc is not None and not self._last_exit_reported:
                self._append_log(f"[GUI] Process exited with code {rc}")
                self._set_status(f"Exited ({rc})")
                self._last_exit_reported = True

        self.after(120, self._pump_output)

    def _on_close(self) -> None:
        try:
            save_ui_state(self._collect_state_from_controls())
        except Exception:
            pass

        if self._controller.is_running():
            self._append_log("[GUI] Closing: stopping running process.")
            try:
                self._controller.stop(timeout=2.0)
            except Exception:
                pass
        self.destroy()


def _run_noninteractive_smoke() -> int:
    state = load_ui_state()
    state["source"] = "sine"
    state["headless"] = True
    state["max_frames"] = "20"
    state["fps"] = "30"
    state["accum"] = "avg"
    state["point_size_step"] = "7"
    state["point_render_style"] = "square_stamp"
    state["value_mode"] = "flat"
    state["rotation"] = "plus45"
    cmd = build_main_command_from_state(state)
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GUI launcher for sound-loopback-lissajous")
    parser.add_argument("--smoke", action="store_true", help="Run non-interactive GUI smoke command and exit")
    args = parser.parse_args(argv)

    if args.smoke:
        return _run_noninteractive_smoke()

    app = SoundLauncherGUI()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
