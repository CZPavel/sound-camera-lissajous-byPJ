from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import inspect
import threading
import time
import wave
from abc import ABC, abstractmethod

import numpy as np


class AudioRingBuffer:
    """Thread-safe ring buffer storing float32 audio frames as [samples, channels]."""

    def __init__(self, capacity_samples: int, channels: int) -> None:
        if capacity_samples <= 0:
            raise ValueError("capacity_samples must be > 0")
        if channels <= 0:
            raise ValueError("channels must be > 0")

        self.capacity_samples = int(capacity_samples)
        self.channels = int(channels)
        self._data = np.zeros((self.capacity_samples, self.channels), dtype=np.float32)
        self._write_pos = 0
        self._size = 0
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        with self._lock:
            return self._size

    def write(self, frames: np.ndarray) -> None:
        arr = np.asarray(frames, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr[:, None]
        if arr.ndim != 2:
            raise ValueError("frames must be shape [samples] or [samples, channels]")

        if arr.shape[1] != self.channels:
            if arr.shape[1] > self.channels:
                arr = arr[:, : self.channels]
            else:
                pad = np.zeros((arr.shape[0], self.channels - arr.shape[1]), dtype=np.float32)
                arr = np.concatenate([arr, pad], axis=1)

        n = int(arr.shape[0])
        if n == 0:
            return

        with self._lock:
            if n >= self.capacity_samples:
                arr = arr[-self.capacity_samples :]
                n = arr.shape[0]
                self._data[:, :] = arr
                self._write_pos = 0
                self._size = self.capacity_samples
                return

            end = self._write_pos + n
            if end <= self.capacity_samples:
                self._data[self._write_pos : end] = arr
            else:
                first = self.capacity_samples - self._write_pos
                self._data[self._write_pos :] = arr[:first]
                self._data[: end % self.capacity_samples] = arr[first:]

            self._write_pos = end % self.capacity_samples
            self._size = min(self.capacity_samples, self._size + n)

    def read_latest(self, num_samples: int) -> np.ndarray:
        num_samples = int(max(1, num_samples))
        out = np.zeros((num_samples, self.channels), dtype=np.float32)

        with self._lock:
            available = min(num_samples, self._size)
            if available <= 0:
                return out

            start = (self._write_pos - available) % self.capacity_samples
            if start + available <= self.capacity_samples:
                recent = self._data[start : start + available]
            else:
                first = self.capacity_samples - start
                recent = np.concatenate([self._data[start:], self._data[: available - first]], axis=0)

        out[-available:] = recent
        return out


def _require_sounddevice():
    try:
        import sounddevice as sd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'sounddevice'. Install requirements.txt first."
        ) from exc
    return sd


def list_audio_devices() -> list[dict]:
    sd = _require_sounddevice()
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    default_input, default_output = sd.default.device

    result: list[dict] = []
    for idx, dev in enumerate(devices):
        hostapi_index = int(dev.get("hostapi", -1))
        hostapi_name = (
            hostapis[hostapi_index].get("name", str(hostapi_index))
            if 0 <= hostapi_index < len(hostapis)
            else str(hostapi_index)
        )

        result.append(
            {
                "index": idx,
                "name": dev.get("name", ""),
                "hostapi_index": hostapi_index,
                "hostapi_name": hostapi_name,
                "max_input_channels": int(dev.get("max_input_channels", 0)),
                "max_output_channels": int(dev.get("max_output_channels", 0)),
                "default_samplerate": float(dev.get("default_samplerate", 0.0)),
                "is_default_input": idx == default_input,
                "is_default_output": idx == default_output,
            }
        )
    return result


