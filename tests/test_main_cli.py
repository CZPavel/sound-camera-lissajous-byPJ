from __future__ import annotations

import argparse

import pytest

from main import build_parser, str2bool


def test_cli_defaults_include_headless_and_max_frames() -> None:
    parser = build_parser()
    args = parser.parse_args([])

    assert args.tau == "5"
    assert args.source == "loopback"
    assert args.fallback_on_fail is True
    assert args.headless is False
    assert args.max_frames == 0
    assert args.log_every == 30
    assert args.point_size_step == 1
    assert args.accum == "none"
    assert args.point_render_style == "classic"
    assert args.value_mode == "radial"
    assert args.rotation == "none"


def test_cli_parses_custom_runtime_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--tau",
            "both",
            "--source",
            "sine",
            "--headless",
            "true",
            "--max-frames",
            "20",
            "--log-every",
            "5",
            "--fallback-on-fail",
            "false",
            "--accum",
            "avg",
            "--point-size-step",
            "7",
            "--point-render-style",
            "sharp_stamp",
            "--value-mode",
            "flat",
            "--rotation",
            "plus45",
        ]
    )

    assert args.tau == "both"
    assert args.source == "sine"
    assert args.headless is True
    assert args.max_frames == 20
    assert args.log_every == 5
    assert args.fallback_on_fail is False
    assert args.accum == "avg"
    assert args.point_size_step == 7
    assert args.point_render_style == "sharp_stamp"
    assert args.value_mode == "flat"
    assert args.rotation == "plus45"


def test_invalid_tau_is_rejected() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--tau", "7"])


def test_tau_10_is_accepted() -> None:
    parser = build_parser()
    args = parser.parse_args(["--tau", "10"])
    assert args.tau == "10"


def test_tau_20_and_50_are_accepted() -> None:
    parser = build_parser()
    args20 = parser.parse_args(["--tau", "20"])
    args50 = parser.parse_args(["--tau", "50"])
    assert args20.tau == "20"
    assert args50.tau == "50"


def test_invalid_point_size_step_is_rejected() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--point-size-step", "0"])


def test_invalid_rotation_is_rejected() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--rotation", "45"])


def test_square_stamp_is_accepted() -> None:
    parser = build_parser()
    args = parser.parse_args(["--point-render-style", "square_stamp"])
    assert args.point_render_style == "square_stamp"


def test_invalid_point_render_style_is_rejected() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--point-render-style", "square"])


def test_str2bool_rejects_invalid_value() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        str2bool("definitely")
