# Changelog

All notable changes to this project are documented here.

## [0.2.0] - 2026-02-22
### Added
- Documentation consolidation package under `docs/`.
- PEKAT handover documentation under `docs/INTEGRATION/`.
- Full context source copy under `context_sources/aa_sound_test/`.
- Context manifest generator script: `scripts/build_context_manifest.py`.
- Handover export script: `scripts/export_handover_bundle.ps1`.
- New tau options: `10`, `20`, `50`.
- New rendering mode: `square_stamp`.
- Rotational isotropic fit for `plus45` / `minus45`.

## [0.1.0] - 2026-02-22
### Added
- Realtime WASAPI loopback capture + fallback (`wav` / `sine`).
- Lissajous HSV rendering pipeline with tau modes `1`, `5`, `both`.
- GUI launcher with persistent settings.
- Tests for renderer, CLI, GUI helpers and runtime smoke.
