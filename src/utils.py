from __future__ import annotations

from datetime import datetime
import time

import numpy as np


def hsv_to_rgb_uint8(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Vectorized HSV(0..1) to RGB uint8 conversion."""
    h = np.asarray(h, dtype=np.float32)
    s = np.asarray(s, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)

    h = np.mod(h, 1.0)
    s = np.clip(s, 0.0, 1.0)
    v = np.clip(v, 0.0, 1.0)

    c = v * s
    h6 = h * 6.0
    x = c * (1.0 - np.abs((h6 % 2.0) - 1.0))
    m = v - c

    i = np.floor(h6).astype(np.int32) % 6

    r = np.zeros_like(v, dtype=np.float32)
    g = np.zeros_like(v, dtype=np.float32)
    b = np.zeros_like(v, dtype=np.float32)

    mask = i == 0
    r[mask], g[mask], b[mask] = c[mask], x[mask], 0.0

    mask = i == 1
    r[mask], g[mask], b[mask] = x[mask], c[mask], 0.0

    mask = i == 2
    r[mask], g[mask], b[mask] = 0.0, c[mask], x[mask]

    mask = i == 3
    r[mask], g[mask], b[mask] = 0.0, x[mask], c[mask]

    mask = i == 4
    r[mask], g[mask], b[mask] = x[mask], 0.0, c[mask]

    mask = i == 5
    r[mask], g[mask], b[mask] = c[mask], 0.0, x[mask]

    rgb = np.stack((r + m, g + m, b + m), axis=-1)
    return np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)


def now_timestamp_for_filename() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


def fps_scheduler_tick(target_fps: float, next_tick: float | None) -> float:
    if target_fps <= 0:
        raise ValueError("target_fps must be > 0")

    interval = 1.0 / float(target_fps)
    now = time.monotonic()

    if next_tick is None:
        next_tick = now + interval
    else:
        next_tick += interval
        if next_tick < now:
            next_tick = now + interval

    sleep_time = next_tick - time.monotonic()
    if sleep_time > 0:
        time.sleep(sleep_time)

    return next_tick
