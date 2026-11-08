"""Renderer tests: geometry, determinism, inversion and validation."""

from __future__ import annotations

import numpy as np
import pytest

from otl.codec.patterns import pattern_colors
from otl.config import ExperimentConfig
from otl.errors import ProtocolError
from otl.tx.renderer import (
    FrameRenderer,
    render_blink_frames,
    render_frame,
    render_inverted,
    renderer_for,
)


def test_render_shape_and_levels() -> None:
    cfg = ExperimentConfig()
    image = render_frame([0] * 30, cfg.layout(), cfg.screen)
    assert image.shape == (cfg.screen.canvas_height, cfg.screen.canvas_width)
    assert image.dtype == np.uint8
    # Cell 0 is all black; the background, gaps and most fiducials are white.
    assert image.min() == 0 and image.max() == 255


def test_render_is_deterministic() -> None:
    cfg = ExperimentConfig()
    cells = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15] + [7] * 14
    a = render_frame(cells, cfg.layout(), cfg.screen)
    b = render_frame(cells, cfg.layout(), cfg.screen)
    assert np.array_equal(a, b)


def test_renderer_cache_returns_same_object() -> None:
    cfg = ExperimentConfig()
    assert renderer_for(cfg.layout(), cfg.screen) is renderer_for(cfg.layout(), cfg.screen)
    assert isinstance(renderer_for(cfg.layout(), cfg.screen), FrameRenderer)


def test_inversion_is_exact_complement() -> None:
    cfg = ExperimentConfig()
    cells = [15] * 30
    normal = render_frame(cells, cfg.layout(), cfg.screen)
    inverted = render_inverted(cells, cfg.layout(), cfg.screen)
    assert np.array_equal(inverted, 255 - normal)


def test_blink_frames_use_bits() -> None:
    cfg = ExperimentConfig()
    cells = [3] * 30
    frames = render_blink_frames(cells, [1, 0, 1], cfg.layout(), cfg.screen)
    assert len(frames) == 3
    assert np.array_equal(frames[0], frames[2])
    assert np.array_equal(frames[1], 255 - frames[0])


def test_tile_matches_pattern_alphabet() -> None:
    cfg = ExperimentConfig()
    renderer = renderer_for(cfg.layout(), cfg.screen)
    for value in range(16):
        image = renderer.render([value] * 30)
        # Count dark fraction inside one cell; every pattern has 0..4 dark triangles.
        rect = cfg.layout().cell_rect(0, 0)
        patch = image[rect.y : rect.y + rect.h, rect.x : rect.x + rect.w]
        dark = float((patch < 128).mean())
        expected = (4 - sum(pattern_colors(value))) / 4.0
        assert abs(dark - expected) < 0.08, (value, dark, expected)


def test_wrong_cell_count_rejected() -> None:
    cfg = ExperimentConfig()
    with pytest.raises(ProtocolError):
        render_frame([0] * 29, cfg.layout(), cfg.screen)
    with pytest.raises(ProtocolError):
        render_frame([0] * 29 + [16], cfg.layout(), cfg.screen)
