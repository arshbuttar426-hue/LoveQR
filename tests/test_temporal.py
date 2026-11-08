"""Temporal decoding: chip thresholding, blink words and rolling shutter."""

from __future__ import annotations

import numpy as np
import pytest

from otl.config import CameraConfig, ExperimentConfig
from otl.decoder.temporal import (
    bands_from_signal,
    bits_from_values,
    decode_rolling,
    decode_values,
    temporal_manifest,
)
from otl.errors import SyncError
from otl.protocol.blink import encode_word
from otl.rx.rolling import (
    chip_values,
    row_signal,
    simulate_rolling_shutter,
    timing_report,
)


def _values(bits: tuple[int, ...], high: float = 240.0, low: float = 15.0) -> list[float]:
    return [high if bit else low for bit in bits]


def test_bits_from_values_roundtrip() -> None:
    bits = (1, 0, 1, 1, 0, 0, 1)
    decoded, contrast = bits_from_values(_values(bits))
    assert decoded == bits
    assert contrast > 0.8


def test_bits_from_flat_sequence_rejected() -> None:
    with pytest.raises(SyncError):
        bits_from_values([128.0] * 26)


def test_decode_values_finds_each_blink_id() -> None:
    for id_index in range(3):
        result = decode_values(_values(encode_word(id_index)))
        assert result.detections, id_index
        best = max(result.detections, key=lambda d: d.id_score)
        assert best.id_index == id_index


def test_noise_tolerance_of_temporal_classifier() -> None:
    rng = np.random.default_rng(3)
    word = np.asarray(_values(encode_word(1)), dtype=np.float64)
    noisy = word + rng.normal(0.0, 12.0, size=word.shape)
    result = decode_values(noisy)
    assert result.detections
    assert max(result.detections, key=lambda d: d.id_score).id_index == 1


def test_timing_report_states_the_physical_limit() -> None:
    camera = CameraConfig()  # 60 Hz display, 27 ms readout
    report = timing_report(camera, chips=26)
    assert report["symbols_per_capture"] == pytest.approx(1.62, abs=0.01)
    assert report["word_fits_in_one_capture"] is False
    assert report["captures_needed_for_word"] > 10


def _rolling_setup() -> tuple[list[np.ndarray], CameraConfig]:
    # 1000 fps display => 1 ms per chip; 27 ms readout sees 27 chips.
    camera = CameraConfig(
        width=1080,
        height=1350,
        row_time_us=20.0,
        exposure_us=100.0,
        display_fps=1000.0,
        random_phase=False,
    )
    bits = encode_word(0)
    frames = [
        np.full((camera.height, camera.width), 255 if bit else 0, dtype=np.uint8)
        for bit in bits
    ]
    return frames, camera


def test_rolling_shutter_recovers_full_word() -> None:
    frames, camera = _rolling_setup()
    capture = simulate_rolling_shutter(frames, camera, phase_us=0.0)
    assert capture.image.shape == (camera.height, camera.width)
    assert capture.image.ndim == 2
    assert len(np.unique(capture.dominant)) >= 26
    result = decode_rolling(capture)
    assert result.detections
    assert max(result.detections, key=lambda d: d.id_score).id_index == 0


def test_rolling_chip_values_align_with_timeline() -> None:
    frames, camera = _rolling_setup()
    capture = simulate_rolling_shutter(frames, camera, phase_us=0.0)
    indices, values = chip_values(capture)
    assert indices[0] == 0
    assert values[0] > 200  # first chip of the Barker sync is 1
    manifest = temporal_manifest(capture)
    assert manifest["visible_symbols"] >= 26
    assert manifest["bands"]


def test_bands_from_signal_finds_edges() -> None:
    signal = np.concatenate(
        [np.full(40, 20.0), np.full(40, 230.0), np.full(40, 20.0)]
    )
    bands = bands_from_signal(signal)
    assert len(bands) >= 3
    means = [band.value for band in bands]
    assert max(means) > 180 and min(means) < 60


def test_row_signal_restricted_to_data_area() -> None:
    cfg = ExperimentConfig()
    image = np.zeros((cfg.screen.canvas_height, cfg.screen.canvas_width), dtype=np.uint8)
    layout = cfg.layout()
    image[:, layout.origin_x : layout.origin_x + layout.data_w] = 200
    signal = row_signal(image, layout)
    assert np.allclose(signal, 200.0)
