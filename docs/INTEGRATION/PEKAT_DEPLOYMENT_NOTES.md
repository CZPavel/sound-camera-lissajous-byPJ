# PEKAT Deployment Notes (Future)

## Recommended pattern
- Keep renderer as isolated module with explicit configuration interface.
- Separate audio capture concerns from rendering concerns.
- Preserve deterministic window timing for reproducibility.

## Runtime profiles
- **Light profile**: 512x512, fps 10, point_size 1
- **Annotation profile**: 1024x1024, square_stamp, avg, flat
- **Analysis profile**: compare multiple tau values over recorded clips

## Operational guidance
- Keep fallback source path for non-audio-HW environments.
- Keep smoke validation routine on each deployment target.
- Version-lock dependencies for reproducible behavior.
