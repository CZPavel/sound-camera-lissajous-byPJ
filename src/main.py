from __future__ import annotations

import argparse
from pathlib import Path
import sys

import cv2
import numpy as np

from audio_capture import (
    AudioSourceBase,
    SineSource,
    WasapiLoopbackSource,
    WavSource,
    list_audio_devices,
    resolve_default_output_device,
)
from liss_render import render_tau_mode
from utils import fps_scheduler_tick, now_timestamp_for_filename


def str2bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    value = value.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Cannot parse boolean value from '{value}'.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Realtime WASAPI loopback -> Lissajous HSV renderer (tau=1/5/both)."
    )

    parser.add_argument("--fps", type=float, default=10.0, help="Rendering FPS (default: 10)")
    parser.add_argument("--window-ms", type=float, default=200.0, help="Audio window size in milliseconds")
    parser.add_argument("--tau", choices=["1", "5", "10", "20", "50", "both"], default="5", help="Tau mode")
    parser.add_argument("--width", type=int, default=512, help="Output width")
    parser.add_argument("--height", type=int, default=512, help="Output height")
    parser.add_argument("--device", default="default", help="Audio output device id/name or 'default'")
    parser.add_argument("--accum", choices=["none", "max", "sum", "avg"], default="none", help="Pixel accumulation mode")
    parser.add_argument(
        "--point-size-step",
        type=int,
        choices=range(1, 8),
        default=1,
        help="Point size step 1..7 (step=1 is single pixel).",
    )
    parser.add_argument(
        "--point-render-style",
        choices=["classic", "sharp_stamp", "square_stamp"],
        default="classic",
        help="Point rendering style (classic softer brush vs sharp stamped brush).",
    )
    parser.add_argument(
        "--value-mode",
        choices=["radial", "flat"],
        default="radial",
        help="Point value mode (radial = intensity by distance from center, flat = uniform value).",
    )
    parser.add_argument(
        "--rotation",
        choices=["none", "plus45", "minus45"],
        default="none",
        help="Rotate normalized coordinates before pixel mapping.",
    )
    parser.add_argument("--save-dir", default=None, help="Optional directory for PNG frame saving")

    parser.add_argument("--list-devices", action="store_true", help="List available sound devices and exit")

    parser.add_argument("--source", choices=["loopback", "wav", "sine"], default="loopback", help="Audio source")
    parser.add_argument("--wav-path", default=None, help="Path to WAV file (used when --source wav, or loopback fallback)")
    parser.add_argument(
        "--fallback-on-fail",
        type=str2bool,
        default=True,
        help="If loopback init fails: fallback to WAV (if provided) or sine",
    )

    parser.add_argument("--sample-rate", type=int, default=None, help="Optional override sample rate")
    parser.add_argument("--channels", type=int, default=None, help="Optional requested channel count")
    parser.add_argument("--sine-freq", type=float, default=440.0, help="Sine fallback frequency in Hz")
    parser.add_argument(
        "--headless",
        type=str2bool,
        default=False,
        help="Disable GUI window rendering (useful for automated smoke tests)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Stop automatically after N rendered frames (0 = unlimited)",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=30,
        help="Print runtime progress every N frames (0 disables periodic progress log)",
    )

    return parser


def print_devices() -> int:
    try:
        rows = list_audio_devices()
    except Exception as exc:
        print(f"[ERROR] Cannot list audio devices: {exc}")
        return 2

    if not rows:
        print("No audio devices returned by sounddevice.")
        return 1

    try:
        default_out = resolve_default_output_device()
    except Exception:
        default_out = None

    print("Available audio devices:")
    print("Idx  DefOut HostAPI              In  Out  DefaultSR  Name")
    print("---  ------ -------------------- --- ---  ---------  ----")
    for row in rows:
        marker = "*" if row["index"] == default_out else " "
        print(
            f"{row['index']:>3}  {marker:^6} {row['hostapi_name'][:20]:20} "
            f"{row['max_input_channels']:>3} {row['max_output_channels']:>3} "
            f"{row['default_samplerate']:>9.1f}  {row['name']}"
        )
    return 0


