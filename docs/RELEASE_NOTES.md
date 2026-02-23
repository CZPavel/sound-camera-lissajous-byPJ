# Release Notes

## 0.2.1 - Loopback stabilization update

### Highlights
- `WasapiLoopbackSource` now prefers `pyaudiowpatch` for Windows WASAPI loopback endpoint capture.
- Default `loopback` behavior targets currently active Windows output endpoint (speakers/headphones).
- Legacy `sounddevice` route is retained as fallback for host compatibility.
- Documentation updates for backend behavior and troubleshooting.

### Dependency updates
- Added runtime dependency: `pyaudiowpatch>=0.2.12.8`

## 0.2.0 - Documentation and handover release

This release focuses on transferability and long-term maintainability.

### Highlights
- Unified technical + user documentation.
- PEKAT integration handover package (documentation only).
- Full context source bundle copied into the repository.
- Deterministic context manifest generation with checksums.

### Not in scope
- Direct integration into `PEKAT_inspection_tool_byPJ`.
- PEKAT runtime module implementation.

Integration is intentionally deferred to a later session on the second PC.