def resolve_default_output_device(sd=None) -> int:
    if sd is None:
        sd = _require_sounddevice()

    default_output = sd.default.device[1]
    if default_output is not None and int(default_output) >= 0:
        return int(default_output)

    devices = sd.query_devices()
    hostapis = sd.query_hostapis()

    for idx, dev in enumerate(devices):
        if int(dev.get("max_output_channels", 0)) <= 0:
            continue
        hostapi_index = int(dev.get("hostapi", -1))
        hostapi_name = (
            hostapis[hostapi_index].get("name", "")
            if 0 <= hostapi_index < len(hostapis)
            else ""
        )
        if "WASAPI" in str(hostapi_name).upper():
            return idx

    for idx, dev in enumerate(devices):
        if int(dev.get("max_output_channels", 0)) > 0:
            return idx

    raise RuntimeError("No output audio device found.")


class AudioSourceBase(ABC):
    sample_rate: int
    channels: int

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_window(self, num_samples: int) -> np.ndarray:
        raise NotImplementedError


class WasapiLoopbackSource(AudioSourceBase):
    def __init__(
        self,
        device: str = "default",
        sample_rate: int | None = None,
        channels: int | None = None,
        blocksize: int = 0,
        buffer_seconds: float = 5.0,
    ) -> None:
        self._sd = _require_sounddevice()
        self.device = device
        self.requested_sample_rate = sample_rate
        self.requested_channels = channels
        self.blocksize = int(blocksize)
        self.buffer_seconds = float(buffer_seconds)

        self.sample_rate = 0
        self.channels = 0
        self.output_device_index = -1

        self._ring: AudioRingBuffer | None = None
        self._stream = None
        self._last_underrun_print = 0.0

    @staticmethod
    def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
        t = text.lower()
        return any(n in t for n in needles)

    def _find_input_loopback_candidate(self, output_device_index: int) -> int | None:
        devices = self._sd.query_devices()
        output_dev = self._sd.query_devices(output_device_index)
        output_name = str(output_dev.get("name", "")).lower()

        preferred_keywords = (
            "loopback",
            "stereo mix",
            "směšovač stereo",
            "what u hear",
            "wave out mix",
        )

        candidates: list[int] = []
        for idx, dev in enumerate(devices):
            if int(dev.get("max_input_channels", 0)) <= 0:
                continue
            name = str(dev.get("name", ""))
            if self._contains_any(name, preferred_keywords):
                candidates.append(idx)

        # Prefer candidates that match output-name tokens.
        if candidates:
            output_tokens = [tok for tok in output_name.replace("(", " ").replace(")", " ").split() if len(tok) >= 4]
            for idx in candidates:
                name = str(devices[idx].get("name", "")).lower()
                if any(tok in name for tok in output_tokens):
                    return idx
            return candidates[0]

        return None

    def _resolve_output_device_index(self) -> int:
        if self.device == "default":
            return resolve_default_output_device(self._sd)

        try:
            idx = int(self.device)
            dev = self._sd.query_devices(idx)
            if int(dev.get("max_output_channels", 0)) <= 0:
                raise RuntimeError(f"Device {idx} is not an output device.")
            return idx
        except ValueError:
            pass

        devices = self._sd.query_devices()
        needle = self.device.lower()
        for idx, dev in enumerate(devices):
            if int(dev.get("max_output_channels", 0)) <= 0:
                continue
            if needle in str(dev.get("name", "")).lower():
                return idx

        raise RuntimeError(f"Cannot resolve output device from '{self.device}'.")

    def start(self) -> None:
        if not hasattr(self._sd, "WasapiSettings"):
            raise RuntimeError("Current sounddevice build has no WasapiSettings support.")

        self.output_device_index = self._resolve_output_device_index()

        output_dev = self._sd.query_devices(self.output_device_index)
        output_hostapi = self._sd.query_hostapis(output_dev["hostapi"])

        def callback(indata, frames, time_info, status):
            if status:
                print(f"[WARN] Loopback callback status: {status}")
            if self._ring is not None:
                self._ring.write(np.asarray(indata, dtype=np.float32))

        wasapi_sig = inspect.signature(self._sd.WasapiSettings)
        supports_loopback_kw = "loopback" in wasapi_sig.parameters

        stream_device_index: int
        stream_dev: dict
        capture_mode: str
        extra_settings = None

        if supports_loopback_kw:
            stream_device_index = self.output_device_index
            stream_dev = output_dev
            capture_mode = "WASAPI loopback"
            extra_settings = self._sd.WasapiSettings(loopback=True)
            max_capture_channels = int(stream_dev.get("max_output_channels", 0))
        else:
            # sounddevice/PortAudio build does not expose loopback flag.
            # Try to use an input loopback-like device (e.g. Stereo Mix) as fallback path.
            alt_input_idx = self._find_input_loopback_candidate(self.output_device_index)
            if alt_input_idx is None:
                raise RuntimeError(
                    "WASAPI loopback flag is unavailable in this sounddevice build and no "
                    "input loopback candidate (e.g. Stereo Mix) was found."
                )

            stream_device_index = alt_input_idx
            stream_dev = self._sd.query_devices(stream_device_index)
            capture_mode = "Input fallback (Stereo Mix / loopback-like)"
            max_capture_channels = int(stream_dev.get("max_input_channels", 0))

        if max_capture_channels <= 0:
            raise RuntimeError("Selected capture device has zero usable channels.")

        self.sample_rate = int(
            round(self.requested_sample_rate or float(stream_dev.get("default_samplerate", 48000.0)))
        )
        self.channels = int(self.requested_channels or min(2, max_capture_channels))
        self.channels = max(1, min(self.channels, max_capture_channels))

        capacity_samples = max(1024, int(self.sample_rate * self.buffer_seconds))
        self._ring = AudioRingBuffer(capacity_samples=capacity_samples, channels=self.channels)

        self._stream = self._sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.blocksize,
            device=stream_device_index,
            channels=self.channels,
            dtype="float32",
            callback=callback,
            extra_settings=extra_settings,
        )
        self._stream.start()

        print(
            "[INFO] Loopback started | "
            f"mode='{capture_mode}' "
            f"output_device={self.output_device_index} output_name='{output_dev['name']}' output_hostapi='{output_hostapi['name']}' "
            f"capture_device={stream_device_index} capture_name='{stream_dev['name']}' "
            f"sr={self.sample_rate} channels={self.channels} ring_capacity={capacity_samples}"
        )

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None

    def get_window(self, num_samples: int) -> np.ndarray:
        if self._ring is None:
            raise RuntimeError("Loopback source is not started.")

        if self._ring.size < num_samples:
            now = time.monotonic()
            if (now - self._last_underrun_print) > 1.0:
                print(
                    f"[WARN] Audio ring underrun: available={self._ring.size} requested={num_samples}. "
                    "Padding with zeros."
                )
                self._last_underrun_print = now

        return self._ring.read_latest(num_samples)


