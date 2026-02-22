# Algorithm Specification

## 1. Delay embedding

For mono signal `x[n]` and integer delay `tau`:

- `X = x[n]`
- `Y = x[n+tau]`

Valid taus in app modes: `1, 5, 10, 20, 50`.

## 2. Normalization

- `Xn = X / (max(|X|) + 1e-9)`
- `Yn = Y / (max(|Y|) + 1e-9)`

## 3. Optional rotation

- `none`: no change
- `plus45`: rotate by `+pi/4`
- `minus45`: rotate by `-pi/4`

After rotation, isotropic fit scaling is applied:
- `scale = max(max(|xr|), max(|yr|), 1e-9)`
- `xr = xr / scale`
- `yr = yr / scale`

Then values are clipped to `[-1, 1]`.

## 4. Pixel mapping

For output width `W`, height `H`:

- `x_pix = floor(((xr + 1)/2) * (W-1))`
- `y_pix = floor((1 - ((yr + 1)/2)) * (H-1))`

## 5. HSV coloring

- Hue: `h = n/(N-1)`
- Saturation: `s = 1`
- Value modes:
  - `radial`: `a = sqrt(Xn^2 + Yn^2)`, `v = a/(max(a)+1e-9)`
  - `flat`: `v = 1`

HSV is converted to `uint8` RGB then optionally channel-reversed to BGR.

## 6. Point expansion (`point_size_step`)

- `radius = point_size_step - 1`, where `point_size_step in [1..7]`
- Styles:
  - `classic`: disk brush with soft radial weights
  - `sharp_stamp`: disk brush, uniform weight
  - `square_stamp`: square brush `[-r..r]x[-r..r]`, uniform weight

## 7. Pixel overlap handling (`accum`)

- `none`: last point overwrites
- `max`: channel-wise maximum
- `sum`: saturating channel-wise sum (clip 255)
- `avg`: per-pixel average over contributed point colors

## 8. Tau composition

- Single mode returns one frame.
- `both` concatenates tau1 and tau5 frames horizontally.
