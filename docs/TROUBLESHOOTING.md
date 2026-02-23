# Troubleshooting

## 1. `Missing dependency 'sounddevice'`
Install runtime dependencies:

```powershell
pip install -r requirements.txt
```

## 2. Loopback cannot start
- Run `python src/main.py --list-devices`
- Try explicit `--device` index
- Keep `--fallback-on-fail true`
- Provide `--wav-path` for deterministic fallback

Additional checks for Windows output capture:
- Verify the active default playback endpoint in Windows Sound settings.
- Confirm that dependency `pyaudiowpatch` is installed from `requirements.txt`.
- In logs, prefer `mode='WASAPI loopback (pyaudiowpatch)'` for primary output capture.
- If the host does not support that path, the app can still run through legacy fallback, but capture source may differ by driver stack.

## 3. Image does not change
- Confirm system audio is actually playing on selected output endpoint.
- Lower `--fps` or adjust `--window-ms`.
- Try `--source sine` to isolate audio capture from rendering.

## 4. GUI starts but no visualization window
- Verify `headless` is false in GUI settings.
- Ensure `max-frames` is 0 for continuous run.
- Check GUI log panel for child process exit code and parameter echo.

## 5. Device name encoding oddities on Windows
Some host API labels may contain locale-dependent characters; selection by numeric device index is safest.

## 6. High CPU usage
Reduce one or more of:
- resolution (`width/height`)
- `point-size-step`
- `fps`
- accumulation complexity (`avg`/`sum`)

## 7. App reacts only to microphone-like input
This usually indicates fallback to a non-loopback input route on the host.

Recommended actions:
- Keep `--source loopback` and set `--device default` first.
- Switch Windows default output to the endpoint you actually monitor (speakers/headphones), then restart app.
- Reinstall dependencies and verify `pyaudiowpatch` import works.
- Use `python src/main.py --list-devices` and retest with explicit output device index.
