# Technical Documentation

## 1. Runtime modules

- `src/main.py`
  - CLI parsing
  - source selection and fallback orchestration
  - render loop, display, save, timing
- `src/audio_capture.py`
  - `AudioRingBuffer`
  - `WasapiLoopbackSource`, `WavSource`, `SineSource`
  - device listing + default output resolution
  - backend order for loopback capture (`pyaudiowpatch` first, `sounddevice` fallback)
- `src/liss_render.py`
  - delay-embedding rendering
  - point brush expansion + overlap accumulation
  - tau tile composition (`both`)
- `src/gui.py`
  - Tkinter launcher
  - settings, process lifecycle, log capture
- `src/gui_state.py`
  - persisted UI state (`ui_state.json`)
- `src/utils.py`
  - HSV conversion helpers, timestamp and fps scheduler

## 2. End-to-end pipeline

1. Source produces latest audio samples.
2. Ring buffer decouples callback timing from render FPS.
3. Window extraction uses last `N = sr * window_ms/1000` samples.
4. Stereo data are mixed to mono (mean over channels).
5. `render_tau_mode` creates one image (`tau=1/5/10/20/50`) or tiled image (`both` = tau1 + tau5).
6. Output frame is shown (OpenCV) and optionally saved to PNG.

## 3. CLI contract

### Core
- `--fps`
- `--window-ms`
- `--tau {1,5,10,20,50,both}`
- `--width`, `--height`
- `--accum {none,max,sum,avg}`
- `--point-size-step {1..7}`
- `--point-render-style {classic,sharp_stamp,square_stamp}`
- `--value-mode {radial,flat}`
- `--rotation {none,plus45,minus45}`

### Source/fallback
- `--source {loopback,wav,sine}`
- `--device`
- `--wav-path`
- `--fallback-on-fail {true|false}`
- `--sample-rate`, `--channels`, `--sine-freq`
- `--list-devices`

### Runtime/testing
- `--headless {true|false}`
- `--max-frames`
- `--log-every`
- `--save-dir`

## 4. Performance and stability notes

- Vectorized NumPy implementation in renderer.
- Ring-buffer underruns are padded with zeros and reported.
- Silence-safe normalization (`+1e-9`) avoids NaN/Inf.
- Headless mode enables deterministic automated smoke tests.

## 5. Loopback backend selection

When `--source loopback` is used, runtime selects audio backend in this order:

1. `pyaudiowpatch` WASAPI loopback endpoint
- maps the selected/default Windows output endpoint to its loopback analogue,
- captures currently playing system audio from speakers/headphones endpoint.
2. `sounddevice` legacy path
- uses direct WASAPI loopback flag when available in the local PortAudio build,
- otherwise attempts an input loopback-like device (Stereo Mix style fallback).

This order prevents the common host-specific issue where loopback capture silently lands on microphone-style inputs.

## 6. Known constraints

- WASAPI behavior differs across PortAudio builds; fallback path may use "Stereo Mix" style input when direct loopback flag is unavailable.
- High resolutions + large brush size + `sum/avg` modes increase CPU and memory bandwidth demands.
