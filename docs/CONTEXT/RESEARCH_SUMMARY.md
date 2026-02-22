# Research Summary

## Objective
Create image-based representations of audio that are:
1. compatible with 8-bit BGR/RGB vision pipelines,
2. interpretable by human annotators,
3. robust for downstream ML workflows.

## Main explored families
- intensity-axis visualizations
- spectrogram-based variants
- lossless audio-to-image payload packing
- phase portraits / Lissajous embeddings
- heatmap and carrier-vs-FM mappings

## Final practical focus in current app
- Realtime Lissajous HSV rendering with configurable tau and brush modes
- stable output options for annotation and CV ingestion
- fallback operation for reproducible testing without live audio hardware

## Why this matters for future PEKAT work
- renderer already produces deterministic, bounded uint8 frames
- runtime controls map well to inspection-tool style settings
- context package preserves rationale for design decisions
