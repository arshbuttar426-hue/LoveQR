"""Measurement primitive tests."""

from __future__ import annotations

import time

import pytest

from otl.errors import MeasurementError
from otl.metrics import (
    Aggregate,
    ResourceMeter,
    Throughput,
    Timer,
    bit_error_rate,
    byte_error_rate,
    frame_error_rate,
    resource_sample,
)


def test_bit_error_rate() -> None:
    assert bit_error_rate(b"\x00", b"\x00") == 0.0
    assert bit_error_rate(b"\x00", b"\xff") == 1.0
    assert bit_error_rate(b"\x00\x00", b"\x01\x00") == 1 / 16
    assert bit_error_rate(b"", b"") == 0.0
    with pytest.raises(MeasurementError):
        bit_error_rate(b"a", b"ab")


def test_byte_and_frame_error_rates() -> None:
    assert byte_error_rate(b"abcd", b"abce") == 0.25
    assert frame_error_rate([(1, 2), (3, 4)], [(1, 2), (3, 5)]) == 0.5
    with pytest.raises(MeasurementError):
        byte_error_rate(b"a", b"ab")


def test_throughput_arithmetic() -> None:
    t = Throughput(
        payload_bytes=1000,
        original_bytes=2000,
        duration_s=2.0,
        frames=100,
        packets=2,
        lost_frames=10,
    )
    assert t.gross_bps == 4000.0
    assert t.net_bps == 8000.0
    assert t.fps == 50.0
    assert t.frame_loss_rate == pytest.approx(10 / 110)
    data = t.to_dict()
    assert data["gross_kib_s"] == pytest.approx(4000.0 / 8192.0)
    assert data["lost_packets"] == 0


def test_zero_duration_is_safe() -> None:
    t = Throughput(payload_bytes=1, original_bytes=1, duration_s=0.0)
    assert t.gross_bps == 0.0 and t.fps == 0.0


def test_timer_measures_elapsed() -> None:
    with Timer() as timer:
        time.sleep(0.01)
    assert timer.elapsed_s >= 0.005


def test_aggregate_statistics() -> None:
    agg = Aggregate()
    for value in (1.0, 2.0, 3.0, 4.0):
        agg.add(value)
    assert agg.n == 4
    assert agg.mean == 2.5
    assert agg.minimum == 1.0 and agg.maximum == 4.0
    assert agg.percentile(50) == pytest.approx(2.5)
    assert agg.to_dict()["p95"] >= agg.to_dict()["p50"]
    assert Aggregate().to_dict()["mean"] == 0.0


def test_resource_sample_fields() -> None:
    sample = resource_sample(0.5)
    data = sample.to_dict()
    assert data["wall_s"] == 0.5
    assert data["max_rss_kb"] > 0
    # Normalised to KiB: a process RSS above 16 GiB would indicate the raw
    # macOS byte count leaked through.
    assert data["max_rss_kb"] < 16 * 1024 * 1024
    assert data["rss_kb"] > 0
    assert data["cpu_percent"] >= 0.0


def test_resource_meter_measures_an_interval_not_process_lifetime() -> None:
    meter = ResourceMeter()
    # Burn a little CPU inside the interval; the delta must be small even if
    # earlier tests already used seconds of process CPU.
    deadline = time.perf_counter() + 0.05
    while time.perf_counter() < deadline:
        pass
    sample = meter.sample()
    assert sample.wall_s >= 0.04
    assert 0.0 <= sample.cpu_s < 5.0
    assert sample.cpu_percent < 500.0
    assert sample.max_rss_kb >= sample.rss_kb > 0
