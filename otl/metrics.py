"""Measurement primitives.

All values produced here are measurements of *software* or a *simulated*
channel.  They must be reported with :class:`otl.types.MeasurementSource` and
never labelled ``VERIFIED`` unless a physical capture exists.
"""

from __future__ import annotations

import os
import resource
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .errors import MeasurementError


class Timer:
    """Wall-clock timer using a monotonic clock."""

    def __init__(self) -> None:
        self._start = 0.0
        self._end: float | None = None

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        self._end = None
        return self

    def __exit__(self, *exc: object) -> None:
        self._end = time.perf_counter()

    @property
    def elapsed_s(self) -> float:
        end = time.perf_counter() if self._end is None else self._end
        return end - self._start


def _cpu_seconds() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


def _peak_rss_kb() -> int:
    """Process lifetime peak RSS, normalised to KiB.

    ``ru_maxrss`` is kilobytes on Linux but bytes on macOS/BSD.
    """
    rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        rss //= 1024
    return rss


def _current_rss_kb() -> int:
    """Current resident set size in KiB, without an extra dependency."""
    try:
        with open("/proc/self/statm", encoding="ascii") as handle:
            pages = int(handle.read().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE") // 1024
    except (OSError, IndexError, ValueError):
        pass
    try:
        result = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(os.getpid())],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        value = result.stdout.strip()
        if value:
            return int(value)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return _peak_rss_kb()


@dataclass(frozen=True)
class ResourceSample:
    wall_s: float
    cpu_s: float
    max_rss_kb: int
    rss_kb: int = 0

    @property
    def cpu_percent(self) -> float:
        return 100.0 * self.cpu_s / self.wall_s if self.wall_s > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "wall_s": self.wall_s,
            "cpu_s": self.cpu_s,
            "cpu_percent": self.cpu_percent,
            "max_rss_kb": self.max_rss_kb,
            "rss_kb": self.rss_kb,
        }


class ResourceMeter:
    """Measure CPU and memory for one interval, not process lifetime.

    ``resource.getrusage`` returns CPU time accumulated since process start.
    Experiments run in one process, so a lifetime sample would attribute every
    earlier experiment's CPU to the current one.  A meter stores a baseline and
    reports the difference, while also tracking the highest RSS it observes.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._cpu0 = _cpu_seconds()
        self._wall0 = time.perf_counter()
        self._peak_rss = _current_rss_kb()

    def sample(self) -> ResourceSample:
        wall_s = time.perf_counter() - self._wall0
        rss = _current_rss_kb()
        self._peak_rss = max(self._peak_rss, rss)
        return ResourceSample(
            wall_s=wall_s,
            cpu_s=max(0.0, _cpu_seconds() - self._cpu0),
            max_rss_kb=self._peak_rss,
            rss_kb=rss,
        )


def resource_sample(wall_s: float, *, baseline_cpu_s: float = 0.0) -> ResourceSample:
    """One-shot sample; ``baseline_cpu_s`` subtracts earlier CPU time."""
    rss = _current_rss_kb()
    return ResourceSample(
        wall_s=wall_s,
        cpu_s=max(0.0, _cpu_seconds() - baseline_cpu_s),
        max_rss_kb=rss,
        rss_kb=rss,
    )


def bit_error_rate(expected: bytes, actual: bytes) -> float:
    """Fraction of differing bits; lengths must match."""
    if len(expected) != len(actual):
        raise MeasurementError(
            "BER requires equal-length byte strings",
            component="metrics",
            operation="bit_error_rate",
            expected=len(expected),
            actual=len(actual),
        )
    if not expected:
        return 0.0
    errors = 0
    for a, b in zip(expected, actual):
        errors += int(a ^ b).bit_count()
    return errors / (8.0 * len(expected))


def byte_error_rate(expected: bytes, actual: bytes) -> float:
    if len(expected) != len(actual):
        raise MeasurementError(
            "byte error rate requires equal-length byte strings",
            component="metrics",
            operation="byte_error_rate",
        )
    if not expected:
        return 0.0
    return sum(1 for a, b in zip(expected, actual) if a != b) / len(expected)


def frame_error_rate(expected: list[tuple[int, ...]], actual: list[tuple[int, ...]]) -> float:
    if len(expected) != len(actual):
        raise MeasurementError(
            "frame error rate requires equal-length sequences",
            component="metrics",
            operation="frame_error_rate",
        )
    if not expected:
        return 0.0
    return sum(1 for a, b in zip(expected, actual) if a != b) / len(expected)


@dataclass(frozen=True)
class Throughput:
    payload_bytes: int
    original_bytes: int
    duration_s: float
    frames: int = 0
    packets: int = 0
    lost_frames: int = 0
    lost_packets: int = 0
    corrected_frames: int = 0

    @property
    def gross_bps(self) -> float:
        return 8.0 * self.payload_bytes / self.duration_s if self.duration_s > 0 else 0.0

    @property
    def net_bps(self) -> float:
        return 8.0 * self.original_bytes / self.duration_s if self.duration_s > 0 else 0.0

    @property
    def fps(self) -> float:
        return self.frames / self.duration_s if self.duration_s > 0 else 0.0

    @property
    def frame_loss_rate(self) -> float:
        total = self.frames + self.lost_frames
        return self.lost_frames / total if total else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload_bytes": self.payload_bytes,
            "original_bytes": self.original_bytes,
            "duration_s": self.duration_s,
            "gross_bps": self.gross_bps,
            "net_bps": self.net_bps,
            "gross_kib_s": self.gross_bps / 8192.0,
            "net_kib_s": self.net_bps / 8192.0,
            "frames": self.frames,
            "packets": self.packets,
            "fps": self.fps,
            "lost_frames": self.lost_frames,
            "lost_packets": self.lost_packets,
            "frame_loss_rate": self.frame_loss_rate,
            "corrected_frames": self.corrected_frames,
        }


@dataclass
class Aggregate:
    values: list[float] = field(default_factory=list)

    def add(self, value: float) -> None:
        self.values.append(float(value))

    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def mean(self) -> float:
        return float(np.mean(self.values)) if self.values else 0.0

    @property
    def std(self) -> float:
        return float(np.std(self.values)) if self.values else 0.0

    @property
    def minimum(self) -> float:
        return float(np.min(self.values)) if self.values else 0.0

    @property
    def maximum(self) -> float:
        return float(np.max(self.values)) if self.values else 0.0

    def percentile(self, q: float) -> float:
        return float(np.percentile(self.values, q)) if self.values else 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "n": float(self.n),
            "mean": self.mean,
            "std": self.std,
            "min": self.minimum,
            "max": self.maximum,
            "p50": self.percentile(50),
            "p95": self.percentile(95),
        }
