"""Synthetic channel tests: determinism and monotonic degradations."""

from __future__ import annotations

import numpy as np
import pytest

from otl.config import ChannelConfig, ExperimentConfig
from otl.errors import ChannelError
from otl.rx.channel import Capture, apply_channel, channel_manifest, load_capture
from otl.tx.renderer import render_frame


def _frame() -> np.ndarray:
    cfg = ExperimentConfig()
    return render_frame(list(range(16)) + [7] * 14, cfg.layout(), cfg.screen)


def test_default_channel_is_identity() -> None:
    image = _frame()
    assert np.array_equal(apply_channel(image), image)


def test_channel_is_seeded_and_deterministic() -> None:
    image = _frame()
    cfg = ChannelConfig(noise_sigma=5.0, blur_sigma=1.0, jpeg_quality=85)
    a = apply_channel(image, cfg, seed=123)
    b = apply_channel(image, cfg, seed=123)
    c = apply_channel(image, cfg, seed=124)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_brightness_and_ambient_shift_levels() -> None:
    image = _frame()
    dark = apply_channel(image, ChannelConfig(brightness=0.5))
    bright = apply_channel(image, ChannelConfig(brightness=1.2))
    assert dark.max() <= 128
    assert bright.max() >= 255  # clipped
    ambient = apply_channel(image, ChannelConfig(ambient=40.0))
    assert ambient.min() >= 39


def test_vignette_darkens_corners() -> None:
    image = np.full((400, 400), 255, dtype=np.uint8)
    out = apply_channel(image, ChannelConfig(vignette=0.5))
    corner = float(out[:50, :50].mean())
    center = float(out[175:225, 175:225].mean())
    assert corner < center


def test_perspective_preserves_shape() -> None:
    image = _frame()
    out = apply_channel(image, ChannelConfig(perspective=0.05))
    assert out.shape == image.shape
    assert out.dtype == np.uint8


def test_grayscale_required() -> None:
    with pytest.raises(ChannelError):
        apply_channel(np.zeros((10, 10, 3), dtype=np.uint8))


def test_load_capture_and_manifest(tmp_path) -> None:
    path = tmp_path / "capture.png"
    from PIL import Image

    Image.fromarray(_frame(), mode="L").save(path)
    capture = load_capture(str(path), device="test-device")
    assert isinstance(capture, Capture)
    assert capture.source == "physical"
    assert capture.device == "test-device"
    assert capture.image.dtype == np.uint8
    manifest = channel_manifest()
    assert manifest["simulation"] is True
    assert "perspective" in str(manifest["model"])
