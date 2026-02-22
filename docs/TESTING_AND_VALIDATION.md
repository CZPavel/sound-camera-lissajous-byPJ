# Testing and Validation

## Automated test suite

Run all tests:

```powershell
pytest -q
```

Coverage scope:
- Rendering shape/dtype/silence/tau variance
- Accumulation modes including `avg`
- Point styles and rotation behavior
- CLI parse and invalid argument rejection
- Ring buffer semantics and underrun handling
- GUI command generation, state persistence, process lifecycle
- Runtime smoke for `sine`, `wav`, and loopback fallback chain

## Smoke validation commands

```powershell
python src/main.py --source sine --headless true --max-frames 20
python src/main.py --source wav --wav-path .\smoke_input.wav --headless true --max-frames 12
python src/gui.py --smoke
```

## Manual validation checklist

1. `python src/main.py --list-devices` prints devices and default marker.
2. GUI launches and can Start/Stop process repeatedly.
3. Loopback image reacts to actual system audio.
4. `save-dir` produces valid PNG files.
5. `square_stamp + avg + flat + plus45` gives sharp, dense trajectories.

## Ready-for-handover checklist

- [ ] Tests green on target PC
- [ ] Loopback verified on target audio stack
- [ ] Context bundle copied and readable
- [ ] Integration docs reviewed by PEKAT-side implementer
