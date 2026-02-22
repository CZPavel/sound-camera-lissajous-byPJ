from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from liss_render import render_lissajous_hsv, render_tau_mode


def _make_sine(num_samples: int, sr: int = 48000, freq: float = 440.0) -> np.ndarray:
    t = np.arange(num_samples, dtype=np.float32) / float(sr)
    return np.sin(2.0 * np.pi * freq * t).astype(np.float32)


def test_render_shape_and_dtype_tau1() -> None:
    samples = _make_sine(8192)
    frame = render_lissajous_hsv(samples, tau=1, width=256, height=256, accum="none", point_size_step=1, bgr=True)
    assert frame.shape == (256, 256, 3)
    assert frame.dtype == np.uint8


def test_silence_stability() -> None:
    samples = np.zeros(4096, dtype=np.float32)
    frame = render_lissajous_hsv(samples, tau=5, width=128, height=128, accum="none", point_size_step=1, bgr=True)
    assert frame.shape == (128, 128, 3)
    assert frame.dtype == np.uint8
    assert np.isfinite(frame).all()


def test_tau_variance() -> None:
    samples = _make_sine(12000, freq=777.0)
    frame_tau1 = render_lissajous_hsv(samples, tau=1, width=196, height=196, accum="none", point_size_step=1, bgr=True)
    frame_tau5 = render_lissajous_hsv(samples, tau=5, width=196, height=196, accum="none", point_size_step=1, bgr=True)
    assert not np.array_equal(frame_tau1, frame_tau5)


def test_accum_modes_max_and_sum() -> None:
    samples = np.ones(4000, dtype=np.float32)

    frame_max = render_lissajous_hsv(samples, tau=1, width=64, height=64, accum="max", point_size_step=1, bgr=True)
    frame_sum = render_lissajous_hsv(samples, tau=1, width=64, height=64, accum="sum", point_size_step=1, bgr=True)

    assert frame_max.dtype == np.uint8
    assert frame_sum.dtype == np.uint8
    assert frame_sum.max() <= 255
    assert frame_sum.max() == 255


def test_tau_both_tile_width() -> None:
    samples = _make_sine(6000)
    frame = render_tau_mode(samples, tau_mode="both", width=100, height=80, accum="none", point_size_step=1, bgr=True)
    assert frame.shape == (80, 200, 3)


def test_tau_10_mode_outputs_valid_frame() -> None:
    samples = _make_sine(7000, freq=510.0)
    frame_tau10 = render_tau_mode(samples, tau_mode="10", width=120, height=90, accum="none", point_size_step=1, bgr=True)
    frame_tau5 = render_tau_mode(samples, tau_mode="5", width=120, height=90, accum="none", point_size_step=1, bgr=True)
    assert frame_tau10.shape == (90, 120, 3)
    assert frame_tau10.dtype == np.uint8
    assert not np.array_equal(frame_tau10, frame_tau5)


def test_tau_20_and_50_modes_output_valid_frames() -> None:
    samples = _make_sine(9000, freq=430.0)
    frame_tau20 = render_tau_mode(samples, tau_mode="20", width=110, height=88, accum="none", point_size_step=1, bgr=True)
    frame_tau50 = render_tau_mode(samples, tau_mode="50", width=110, height=88, accum="none", point_size_step=1, bgr=True)
    assert frame_tau20.shape == (88, 110, 3)
    assert frame_tau50.shape == (88, 110, 3)
    assert frame_tau20.dtype == np.uint8
    assert frame_tau50.dtype == np.uint8
    assert not np.array_equal(frame_tau20, frame_tau50)


def test_point_size_step_increases_coverage() -> None:
    samples = _make_sine(9000, freq=510.0)
    frame_small = render_lissajous_hsv(samples, tau=5, width=140, height=140, accum="none", point_size_step=1, bgr=True)
    frame_big = render_lissajous_hsv(samples, tau=5, width=140, height=140, accum="none", point_size_step=7, bgr=True)

    nnz_small = int(np.count_nonzero(frame_small))
    nnz_big = int(np.count_nonzero(frame_big))
    assert nnz_big > nnz_small


def test_accum_avg_produces_distinct_result_on_overlap() -> None:
    samples = np.ones(7000, dtype=np.float32)
    frame_sum = render_lissajous_hsv(samples, tau=1, width=80, height=80, accum="sum", point_size_step=4, bgr=True)
    frame_avg = render_lissajous_hsv(samples, tau=1, width=80, height=80, accum="avg", point_size_step=4, bgr=True)

    assert frame_avg.dtype == np.uint8
    assert frame_sum.dtype == np.uint8
    assert not np.array_equal(frame_avg, frame_sum)
    assert frame_avg.max() <= 255


