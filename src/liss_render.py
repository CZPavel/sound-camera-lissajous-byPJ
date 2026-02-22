from __future__ import annotations

from functools import lru_cache
from typing import Literal

import numpy as np

from utils import hsv_to_rgb_uint8

AccumMode = Literal["none", "max", "sum", "avg"]
TauMode = Literal["1", "5", "10", "20", "50", "both"]
PointRenderStyle = Literal["classic", "sharp_stamp", "square_stamp"]
ValueMode = Literal["radial", "flat"]
RotationMode = Literal["none", "plus45", "minus45"]


def _prepare_xy(samples_mono: np.ndarray, tau: int) -> tuple[np.ndarray, np.ndarray]:
    if tau <= 0:
        raise ValueError("tau must be a positive integer")

    samples = np.asarray(samples_mono, dtype=np.float32).reshape(-1)
    if samples.size <= tau:
        return np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.float32)

    x = samples[:-tau]
    y = samples[tau:]
    return x, y


def _accumulate_pixels(
    image: np.ndarray,
    y_pix: np.ndarray,
    x_pix: np.ndarray,
    rgb: np.ndarray,
    accum: AccumMode,
) -> np.ndarray:
    if accum == "none":
        image[y_pix, x_pix] = rgb
        return image

    if accum == "max":
        for c in range(3):
            np.maximum.at(image[..., c], (y_pix, x_pix), rgb[:, c])
        return image

    if accum == "sum":
        work = np.zeros_like(image, dtype=np.uint32)
        for c in range(3):
            np.add.at(work[..., c], (y_pix, x_pix), rgb[:, c].astype(np.uint32))
        np.clip(work, 0, 255, out=work)
        return work.astype(np.uint8)

    if accum == "avg":
        sum_rgb = np.zeros_like(image, dtype=np.uint32)
        count = np.zeros(image.shape[:2], dtype=np.uint32)
        for c in range(3):
            np.add.at(sum_rgb[..., c], (y_pix, x_pix), rgb[:, c].astype(np.uint32))
        np.add.at(count, (y_pix, x_pix), 1)

        count_nonzero = np.maximum(count, 1)[:, :, None]
        avg = sum_rgb / count_nonzero
        return np.clip(np.round(avg), 0, 255).astype(np.uint8)

    raise ValueError(f"Unsupported accum mode: {accum}")


