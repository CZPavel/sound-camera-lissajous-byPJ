# PEKAT Risk Register

| ID | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| R1 | Loopback behavior differs between machines | High | Medium | Keep wav/sine fallback and explicit device selection |
| R2 | CPU load too high at large resolution + brush | Medium | Medium | Provide runtime profiles, cap defaults |
| R3 | Output visual semantics misunderstood by users | Medium | Medium | Add user validation round + curated presets |
| R4 | Inconsistent dependency versions | Medium | Medium | Pin versions and run smoke tests after install |
| R5 | Encoding/path issues on Windows locale | Low | Medium | Prefer numeric device IDs and ASCII-safe context filenames |

## Open actions
- Perform user acceptance test of current visual presets.
- Refine script descriptions in context package.
- Prepare dedicated "zvuková kamera" concept branch.