@dataclass
class _TimedProducerState:
    start_monotonic: float = 0.0
    produced_samples: int = 0


class _TimedGeneratedSource(AudioSourceBase, ABC):
    def __init__(self, sample_rate: int, channels: int, buffer_seconds: float = 5.0) -> None:
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self._ring = AudioRingBuffer(
            capacity_samples=max(1024, int(self.sample_rate * float(buffer_seconds))),
            channels=self.channels,
        )
        self._state = _TimedProducerState()
        self._last_underrun_print = 0.0

    @abstractmethod
    def _generate(self, num_samples: int) -> np.ndarray:
        raise NotImplementedError

    def start(self) -> None:
        self._state = _TimedProducerState(start_monotonic=time.monotonic(), produced_samples=0)

    def stop(self) -> None:
        return

    def _produce_until_now(self) -> None:
        elapsed = time.monotonic() - self._state.start_monotonic
        should_have = int(elapsed * self.sample_rate)
        missing = should_have - self._state.produced_samples
        if missing <= 0:
            return

        chunk = self._generate(missing)
        self._ring.write(chunk)
        self._state.produced_samples += missing

    def get_window(self, num_samples: int) -> np.ndarray:
        self._produce_until_now()

        if self._ring.size < num_samples:
            now = time.monotonic()
            if (now - self._last_underrun_print) > 1.0:
                print(
                    f"[WARN] Generated source underrun: available={self._ring.size} requested={num_samples}. "
                    "Padding with zeros."
                )
                self._last_underrun_print = now

        return self._ring.read_latest(num_samples)


