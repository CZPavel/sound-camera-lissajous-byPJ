from __future__ import annotations

from gui import build_main_command_from_state, build_smoke_state
from gui_state import default_ui_state


def test_build_command_contains_core_arguments() -> None:
    state = default_ui_state()
    state.update(
        {
            "source": "sine",
            "tau": "both",
            "fps": "33",
            "window_ms": "150",
            "width": "320",
            "height": "320",
            "accum": "sum",
            "point_size_step": "6",
            "point_render_style": "square_stamp",
            "value_mode": "flat",
            "rotation": "minus45",
            "headless": True,
            "max_frames": "20",
            "log_every": "10",
            "fallback_on_fail": False,
        }
    )
    cmd = build_main_command_from_state(state, python_executable="python")

    assert cmd[:2] == ["python", "src/main.py"]
    assert "--source" in cmd and "sine" in cmd
    assert "--tau" in cmd and "both" in cmd
    assert "--headless" in cmd and "true" in cmd
    assert "--fallback-on-fail" in cmd and "false" in cmd
    assert "--max-frames" in cmd and "20" in cmd
    assert "--point-size-step" in cmd and "6" in cmd
    assert "--point-render-style" in cmd and "square_stamp" in cmd
    assert "--value-mode" in cmd and "flat" in cmd
    assert "--rotation" in cmd and "minus45" in cmd


def test_wav_path_is_added_conditionally() -> None:
    state = default_ui_state()
    state["source"] = "wav"
    state["wav_path"] = r"C:\tmp\test.wav"
    cmd = build_main_command_from_state(state, python_executable="python")
    assert "--wav-path" in cmd
    assert r"C:\tmp\test.wav" in cmd


def test_optional_numeric_args_omitted_when_blank() -> None:
    state = default_ui_state()
    state["sample_rate"] = ""
    state["channels"] = ""
    cmd = build_main_command_from_state(state, python_executable="python")
    assert "--sample-rate" not in cmd
    assert "--channels" not in cmd


def test_build_smoke_state_is_temporary_and_non_mutating() -> None:
    base = default_ui_state()
    base["source"] = "loopback"
    base["headless"] = False
    base["max_frames"] = "0"
    base["fps"] = "10"

    smoke = build_smoke_state(base)

    assert smoke["source"] == "sine"
    assert smoke["headless"] is True
    assert smoke["max_frames"] == "20"
    assert smoke["fps"] == "30"
    assert smoke["accum"] == "avg"
    assert smoke["point_size_step"] == "7"
    assert smoke["point_render_style"] == "square_stamp"
    assert smoke["value_mode"] == "flat"
    assert smoke["rotation"] == "plus45"

    # original must remain unchanged
    assert base["source"] == "loopback"
    assert base["headless"] is False
    assert base["max_frames"] == "0"
    assert base["fps"] == "10"
    assert base["point_render_style"] == "classic"
    assert base["value_mode"] == "radial"
    assert base["rotation"] == "none"
