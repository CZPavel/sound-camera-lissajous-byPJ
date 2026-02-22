# User Guide

## 1. What this app does

The app captures audio that is playing on the PC and renders it as dynamic Lissajous HSV images suitable for human annotation and vision pipelines.

## 2. Install and start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src/gui.py
```

## 3. GUI workflow

1. Choose **Source** (`loopback`, `wav`, `sine`).
2. For loopback, click **Refresh devices** and choose output endpoint.
3. Set tau (`1/5/10/20/50/both`), resolution, FPS, window and accumulation.
4. Optionally set save folder.
5. Click **Start**.
6. Stop with **Stop** or close app.

## 4. Recommended presets

### Sharp annotation-friendly trajectory
- `point_render_style = square_stamp`
- `accum = avg`
- `value_mode = flat`
- `rotation = plus45`
- `point_size_step = 5..7`

### Lightweight realtime preview
- `512x512`, `fps=10`, `window-ms=200`
- `point_size_step=1`
- `accum=none`

## 5. CLI examples

```powershell
python src/main.py --list-devices
python src/main.py --source loopback --device default --tau 20
python src/main.py --source sine --tau 50 --headless true --max-frames 20
python src/main.py --source wav --wav-path .\smoke_input.wav --save-dir .\out_frames
```

## 6. FAQ

**Q: Why does app stop quickly?**  
A: Check `max-frames`; set to `0` for continuous operation.

**Q: Why no image from smoke button?**  
A: Smoke runs headless by design.

**Q: Which tau should I pick?**  
A: Start with `tau=5`; compare with `10/20/50` for class separation.