def _build_source_from_args(args: argparse.Namespace, force_source: str | None = None) -> AudioSourceBase:
    selected = force_source or args.source

    if selected == "loopback":
        return WasapiLoopbackSource(
            device=args.device,
            sample_rate=args.sample_rate,
            channels=args.channels,
        )

    if selected == "wav":
        if not args.wav_path:
            raise RuntimeError("--wav-path is required when --source wav")
        return WavSource(args.wav_path)

    if selected == "sine":
        return SineSource(
            sample_rate=args.sample_rate or 48000,
            frequency_hz=args.sine_freq,
            channels=max(1, args.channels or 1),
        )

    raise RuntimeError(f"Unsupported source: {selected}")


def _to_mono(window: np.ndarray) -> np.ndarray:
    arr = np.asarray(window, dtype=np.float32)
    if arr.ndim == 1:
        return arr
    if arr.ndim == 2:
        return arr.mean(axis=1, dtype=np.float32)
    raise RuntimeError(f"Unexpected window shape: {arr.shape}")


def run_app(args: argparse.Namespace) -> int:
    source: AudioSourceBase | None = None

    try:
        try:
            source = _build_source_from_args(args)
            source.start()
        except Exception as exc:
            if args.source == "loopback" and args.fallback_on_fail:
                print(f"[WARN] Loopback init failed: {exc}")
                if args.wav_path:
                    print("[INFO] Falling back to WAV source.")
                    source = _build_source_from_args(args, force_source="wav")
                else:
                    print("[INFO] Falling back to sine source.")
                    source = _build_source_from_args(args, force_source="sine")
                source.start()
            else:
                raise

        if args.save_dir:
            save_dir = Path(args.save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Saving PNG frames to: {save_dir}")
        else:
            save_dir = None

        window_samples = max(2, int(round(source.sample_rate * (args.window_ms / 1000.0))))
        print(
            f"[INFO] Runtime config | source={source.__class__.__name__} sr={source.sample_rate} "
            f"channels={source.channels} fps={args.fps} window_ms={args.window_ms} "
            f"window_samples={window_samples} tau={args.tau} size={args.width}x{args.height} accum={args.accum} "
            f"point_size_step={args.point_size_step} point_render_style={args.point_render_style} "
            f"value_mode={args.value_mode} rotation={args.rotation} "
            f"headless={args.headless} max_frames={args.max_frames}"
        )

        title = f"Lissajous HSV | tau={args.tau} | source={source.__class__.__name__}"
        frame_idx = 0
        next_tick = None

        while True:
            window = source.get_window(window_samples)
            mono = _to_mono(window)

            frame = render_tau_mode(
                samples_mono=mono,
                tau_mode=args.tau,
                width=args.width,
                height=args.height,
                accum=args.accum,
                point_size_step=args.point_size_step,
                point_render_style=args.point_render_style,
                value_mode=args.value_mode,
                rotation=args.rotation,
                bgr=True,
            )

            if not args.headless:
                cv2.imshow(title, frame)

            if save_dir is not None:
                filename = f"frame_{now_timestamp_for_filename()}_{frame_idx:06d}.png"
                out_path = save_dir / filename
                ok = cv2.imwrite(str(out_path), frame)
                if not ok:
                    print(f"[WARN] Failed to save frame: {out_path}")

            if not args.headless:
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    print("[INFO] Exit requested by user.")
                    break

            frame_idx += 1
            if args.log_every and frame_idx % args.log_every == 0:
                print(f"[INFO] Rendered frames: {frame_idx}")

            if args.max_frames and frame_idx >= args.max_frames:
                print(f"[INFO] Reached max-frames={args.max_frames}, stopping.")
                break

            next_tick = fps_scheduler_tick(args.fps, next_tick)

    except KeyboardInterrupt:
        print("[INFO] Interrupted by keyboard.")
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1
    finally:
        if source is not None:
            try:
                source.stop()
            except Exception as stop_exc:
                print(f"[WARN] Source stop failed: {stop_exc}")
        if not args.headless:
            cv2.destroyAllWindows()

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_devices:
        return print_devices()

    return run_app(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
