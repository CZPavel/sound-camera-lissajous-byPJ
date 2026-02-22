# PEKAT Porting Checklist

## Pre-port checks
- [ ] Confirm target Python/OpenCV compatibility on notebook.
- [ ] Confirm target audio capture strategy (loopback vs external feed).
- [ ] Validate frame format expected by PEKAT workflow.

## Porting steps
1. Copy `src/liss_render.py` and associated utils.
2. Map PEKAT-side input signal source to renderer window input.
3. Replicate CLI/GUI setting schema into PEKAT config surface.
4. Validate output in PEKAT BGR pipeline with known sample clips.
5. Run classification/anotation sanity checks.

## Acceptance after port
- [ ] `tau` variants match standalone reference outputs.
- [ ] `square_stamp` behavior preserved.
- [ ] Rotation isotropic fit preserved.
- [ ] Runtime stable under silence and burst audio.
- [ ] End-user confirms expected visual readability.
