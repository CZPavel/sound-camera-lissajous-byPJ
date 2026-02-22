# PEKAT Interface Contract (Future)

## 1. Input contract
- Mono float signal window or stereo float window (stereo converted to mono by mean).
- Config:
  - `tau_mode` in `{1,5,10,20,50,both}`
  - `width`, `height`
  - `accum`, `point_size_step`, `point_render_style`, `value_mode`, `rotation`

## 2. Output contract
- `np.ndarray` frame with shape `(H,W,3)` for single tau, `(H,2W,3)` for `both`.
- `dtype=uint8`
- BGR for OpenCV workflows (`bgr=True`) and RGB optional.
- Optional PNG persistence.

## 3. Error/edge behavior
- If insufficient data: zero-padding, non-fatal warning.
- Silence-safe normalization with `1e-9` epsilon.
- Invalid settings rejected via explicit validation.

## 4. Expected defaults
- `tau=5`
- `fps=10`, `window-ms=200`
- `512x512`
- `accum=none`, `point_size_step=1`
- `point_render_style=classic`, `value_mode=radial`, `rotation=none`