def test_tau_both_with_large_points_and_avg() -> None:
    samples = _make_sine(6000, freq=333.0)
    frame = render_tau_mode(
        samples,
        tau_mode="both",
        width=120,
        height=90,
        accum="avg",
        point_size_step=6,
        bgr=True,
    )
    assert frame.shape == (90, 240, 3)


def test_sharp_stamp_is_brighter_than_classic_for_large_points() -> None:
    samples = _make_sine(12000, freq=510.0)
    frame_classic = render_lissajous_hsv(
        samples,
        tau=5,
        width=160,
        height=160,
        accum="none",
        point_size_step=7,
        point_render_style="classic",
        bgr=True,
    )
    frame_sharp = render_lissajous_hsv(
        samples,
        tau=5,
        width=160,
        height=160,
        accum="none",
        point_size_step=7,
        point_render_style="sharp_stamp",
        bgr=True,
    )
    assert int(frame_sharp.sum()) > int(frame_classic.sum())


def test_value_mode_flat_differs_from_radial() -> None:
    samples = _make_sine(10000, freq=350.0)
    frame_radial = render_lissajous_hsv(
        samples,
        tau=5,
        width=128,
        height=128,
        accum="max",
        point_size_step=4,
        value_mode="radial",
        bgr=True,
    )
    frame_flat = render_lissajous_hsv(
        samples,
        tau=5,
        width=128,
        height=128,
        accum="max",
        point_size_step=4,
        value_mode="flat",
        bgr=True,
    )
    assert not np.array_equal(frame_radial, frame_flat)
    assert int(frame_flat.sum()) > int(frame_radial.sum())


def test_rotation_modes_change_output() -> None:
    samples = _make_sine(9000, freq=777.0)
    frame_none = render_lissajous_hsv(samples, tau=5, width=140, height=140, accum="none", rotation="none", bgr=True)
    frame_plus = render_lissajous_hsv(samples, tau=5, width=140, height=140, accum="none", rotation="plus45", bgr=True)
    frame_minus = render_lissajous_hsv(samples, tau=5, width=140, height=140, accum="none", rotation="minus45", bgr=True)
    assert not np.array_equal(frame_none, frame_plus)
    assert not np.array_equal(frame_none, frame_minus)


def test_rotation_plus45_uses_wide_canvas_span() -> None:
    rng = np.random.default_rng(0)
    samples = rng.uniform(-1.0, 1.0, 12000).astype(np.float32)
    frame = render_lissajous_hsv(
        samples,
        tau=5,
        width=220,
        height=220,
        accum="none",
        point_size_step=3,
        rotation="plus45",
        bgr=True,
    )
    mask = np.any(frame > 0, axis=2)
    ys, xs = np.where(mask)
    assert xs.size > 0 and ys.size > 0
    x_span = int(xs.max() - xs.min())
    y_span = int(ys.max() - ys.min())
    assert x_span > 190
    assert y_span > 190


def test_square_stamp_has_more_coverage_than_sharp_stamp() -> None:
    samples = _make_sine(12000, freq=420.0)
    frame_sharp = render_lissajous_hsv(
        samples,
        tau=5,
        width=160,
        height=160,
        accum="none",
        point_size_step=3,
        point_render_style="sharp_stamp",
        bgr=True,
    )
    frame_square = render_lissajous_hsv(
        samples,
        tau=5,
        width=160,
        height=160,
        accum="none",
        point_size_step=3,
        point_render_style="square_stamp",
        bgr=True,
    )
    assert int(np.count_nonzero(frame_square)) > int(np.count_nonzero(frame_sharp))


def test_square_stamp_with_avg_overlap_is_valid() -> None:
    samples = np.ones(8000, dtype=np.float32)
    frame_avg = render_lissajous_hsv(
        samples,
        tau=1,
        width=100,
        height=100,
        accum="avg",
        point_size_step=5,
        point_render_style="square_stamp",
        bgr=True,
    )
    frame_sum = render_lissajous_hsv(
        samples,
        tau=1,
        width=100,
        height=100,
        accum="sum",
        point_size_step=5,
        point_render_style="square_stamp",
        bgr=True,
    )
    assert frame_avg.dtype == np.uint8
    assert frame_avg.max() <= 255
    assert not np.array_equal(frame_avg, frame_sum)


def test_tau_both_with_all_new_modes() -> None:
    samples = _make_sine(7000, freq=278.0)
    frame = render_tau_mode(
        samples_mono=samples,
        tau_mode="both",
        width=100,
        height=90,
        accum="avg",
        point_size_step=7,
        point_render_style="square_stamp",
        value_mode="flat",
        rotation="plus45",
        bgr=True,
    )
    assert frame.shape == (90, 200, 3)
    assert frame.dtype == np.uint8