class WavSource(_TimedGeneratedSource):
    def __init__(self, wav_path: str | Path, loop: bool = True, buffer_seconds: float = 5.0) -> None:
        path = Path(wav_path)
        if not path.exists():
            raise FileNotFoundError(f"WAV file not found: {path}")

        with wave.open(str(path), "rb") as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        audio = self._decode_pcm(raw, sample_width, channels)
        if audio.size == 0:
            raise RuntimeError("WAV source contains no audio samples.")

        self._audio = audio
        self._cursor = 0
        self._loop = bool(loop)
        self.path = path

        super().__init__(sample_rate=sample_rate, channels=channels, buffer_seconds=buffer_seconds)

    @staticmethod
    def _decode_pcm(raw: bytes, sample_width: int, channels: int) -> np.ndarray:
        if sample_width == 1:
            arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            arr = (arr - 128.0) / 128.0
        elif sample_width == 2:
            arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 3:
            u8 = np.frombuffer(raw, dtype=np.uint8)
            if u8.size % 3 != 0:
                u8 = u8[: (u8.size // 3) * 3]
            b = u8.reshape(-1, 3).astype(np.int32)
            vals = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
            vals = (vals ^ 0x800000) - 0x800000
            arr = vals.astype(np.float32) / 8388608.0
        elif sample_width == 4:
            arr = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise RuntimeError(f"Unsupported WAV sample width: {sample_width} bytes")

        if channels <= 0:
            raise RuntimeError("Invalid WAV channel count")

        usable = (arr.size // channels) * channels
        arr = arr[:usable]
        return arr.reshape(-1, channels)

    def start(self) -> None:
        super().start()
        print(
            f"[INFO] WAV source started | file='{self.path}' sr={self.sample_rate} channels={self.channels}"
        )

    def _generate(self, num_samples: int) -> np.ndarray:
        num_samples = int(max(0, num_samples))
        if num_samples == 0:
            return np.zeros((0, self.channels), dtype=np.float32)

        total = self._audio.shape[0]
        if total <= 0:
            return np.zeros((num_samples, self.channels), dtype=np.float32)

        if self._loop:
            idx = (np.arange(num_samples, dtype=np.int64) + self._cursor) % total
            self._cursor = int((self._cursor + num_samples) % total)
            return self._audio[idx].astype(np.float32, copy=False)

        end = min(self._cursor + num_samples, total)
        chunk = self._audio[self._cursor:end]
        self._cursor = end

        if chunk.shape[0] < num_samples:
            pad = np.zeros((num_samples - chunk.shape[0], self.channels), dtype=np.float32)
            chunk = np.concatenate([chunk, pad], axis=0)
        return chunk.astype(np.float32, copy=False)


class SineSource(_TimedGeneratedSource):
    def __init__(
        self,
        sample_rate: int = 48000,
        frequency_hz: float = 440.0,
        channels: int = 1,
        buffer_seconds: float = 5.0,
    ) -> None:
        super().__init__(sample_rate=sample_rate, channels=channels, buffer_seconds=buffer_seconds)
        self.frequency_hz = float(frequency_hz)
        self._sample_cursor = 0

    def start(self) -> None:
        super().start()
        print(
            f"[INFO] Sine source started | sr={self.sample_rate} channels={self.channels} freq={self.frequency_hz:.2f}Hz"
        )

    def _generate(self, num_samples: int) -> np.ndarray:
        num_samples = int(max(0, num_samples))
        if num_samples == 0:
            return np.zeros((0, self.channels), dtype=np.float32)

        idx = np.arange(num_samples, dtype=np.float64) + float(self._sample_cursor)
        phase = (2.0 * np.pi * self.frequency_hz * idx) / float(self.sample_rate)
        wave_data = np.sin(phase).astype(np.float32)
        self._sample_cursor += num_samples

        if self.channels == 1:
            return wave_data[:, None]

        return np.repeat(wave_data[:, None], self.channels, axis=1)