@lru_cache(maxsize=32)
def _disk_brush(radius: int, point_render_style: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if radius <= 0:
        return (
            np.array([0], dtype=np.int32),
            np.array([0], dtype=np.int32),
            np.array([1.0], dtype=np.float32),
        )

    if point_render_style == "square_stamp":
        yy, xx = np.mgrid[-radius : radius + 1, -radius : radius + 1]
        dx = xx.reshape(-1).astype(np.int32)
        dy = yy.reshape(-1).astype(np.int32)
        w = np.ones(dx.shape[0], dtype=np.float32)
        return dx, dy, w

    yy, xx = np.mgrid[-radius : radius + 1, -radius : radius + 1]
    dist = np.sqrt((xx * xx + yy * yy).astype(np.float32))
    mask = dist <= float(radius)
    dx = xx[mask].astype(np.int32)
    dy = yy[mask].astype(np.int32)

    if point_render_style == "classic":
        # Keep a softer look for larger brush sizes.
        # 1.0 at center, gradually down to 0.35 near brush edge.
        d = dist[mask]
        w = 1.0 - (d / (radius + 1e-9)) * 0.65
        w = np.clip(w, 0.35, 1.0).astype(np.float32)
    elif point_render_style == "sharp_stamp":
        w = np.ones(dx.shape[0], dtype=np.float32)
    else:
        raise ValueError(f"Unsupported point_render_style: {point_render_style}")

    return dx, dy, w


def _expand_points_with_disk(
    x_pix: np.ndarray,
    y_pix: np.ndarray,
    rgb: np.ndarray,
    width: int,
    height: int,
    radius: int,
    point_render_style: PointRenderStyle,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if radius <= 0:
        return x_pix, y_pix, rgb

    dx, dy, weights = _disk_brush(radius, point_render_style)
    # broadcast points with brush offsets
    xp = x_pix[:, None] + dx[None, :]
    yp = y_pix[:, None] + dy[None, :]
    valid = (xp >= 0) & (xp < width) & (yp >= 0) & (yp < height)

    if not np.any(valid):
        return (
            np.empty((0,), dtype=np.int32),
            np.empty((0,), dtype=np.int32),
            np.empty((0, 3), dtype=np.uint8),
        )

    x_exp = xp[valid].astype(np.int32, copy=False)
    y_exp = yp[valid].astype(np.int32, copy=False)
    rgb_exp = np.repeat(rgb[:, None, :], dx.size, axis=1).astype(np.float32)
    rgb_exp *= weights[None, :, None]
    rgb_exp = rgb_exp[valid]
    return x_exp, y_exp, np.clip(np.round(rgb_exp), 0, 255).astype(np.uint8)


def _rotate_xy(xn: np.ndarray, yn: np.ndarray, rotation: RotationMode | str) -> tuple[np.ndarray, np.ndarray]:
    mode = str(rotation)
    if mode == "none":
        return xn, yn

    if mode == "plus45":
        theta = np.pi / 4.0
    elif mode == "minus45":
        theta = -np.pi / 4.0
    else:
        raise ValueError("rotation must be one of: 'none', 'plus45', 'minus45'")

    c = np.cos(theta).astype(np.float32)
    s = np.sin(theta).astype(np.float32)
    xr = (c * xn) - (s * yn)
    yr = (s * xn) + (c * yn)

    # Isotropic fit scale after rotation so rotated portrait uses full range
    # while preserving aspect ratio (single shared scale factor).
    max_abs = max(float(np.max(np.abs(xr))), float(np.max(np.abs(yr))), 1e-9)
    xr = xr / max_abs
    yr = yr / max_abs

    np.clip(xr, -1.0, 1.0, out=xr)
    np.clip(yr, -1.0, 1.0, out=yr)
    return xr, yr


def render_lissajous_hsv(
    samples_mono: np.ndarray,
    tau: int,
    width: int,
    height: int,
    accum: AccumMode = "none",
    point_size_step: int = 1,
    point_render_style: PointRenderStyle = "classic",
    value_mode: ValueMode = "radial",
    rotation: RotationMode = "none",
    bgr: bool = True,
) -> np.ndarray:
    """
    Render Lissajous/phase portrait according to the required algorithm:
      X = x[n], Y = x[n+tau]
      Xn = X / (max(|X|) + 1e-9)
      Yn = Y / (max(|Y|) + 1e-9)
      x_pix = floor(((Xn + 1)/2) * (W-1))
      y_pix = floor((1 - ((Yn + 1)/2)) * (H-1))
      hue = n/(N-1), sat = 1,
      value = sqrt(Xn^2 + Yn^2) / (max(a)+1e-9)
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if not (1 <= int(point_size_step) <= 7):
        raise ValueError("point_size_step must be in range 1..7")
    if point_render_style not in ("classic", "sharp_stamp", "square_stamp"):
        raise ValueError("point_render_style must be one of: 'classic', 'sharp_stamp', 'square_stamp'")
    if value_mode not in ("radial", "flat"):
        raise ValueError("value_mode must be one of: 'radial', 'flat'")

    image = np.zeros((height, width, 3), dtype=np.uint8)

    x, y = _prepare_xy(samples_mono, tau)
    n_points = x.size
    if n_points == 0:
        return image[..., ::-1] if bgr else image

    xn = x / (np.max(np.abs(x)) + 1e-9)
    yn = y / (np.max(np.abs(y)) + 1e-9)

    xr, yr = _rotate_xy(xn, yn, rotation)

    x_pix = np.floor(((xr + 1.0) / 2.0) * (width - 1)).astype(np.int32)
    y_pix = np.floor((1.0 - ((yr + 1.0) / 2.0)) * (height - 1)).astype(np.int32)
    np.clip(x_pix, 0, width - 1, out=x_pix)
    np.clip(y_pix, 0, height - 1, out=y_pix)

    if n_points == 1:
        h = np.array([0.0], dtype=np.float32)
    else:
        h = np.arange(n_points, dtype=np.float32) / float(n_points - 1)

    s = np.ones(n_points, dtype=np.float32)
    if value_mode == "radial":
        a = np.sqrt(xn * xn + yn * yn)
        v = a / (np.max(a) + 1e-9)
    else:
        v = np.ones(n_points, dtype=np.float32)

    rgb = hsv_to_rgb_uint8(h, s, v)
    radius = int(point_size_step) - 1
    x_draw, y_draw, rgb_draw = _expand_points_with_disk(
        x_pix=x_pix,
        y_pix=y_pix,
        rgb=rgb,
        width=width,
        height=height,
        radius=radius,
        point_render_style=point_render_style,
    )
    image = _accumulate_pixels(image, y_draw, x_draw, rgb_draw, accum)

    return image[..., ::-1] if bgr else image


def render_tau_mode(
    samples_mono: np.ndarray,
    tau_mode: TauMode | str,
    width: int,
    height: int,
    accum: AccumMode = "none",
    point_size_step: int = 1,
    point_render_style: PointRenderStyle = "classic",
    value_mode: ValueMode = "radial",
    rotation: RotationMode = "none",
    bgr: bool = True,
) -> np.ndarray:
    tau_mode = str(tau_mode)

    if tau_mode == "1":
        return render_lissajous_hsv(
            samples_mono,
            tau=1,
            width=width,
            height=height,
            accum=accum,
            point_size_step=point_size_step,
            point_render_style=point_render_style,
            value_mode=value_mode,
            rotation=rotation,
            bgr=bgr,
        )

    if tau_mode == "5":
        return render_lissajous_hsv(
            samples_mono,
            tau=5,
            width=width,
            height=height,
            accum=accum,
            point_size_step=point_size_step,
            point_render_style=point_render_style,
            value_mode=value_mode,
            rotation=rotation,
            bgr=bgr,
        )

    if tau_mode == "10":
        return render_lissajous_hsv(
            samples_mono,
            tau=10,
            width=width,
            height=height,
            accum=accum,
            point_size_step=point_size_step,
            point_render_style=point_render_style,
            value_mode=value_mode,
            rotation=rotation,
            bgr=bgr,
        )

    if tau_mode == "20":
        return render_lissajous_hsv(
            samples_mono,
            tau=20,
            width=width,
            height=height,
            accum=accum,
            point_size_step=point_size_step,
            point_render_style=point_render_style,
            value_mode=value_mode,
            rotation=rotation,
            bgr=bgr,
        )

    if tau_mode == "50":
        return render_lissajous_hsv(
            samples_mono,
            tau=50,
            width=width,
            height=height,
            accum=accum,
            point_size_step=point_size_step,
            point_render_style=point_render_style,
            value_mode=value_mode,
            rotation=rotation,
            bgr=bgr,
        )

    if tau_mode == "both":
        left = render_lissajous_hsv(
            samples_mono,
            tau=1,
            width=width,
            height=height,
            accum=accum,
            point_size_step=point_size_step,
            point_render_style=point_render_style,
            value_mode=value_mode,
            rotation=rotation,
            bgr=bgr,
        )
        right = render_lissajous_hsv(
            samples_mono,
            tau=5,
            width=width,
            height=height,
            accum=accum,
            point_size_step=point_size_step,
            point_render_style=point_render_style,
            value_mode=value_mode,
            rotation=rotation,
            bgr=bgr,
        )
        return np.concatenate([left, right], axis=1)

    raise ValueError("tau_mode must be one of: '1', '5', '10', '20', '50', 'both'")
