"""End-to-end pipeline tests.

Every assertion is about the software/simulated channel.  No physical camera
is involved, so results are OBSERVED + SIMULATED, never VERIFIED.
"""

from __future__ import annotations

import os

import pytest

from otl.config import ChannelConfig, CompressionConfig, ExperimentConfig
from otl.pipeline import pipeline_manifest, simulate_transfer


def _cfg(**kwargs) -> ExperimentConfig:
    return ExperimentConfig(**kwargs)


def test_clean_transfer_roundtrip() -> None:
    data = b"The quick brown fox jumps over the lazy dog. " * 20
    result = simulate_transfer(data, "clean.txt", apply_optics=False)
    assert result.success
    assert result.original == data
    assert result.frames_total == 255
    assert result.frames_crc_ok == result.frames_decoded == 255
    assert result.ber == 0.0
    assert result.errors == []
    assert result.throughput.net_bps > 0


def test_channel_transfer_roundtrip() -> None:
    data = b"degraded channel payload " * 30
    channel = ChannelConfig(
        blur_sigma=1.0,
        noise_sigma=3.0,
        ambient=18.0,
        brightness=0.88,
        gamma=1.1,
        vignette=0.2,
        perspective=0.02,
        jpeg_quality=88,
    )
    result = simulate_transfer(data, "channel.txt", _cfg(channel=channel))
    assert result.success
    assert result.original == data
    assert result.ber == 0.0


def test_frame_loss_within_rs_capacity() -> None:
    data = b"loss tolerance " * 40
    result = simulate_transfer(data, "loss.txt", drop_probability=0.04, seed=11)
    assert result.success
    assert 0 < result.frames_dropped <= 32
    assert result.per_packet[0]["frames_missing"] == result.frames_dropped


def test_excess_frame_loss_fails_loudly() -> None:
    result = simulate_transfer(b"too much loss", "fail.txt", drop_probability=0.5, seed=2)
    assert not result.success
    assert result.original is None
    stages = {error["stage"] for error in result.errors}
    assert "packet" in stages and "reassembly" in stages
    packet_error = next(e for e in result.errors if e["stage"] == "packet")
    assert packet_error["code"] == "E_RECONSTRUCT"


def test_multi_packet_transfer() -> None:
    data = os.urandom(6000)
    cfg = _cfg(compression=CompressionConfig(enabled=False))
    result = simulate_transfer(data, "multi.bin", cfg, apply_optics=False)
    assert result.success
    assert result.original == data
    assert result.throughput.packets == 3
    assert result.frames_total == 3 * 255


def test_same_seed_reproduces_drop_pattern() -> None:
    data = b"deterministic loss " * 30
    a = simulate_transfer(data, "seed.txt", drop_probability=0.05, seed=99)
    b = simulate_transfer(data, "seed.txt", drop_probability=0.05, seed=99)
    assert a.frames_dropped == b.frames_dropped
    assert a.per_packet[0]["erasures"] == b.per_packet[0]["erasures"]
    assert a.success and b.success


def test_pipeline_manifest() -> None:
    manifest = pipeline_manifest()
    assert manifest["simulation"] is True
    assert "spatial_decode" in manifest["stages"]  # type: ignore[operator]
