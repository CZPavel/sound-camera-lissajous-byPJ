# Decision Log

## D-001 Keep project standalone for now
Integration into PEKAT is deferred; this repository remains separate and portable.

## D-002 Default render settings stay backward-compatible
Default remains `tau=5`, `classic`, `radial`, `rotation=none`.

## D-003 Add sharp annotation style
`square_stamp` added to provide hard-edged larger points without soft neighborhood weighting.

## D-004 Rotation fit
For `plus45/minus45`, isotropic fit scaling is applied after rotation.

## D-005 Extended tau options
Added `tau=10`, `20`, `50` while keeping `both` as `tau1+tau5` tile.

## D-006 Documentation-first handover
Created dedicated integration docs (`docs/INTEGRATION/`) instead of implementing PEKAT integration now.

## D-007 Future notes captured
Next steps include:
- user validation of current version,
- script description refinements,
- "zvuková kamera" concept continuation.
