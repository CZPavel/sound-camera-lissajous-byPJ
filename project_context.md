# Project Context

## Goal
Build and validate a standalone Windows audio-visualization application that converts realtime system output audio into image frames suitable for vision pipelines and human annotation.

## Current scope
- Standalone local app (CLI + GUI launcher)
- Realtime loopback with robust fallbacks (`wav`, `sine`)
- Deterministic frame synthesis using delay embedding and HSV mapping
- Exportable PNG/BGR frames for downstream processing

## Integration status
Integration into `PEKAT_inspection_tool_byPJ` is intentionally deferred.
This repository includes complete handover documentation under `docs/INTEGRATION/` for later implementation on a second PC.

## Documentation contract
- Runtime source of truth: `docs/TECHNICAL.md`
- Algorithm source of truth: `docs/ALGORITHM_SPEC.md`
- User operation source of truth: `docs/USER_GUIDE.md`
- Context and decisions: `docs/CONTEXT/`

## Future work notes
- User validation of current behavior is required before integration.
- Script descriptions for context assets should be refined with domain experts.
- "Zvuková kamera" concept is the next strategic branch.
