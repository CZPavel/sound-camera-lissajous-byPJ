from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_STATE_PATH = PROJECT_ROOT / "ui_state.json"

DEFAULT_UI_STATE: dict[str, Any] = {
    "source": "loopback",
    "device": "default",
    "tau": "5",
    "fps": "10",
    "window_ms": "200",
    "width": "512",
    "height": "512",
    "accum": "none",
    "point_size_step": "1",
    "point_render_style": "classic",
    "value_mode": "radial",
    "rotation": "none",
    "wav_path": "",
    "save_dir": "",
    "fallback_on_fail": True,
    "headless": False,
    "max_frames": "0",
    "log_every": "30",
    "sample_rate": "",
    "channels": "",
    "sine_freq": "440",
}


def default_ui_state() -> dict[str, Any]:
    return dict(DEFAULT_UI_STATE)


def get_ui_state_path(path: str | Path | None = None) -> Path:
    if path is None:
        return UI_STATE_PATH
    return Path(path)


def _sanitize_state(candidate: dict[str, Any]) -> dict[str, Any]:
    out = default_ui_state()
    for key in out:
        if key in candidate:
            out[key] = candidate[key]

    out["fallback_on_fail"] = bool(out["fallback_on_fail"])
    out["headless"] = bool(out["headless"])
    return out


def load_ui_state(path: str | Path | None = None) -> dict[str, Any]:
    state_path = get_ui_state_path(path)
    if not state_path.exists():
        return default_ui_state()

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return default_ui_state()

    if not isinstance(data, dict):
        return default_ui_state()

    return _sanitize_state(data)


def save_ui_state(state: dict[str, Any], path: str | Path | None = None) -> Path:
    state_path = get_ui_state_path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _sanitize_state(state)
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return state_path
