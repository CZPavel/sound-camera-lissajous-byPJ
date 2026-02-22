from __future__ import annotations

from pathlib import Path

from gui_state import default_ui_state, load_ui_state, save_ui_state


def test_load_missing_returns_defaults(tmp_path: Path) -> None:
    state_path = tmp_path / "missing_state.json"
    state = load_ui_state(state_path)
    assert state == default_ui_state()


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    state_path = tmp_path / "ui_state.json"
    payload = default_ui_state()
    payload["source"] = "sine"
    payload["tau"] = "both"
    payload["fps"] = "25"
    payload["fallback_on_fail"] = False
    payload["headless"] = True
    payload["point_size_step"] = "7"
    payload["point_render_style"] = "square_stamp"
    payload["value_mode"] = "flat"
    payload["rotation"] = "plus45"

    save_ui_state(payload, state_path)
    loaded = load_ui_state(state_path)

    assert loaded["source"] == "sine"
    assert loaded["tau"] == "both"
    assert loaded["fps"] == "25"
    assert loaded["fallback_on_fail"] is False
    assert loaded["headless"] is True
    assert loaded["point_size_step"] == "7"
    assert loaded["point_render_style"] == "square_stamp"
    assert loaded["value_mode"] == "flat"
    assert loaded["rotation"] == "plus45"


def test_load_corrupted_json_falls_back_to_defaults(tmp_path: Path) -> None:
    state_path = tmp_path / "broken.json"
    state_path.write_text("{ this is not valid json", encoding="utf-8")

    loaded = load_ui_state(state_path)
    assert loaded == default_ui_state()


def test_unknown_keys_are_ignored(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text('{"source":"wav","unknown_key":"x"}', encoding="utf-8")

    loaded = load_ui_state(state_path)
    assert loaded["source"] == "wav"
    assert "unknown_key" not in loaded


def test_missing_point_size_step_uses_default(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text('{"source":"sine"}', encoding="utf-8")

    loaded = load_ui_state(state_path)
    assert loaded["point_size_step"] == "1"
    assert loaded["point_render_style"] == "classic"
    assert loaded["value_mode"] == "radial"
    assert loaded["rotation"] == "none"
