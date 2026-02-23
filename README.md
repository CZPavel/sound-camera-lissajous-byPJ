# sound-loopback-lissajous

Standalone Windows 10/11 Python application:

**System audio (WASAPI loopback) -> Lissajous HSV renderer -> BGR/RGB 8-bit frames (OpenCV/PNG).**

This repository includes a full documentation + context package prepared for future porting into `PEKAT_inspection_tool_byPJ`.

---

## Quick start

```powershell
cd C:\PYTHON_test\VS_CODE_PROJECTS\sound-loopback-lissajous
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run GUI:

```powershell
python src/gui.py
```

Run CLI (default loopback):

```powershell
python src/main.py
```

Smoke run (headless):

```powershell
python src/main.py --source sine --headless true --max-frames 20
```

---

## Core capabilities

- Audio sources: `loopback`, `wav`, `sine`
- Loopback backend preference: `pyaudiowpatch` WASAPI loopback endpoint for current Windows default output, with `sounddevice` legacy fallback
- Tau modes: `1`, `5`, `10`, `20`, `50`, `both`
- Point rendering: `classic`, `sharp_stamp`, `square_stamp`
- Value modes: `radial`, `flat`
- Rotation: `none`, `plus45`, `minus45` (+ isotropic fit on rotated modes)
- Pixel overlap accumulation: `none`, `max`, `sum`, `avg`
- Optional frame saving (`--save-dir`)

---

## Documentation map

- Technical runtime: `docs/TECHNICAL.md`
- Algorithm details: `docs/ALGORITHM_SPEC.md`
- User usage guide: `docs/USER_GUIDE.md`
- Architecture and data flow: `docs/ARCHITECTURE.md`
- Testing and validation: `docs/TESTING_AND_VALIDATION.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`

### Future PEKAT handover docs
- `docs/INTEGRATION/PEKAT_BRIDGE_OVERVIEW.md`
- `docs/INTEGRATION/PEKAT_INTERFACE_CONTRACT.md`
- `docs/INTEGRATION/PEKAT_PORTING_CHECKLIST.md`
- `docs/INTEGRATION/PEKAT_DEPLOYMENT_NOTES.md`
- `docs/INTEGRATION/PEKAT_RISK_REGISTER.md`

### Context package
- Source copies: `context_sources/aa_sound_test/`
- Source index + summary + decisions + checksums: `docs/CONTEXT/`

---

## Testing

```powershell
pytest -q
python src/gui.py --smoke
```

## Audio backend note

- The default `loopback` path now targets the active Windows output endpoint (speakers/headphones) via `pyaudiowpatch`.
- If this path is unavailable on a host, runtime falls back to the legacy `sounddevice` path.

---

## Sync reminder

- Before next work round: `sync-codex.ps1 -Mode Down`
- After finishing round: `sync-codex.ps1 -Mode Up`
