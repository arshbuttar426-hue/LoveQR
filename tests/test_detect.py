"""Detection and spatial decoding tests on synthetic images.

These tests exercise the decoder on prerecorded arrays; no camera is needed.
"""

from __future__ import annotations

import numpy as np
import pytest

from otl.config import ChannelConfig, ExperimentConfig
from otl.decoder.spatial import decode_cells, decode_image
from otl.errors import DetectionError
from otl.protocol.frame import pack_frame
from otl.rx.channel import apply_channel
from otl.rx.detect import (
    classify_samples,
    detect_geometry,
    find_fiducials,
    reference_levels,
    sample_cells,
)
from otl.tx.renderer import render_frame
from otl.types import FrameHeader


def _case() -> tuple[ExperimentConfig, tuple[int, ...], np.ndarray]:
    cfg = ExperimentConfig()
    cells = pack_frame(FrameHeader(2, 41), bytes(range(11)), cfg.protocol)
    image = render_frame(cells, cfg.layout(), cfg.screen)
    return cfg, cells, image


def test_clean_roundtrip() -> None:
    cfg, cells, image = _case()
    decoded = decode_image(image, cfg.layout(), cfg.receiver, cfg.protocol)
    assert decoded.crc_ok
    assert decoded.frame.header == FrameHeader(2, 41)
    assert decoded.frame.data == bytes(range(11))
    assert decoded.frame.cell_values == cells
    assert decoded.observation.confidence > 0.9


def test_fiducials_found_in_all_quadrants() -> None:
    cfg, _, image = _case()
    fiducials = find_fiducials(image, cfg.layout(), cfg.receiver)
    assert set(fiducials.centers) == {"tl", "tr", "bl", "br"}
    assert fiducials.method == "components"


def test_perspective_and_blur_roundtrip() -> None:
    cfg, cells, image = _case()
    channel = ChannelConfig(
        perspective=0.02,
        blur_sigma=1.0,
        noise_sigma=2.0,
        ambient=15.0,
        brightness=0.9,
        vignette=0.15,
        jpeg_quality=90,
    )
    captured = apply_channel(image, channel, seed=5)
    decoded = decode_image(captured, cfg.layout(), cfg.receiver, cfg.protocol)
    assert decoded.crc_ok
    assert decoded.frame.cell_values == cells


def test_all_black_and_all_white_frames_use_border_reference() -> None:
    cfg = ExperimentConfig()
    for value in (0x0, 0xF):
        cells = (value,) * 30
        image = render_frame(cells, cfg.layout(), cfg.screen)
        decoded = decode_image(image, cfg.layout(), cfg.receiver, cfg.protocol)
        assert decoded.frame.cell_values == cells
        # 0x0 and 0xF have no per-cell contrast; the border supplies it.
        assert decoded.observation.contrast > 0.5


def test_reference_levels_span_border_and_background() -> None:
    cfg, _, image = _case()
    rectified, _, _ = detect_geometry(image, cfg.layout(), cfg.receiver)
    lo, hi = reference_levels(rectified, cfg.layout())
    assert lo <= 5
    assert hi >= 250


def test_low_contrast_is_rejected_without_reference() -> None:
    samples = np.full((30, 4), 128.0)
    with pytest.raises(DetectionError):
        classify_samples(samples)


def test_solid_cells_do_not_turn_sensor_noise_into_triangles() -> None:
    """Camera noise in a solid cell is not a black/white triangle boundary.

    This reproduces the M9 physical capture: a dark cell whose four samples
    varied by ~20 grey levels was decoded as a triangle because the old rule
    used the cell's own min/max whenever that noise exceeded ``min_contrast``.
    """
    rng = np.random.default_rng(7)
    dark = 88.0 + rng.normal(0.0, 8.0, size=(30, 4))
    dark = np.clip(dark, 60.0, 140.0)
    observation = classify_samples(dark, reference=(60.0, 239.0))
    assert observation.cells == (0,) * 30

    bright = 235.0 + rng.normal(0.0, 2.0, size=(30, 4))
    observation = classify_samples(bright, reference=(60.0, 239.0))
    assert observation.cells == (0xF,) * 30

    # A real mixed cell still spans most of the frame range and keeps its
    # own threshold, so a global brightness gradient does not flip it.
    mixed = np.tile(np.array([90.0, 232.0, 88.0, 86.0]), (30, 1))
    observation = classify_samples(mixed, reference=(60.0, 239.0))
    assert observation.cells == (0b0100,) * 30


def test_blank_image_without_fiducials_is_rejected() -> None:
    cfg = ExperimentConfig()
    blank = np.full((cfg.screen.canvas_height, cfg.screen.canvas_width), 255, dtype=np.uint8)
    with pytest.raises(DetectionError):
        decode_image(blank, cfg.layout(), cfg.receiver, cfg.protocol)


def test_decode_cells_without_optics() -> None:
    cfg, cells, _ = _case()
    frame = decode_cells(cells, cfg.protocol)
    assert frame.crc_ok
    assert frame.data == bytes(range(11))
