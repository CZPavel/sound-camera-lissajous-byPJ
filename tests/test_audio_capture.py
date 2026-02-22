from __future__ import annotations

import numpy as np

from audio_capture import AudioRingBuffer


def test_ring_buffer_basic_write_read() -> None:
    rb = AudioRingBuffer(capacity_samples=8, channels=1)
    rb.write(np.array([1.0, 2.0, 3.0], dtype=np.float32))

    out = rb.read_latest(3)
    assert out.shape == (3, 1)
    assert np.allclose(out[:, 0], [1.0, 2.0, 3.0])


def test_ring_buffer_overflow_keeps_latest_samples() -> None:
    rb = AudioRingBuffer(capacity_samples=5, channels=1)
    rb.write(np.arange(1, 9, dtype=np.float32))  # 1..8

    out = rb.read_latest(5)
    assert out.shape == (5, 1)
    assert np.allclose(out[:, 0], [4.0, 5.0, 6.0, 7.0, 8.0])


def test_ring_buffer_zero_padding_when_not_enough_data() -> None:
    rb = AudioRingBuffer(capacity_samples=10, channels=1)
    rb.write(np.array([10.0, 20.0], dtype=np.float32))

    out = rb.read_latest(5)
    assert out.shape == (5, 1)
    assert np.allclose(out[:, 0], [0.0, 0.0, 0.0, 10.0, 20.0])


def test_ring_buffer_channel_adaptation_pad_and_trim() -> None:
    rb = AudioRingBuffer(capacity_samples=8, channels=2)

    rb.write(np.array([1.0, 2.0], dtype=np.float32))  # mono -> pad to 2ch
    out = rb.read_latest(2)
    assert np.allclose(out, [[1.0, 0.0], [2.0, 0.0]])

    rb.write(np.array([[5.0, 6.0, 7.0]], dtype=np.float32))  # 3ch -> trim to 2ch
    out = rb.read_latest(1)
    assert np.allclose(out, [[5.0, 6.0]])
