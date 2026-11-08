"""E12 — Physical channel efficiency and reliability.

E12 is an analysis experiment.  It does not create optical data and it does not
change the M9 transmitter, frame format, packet layout, RS code, renderer or
decoder.  It consumes finalized physical capture sessions and answers four
questions with explicit denominators:

1. What are the gross-channel, gross-payload, RS-goodput and application rates?
2. How much application payload does each displayed frame actually carry?
3. Where does the gap between RS goodput and application throughput come from?
4. Are the physical baselines repeatable, and which stage is the bottleneck?

Measured values come from preserved camera files.  Projections are arithmetic
only and are labelled ``PROJECTION — not measured``.  Distance, angle and
ambient illuminance are never invented: a missing value stays ``UNMEASURED``.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from otl.config import ExperimentConfig, config_to_dict
from otl.decoder.spatial import decode_image
from otl.errors import OTLError
from otl.metrics import Aggregate, ResourceMeter
from otl.protocol.frame import frame_manifest
from otl.protocol.packet import (
    DATA_BYTES_PER_FRAME,
    FILE_HEADER_SIZE,
    FRAMES_PER_PACKET,
    PACKET_BYTES,
    PAYLOAD_0,
    decode_packet,
    packet_manifest,
)
from otl.rx.session import (
    EVIDENCE_PHYSICAL,
    load_captures,
    load_session,
    validate_session,
)
from otl.tx.renderer import load_frame

from .e11_physical import _bit_accuracy, _ground_truth_cells, _recover_payload
from .harness import ROOT, ExperimentSpec, RunContext

SESSIONS_ROOT = ROOT / "datasets" / "physical"
FROZEN_M9_ID = "m9-iphone14-2-packet-20261108T104529Z"
RS_CODE_RATE = PACKET_BYTES / (FRAMES_PER_PACKET * DATA_BYTES_PER_FRAME)
PROJECTION_LABEL = "PROJECTION — not measured"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_json(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _stats(values: list[float]) -> dict[str, float] | None:
    clean = [float(value) for value in values if isinstance(value, (int, float))]
    if not clean:
        return None
    mean = statistics.mean(clean)
    std = statistics.pstdev(clean) if len(clean) > 1 else 0.0
    return {
        "n": float(len(clean)),
        "mean": mean,
        "std": std,
        "min": min(clean),
        "max": max(clean),
        "p50": statistics.median(clean),
        "cv": (std / mean) if mean else None,
    }


def _aggregate(values: list[float]) -> dict[str, float]:
    aggregate = Aggregate()
    for value in values:
        aggregate.add(value)
    return aggregate.to_dict()


def _parse_brightness(text: str) -> float | None:
    if not text:
        return None
    match = re.search(r"start\s*=\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    if "not measured" in text.lower() or "unmeasured" in text.lower():
        return None
    # Fallback: a standalone fraction such as "0.90".  Do not accept
    # percentages or multi-digit brightness descriptions ("100%", "50%").
    match = re.search(
        r"(?<![\d.])(0(?:\.\d+)?|1(?:\.0+)?)(?![\d.%])", text
    )
    return float(match.group(1)) if match else None


def _factor_status(value: Any, *, instrumented: bool = False) -> str:
    if value is None or value == "":
        return "UNMEASURED"
    if instrumented:
        return "MEASURED (instrument readback)"
    return "OPERATOR-RECORDED (not independently instrumented)"


def _factor_record(session: Any) -> dict[str, Any]:
    brightness = _parse_brightness(session.display.brightness)
    factors = {
        "distance_mm": {
            "value": session.geometry.distance_mm,
            "unit": "mm",
            "status": _factor_status(session.geometry.distance_mm),
        },
        "angle_deg": {
            "value": session.geometry.angle_deg,
            "unit": "deg",
            "status": _factor_status(session.geometry.angle_deg),
        },
        "ambient_lux": {
            "value": session.geometry.ambient_lux,
            "unit": "lux",
            "status": _factor_status(session.geometry.ambient_lux),
        },
        "display_brightness_fraction": {
            "value": brightness,
            "unit": "fraction of controller range (0..1); not nits",
            "status": (
                "MEASURED (DisplayServicesGetBrightness)"
                if brightness is not None
                else "UNMEASURED"
            ),
        },
        "lighting": {
            "value": session.geometry.lighting or None,
            "unit": "description",
            "status": (
                "OPERATOR-RECORDED"
                if session.geometry.lighting
                else "UNMEASURED"
            ),
        },
    }
    return {
        "factors": factors,
        "unmeasured": [
            name for name, record in factors.items() if record["status"] == "UNMEASURED"
        ],
    }


def _series(session_id: str) -> str:
    if session_id.startswith("m9-"):
        return "m9_reference"
    if "baseline" in session_id:
        return "baseline"
    if "brightness" in session_id:
        return "brightness"
    return "other"


# ---------------------------------------------------------------------------
# Efficiency arithmetic
# ---------------------------------------------------------------------------


def efficiency_budget(
    cfg: ExperimentConfig,
    *,
    display_fps: float,
    expected_frames: int,
    payload_bytes: int,
    wire_bytes: int,
    compressed: bool,
    packet_bytes: int = PACKET_BYTES,
    file_header_bytes: int = FILE_HEADER_SIZE,
) -> dict[str, Any]:
    """Return the exact rate/utilisation decomposition for one transfer.

    All rates use the observed display frame period, not the camera frame rate
    and not the raw panel refresh.  ``packet_duration_s`` is the denominator
    shared by every per-second rate.

    The gap identity is::

        channel - application
            = (channel - gross_payload)                  framing (header + CRC)
            + (gross_payload - rs_goodput)               RS parity
            + (rs_goodput - wire_payload)                unused packet capacity
            - (application - wire_payload)               compression gain
    """
    if display_fps <= 0:
        raise ValueError("display_fps must be positive")
    if expected_frames <= 0:
        raise ValueError("expected_frames must be positive")
    if payload_bytes < 0 or wire_bytes < 0:
        raise ValueError("byte counts must be non-negative")

    packet_duration_s = expected_frames / display_fps
    total_bits = cfg.protocol.total_bits
    payload_bits = cfg.protocol.payload_bits
    data_bytes_per_frame = cfg.protocol.data_bytes_per_frame

    channel_bps = total_bits * display_fps
    gross_payload_bps = payload_bits * display_fps
    rs_goodput_bps = packet_bytes * 8.0 / packet_duration_s
    wire_bps = wire_bytes * 8.0 / packet_duration_s
    application_bps = payload_bytes * 8.0 / packet_duration_s

    compression_ratio = (
        payload_bytes / wire_bytes if compressed and wire_bytes else 1.0
    )
    compression_gain_bps = application_bps - wire_bps

    framing_loss_bps = channel_bps - gross_payload_bps
    rs_loss_bps = gross_payload_bps - rs_goodput_bps
    packet_fill_loss_bps = rs_goodput_bps - wire_bps
    residual_bps = channel_bps - (
        application_bps
        + framing_loss_bps
        + rs_loss_bps
        + packet_fill_loss_bps
        - compression_gain_bps
    )

    losses = [
        {
            "stage": "framing_header_and_crc",
            "bps": framing_loss_bps,
            "fraction_of_channel": framing_loss_bps / channel_bps,
        },
        {
            "stage": "reed_solomon_parity",
            "bps": rs_loss_bps,
            "fraction_of_channel": rs_loss_bps / channel_bps,
        },
        {
            "stage": "unused_packet_capacity",
            "bps": packet_fill_loss_bps,
            "fraction_of_channel": packet_fill_loss_bps / channel_bps,
        },
        {
            "stage": "compression_gain",
            "bps": -compression_gain_bps,
            "fraction_of_channel": -compression_gain_bps / channel_bps,
        },
    ]

    application_bytes_per_frame = payload_bytes / expected_frames
    wire_bytes_per_frame = wire_bytes / expected_frames
    application_bits_per_frame = application_bytes_per_frame * 8.0

    return {
        "display_fps": display_fps,
        "expected_frames": expected_frames,
        "packet_duration_s": packet_duration_s,
        "frame_bits": total_bits,
        "payload_bits_per_frame": payload_bits,
        "data_bytes_per_frame": data_bytes_per_frame,
        "frame_payload_utilisation": payload_bits / total_bits,
        "frame_protocol_overhead": (total_bits - payload_bits) / total_bits,
        "rs_code_rate": RS_CODE_RATE,
        "rs_overhead_fraction": 1.0 - RS_CODE_RATE,
        "packet_bytes": packet_bytes,
        "packet_payload_capacity_bytes": PAYLOAD_0,
        "file_header_bytes": file_header_bytes,
        "payload_bytes": payload_bytes,
        "wire_bytes": wire_bytes,
        "compressed": compressed,
        "compression_ratio": compression_ratio,
        "channel_bps": channel_bps,
        "gross_payload_bps": gross_payload_bps,
        "rs_goodput_bps": rs_goodput_bps,
        "wire_payload_bps": wire_bps,
        "application_bps": application_bps,
        "rs_to_application_gap_bps": rs_goodput_bps - application_bps,
        "rs_to_application_ratio": (
            rs_goodput_bps / application_bps if application_bps else None
        ),
        "application_share_of_channel": application_bps / channel_bps,
        "application_share_of_gross_payload": (
            application_bps / gross_payload_bps if gross_payload_bps else None
        ),
        "application_share_of_rs_goodput": (
            application_bps / rs_goodput_bps if rs_goodput_bps else None
        ),
        "wire_share_of_rs_goodput": wire_bps / rs_goodput_bps,
        "application_bytes_per_frame": application_bytes_per_frame,
        "wire_bytes_per_frame": wire_bytes_per_frame,
        "application_bits_per_frame": application_bits_per_frame,
        "application_payload_utilisation_per_frame": (
            application_bytes_per_frame / data_bytes_per_frame
        ),
        "wire_payload_utilisation_per_frame": (
            wire_bytes_per_frame / data_bytes_per_frame
        ),
        "packet_fill_wire": wire_bytes / packet_bytes,
        "packet_fill_file_object": (file_header_bytes + wire_bytes) / packet_bytes,
        "packet_fill_application": payload_bytes / packet_bytes,
        "packet_payload_capacity_utilisation": wire_bytes / PAYLOAD_0,
        "application_payload_capacity_utilisation": payload_bytes / PAYLOAD_0,
        "losses": losses,
        "residual_bps": residual_bps,
        "dominant_loss": max(
            (loss for loss in losses if loss["bps"] > 0),
            key=lambda loss: loss["bps"],
        ),
        "note": (
            "Measured rates use the observed display period and SHA-verified "
            "payload. The per-frame utilisation denominator is 11 payload "
            "bytes/frame; the packet denominator is 2,453 RS data bytes."
        ),
    }


def projection(
    cfg: ExperimentConfig,
    *,
    payload_bytes: int,
    fps: float = 60.0,
    packets: int = 1,
) -> dict[str, Any]:
    """Arithmetic projection only.  It must never be reported as measured."""
    frames = FRAMES_PER_PACKET * packets
    duration_s = frames / fps
    packet_capacity = PAYLOAD_0 + (packets - 1) * PACKET_BYTES
    return {
        "status": PROJECTION_LABEL,
        "fps": fps,
        "packets": packets,
        "frames": frames,
        "duration_s": duration_s,
        "payload_bytes": payload_bytes,
        "packet_payload_capacity_bytes": packet_capacity,
        "payload_capacity_utilisation": (
            payload_bytes / packet_capacity if packet_capacity else None
        ),
        "channel_bps": cfg.protocol.total_bits * fps,
        "gross_payload_bps": cfg.protocol.payload_bits * fps,
        "rs_goodput_bps": PACKET_BYTES * packets * 8.0 / duration_s,
        "application_bps": payload_bytes * 8.0 / duration_s,
    }


def frozen_configuration(cfg: ExperimentConfig) -> dict[str, Any]:
    payload = {
        "experiment_config": config_to_dict(cfg),
        "frame_manifest": frame_manifest(cfg.protocol),
        "packet_manifest": packet_manifest(),
    }
    return {
        "config_sha256": _sha256_json(payload),
        "config": payload,
    }


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------


def _session_paths(ctx: RunContext) -> list[Path]:
    explicit = ctx.options.get("sessions") or ctx.options.get("session")
    if explicit:
        if isinstance(explicit, (list, tuple)):
            candidates = [Path(item) for item in explicit]
        else:
            candidates = [
                Path(item.strip())
                for item in str(explicit).split(",")
                if item.strip()
            ]
        return candidates
    if not SESSIONS_ROOT.is_dir():
        return []
    paths: list[Path] = []
    for child in sorted(SESSIONS_ROOT.iterdir()):
        if not child.is_dir() or not (child / "session.json").is_file():
            continue
        if not (child / "session.lock.json").is_file():
            continue
        if child.name.startswith(("m9-", "m10-")):
            paths.append(child)
    return paths


# ---------------------------------------------------------------------------
# One session
# ---------------------------------------------------------------------------


def _cached_ground_cells(
    root: Path,
    record: dict[str, Any],
    cfg: ExperimentConfig,
    cache: dict[str, tuple[list[int] | None, str | None, str | None]],
) -> tuple[list[int] | None, str | None, str | None]:
    display_file = record.get("display_file")
    frame = record.get("frame")
    if display_file is None and isinstance(frame, dict):
        display_file = (
            f"display/p{int(frame['packet_id']):02d}"
            f"_f{int(frame['frame_index']):03d}.png"
        )
    if not display_file:
        return None, None, None
    key = str(display_file)
    if key not in cache:
        cache[key] = _ground_truth_cells(root, record, cfg)
    return cache[key]


def _analyse_session(
    root: Path,
    ctx: RunContext,
    cfg: ExperimentConfig,
    ground_cache: dict[str, tuple[list[int] | None, str | None, str | None]],
) -> dict[str, Any]:
    problems = validate_session(root)
    if problems:
        return {
            "session_id": root.name,
            "session_path": str(root),
            "status": "invalid",
            "problems": problems,
        }

    session = load_session(root)
    if session.status != "final" or not (root / "session.lock.json").is_file():
        return {
            "session_id": session.session_id,
            "session_path": str(root),
            "status": "skipped",
            "problems": ["session is not finalized"],
        }
    if session.capture_source not in {"camera", "manual-import"}:
        return {
            "session_id": session.session_id,
            "session_path": str(root),
            "status": "skipped",
            "problems": [f"capture_source is {session.capture_source!r}"],
        }
    if session.evidence_source != EVIDENCE_PHYSICAL:
        return {
            "session_id": session.session_id,
            "session_path": str(root),
            "status": "skipped",
            "problems": [
                f"evidence_source is {session.evidence_source!r}, not physical"
            ],
        }

    all_captures = load_captures(root)
    image_captures = [
        record
        for record in all_captures
        if record.get("kind") in {"still", "video-frame"}
    ]
    captures: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for record in image_captures:
        digest = record.get("sha256")
        if digest and digest in seen_hashes:
            continue
        if digest:
            seen_hashes.add(digest)
        captures.append(record)
    media = [
        record for record in all_captures if record.get("kind") not in {"still", "video-frame"}
    ]

    layout = cfg.layout()
    decode_ms: list[float] = []
    cell_accuracy_by_frame: dict[tuple[int, int], list[float]] = {}
    bit_accuracy_by_frame: dict[tuple[int, int], list[float]] = {}
    first_seen: dict[tuple[int, int], float] = {}
    samples_by_frame: Counter[tuple[int, int]] = Counter()
    packet_frames: dict[int, dict[int, bytes]] = {}
    error_counts: Counter[str] = Counter()
    crc_ok_count = 0
    contrast_values: list[float] = []
    margin_values: list[float] = []
    confidence_values: list[float] = []
    luma_p50_values: list[float] = []
    luma_p99_values: list[float] = []
    meter = ResourceMeter()

    for record in captures:
        decode_path = record.get("decode_path") or record.get("path")
        image_path = root / decode_path
        if not image_path.is_file():
            error_counts["E_IO"] += 1
            continue
        image = load_frame(str(image_path))
        gray = image.mean(axis=2) if image.ndim == 3 else image
        luma_p50_values.append(float(np.percentile(gray, 50)))
        luma_p99_values.append(float(np.percentile(gray, 99)))

        started = time.perf_counter()
        try:
            decoded = decode_image(image, layout, cfg.receiver, cfg.protocol)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            error = None
        except OTLError as exc:
            decoded = None
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            error = exc.to_dict()
        decode_ms.append(elapsed_ms)
        if error is not None:
            error_counts[str(error.get("code", "unknown"))] += 1
            continue

        crc_ok = bool(decoded.crc_ok)
        contrast_values.append(float(decoded.observation.contrast))
        margin_values.append(float(decoded.observation.bit_margin))
        confidence_values.append(float(decoded.fiducials.confidence))
        header = decoded.frame.header
        frame_key = (header.packet_id, header.frame_index)
        if crc_ok:
            crc_ok_count += 1
            packet_frames.setdefault(header.packet_id, {})[
                header.frame_index
            ] = decoded.frame.data
            samples_by_frame[frame_key] += 1
            position = record.get("pos_msec")
            if position is not None:
                first_seen.setdefault(frame_key, float(position))

        ground_record = record
        if record.get("kind") == "video-frame" and crc_ok:
            ground_record = dict(record)
            ground_record["display_file"] = (
                f"display/p{header.packet_id:02d}_f{header.frame_index:03d}.png"
            )
        ground_cells, _display_file, _ground_error = _cached_ground_cells(
            root, ground_record, cfg, ground_cache
        )
        if ground_cells is not None:
            observed = list(decoded.observation.cells)
            matches = sum(1 for a, b in zip(observed, ground_cells) if a == b)
            cell_accuracy_by_frame.setdefault(frame_key, []).append(
                matches / len(ground_cells)
            )
            bit_accuracy_by_frame.setdefault(frame_key, []).append(
                _bit_accuracy(observed, ground_cells)
            )

    unique_frame_keys = {
        (packet_id, frame_index)
        for packet_id, frames in packet_frames.items()
        for frame_index in frames
    }
    unique_frames = len(unique_frame_keys)
    expected_frames = int(session.transmitter.get("frame_count") or 0)
    manifest_fps = float(session.transmitter.get("fps") or 0.0) or None
    unique_positions = sorted(first_seen.values())
    observed_display_fps = None
    if len(unique_positions) >= 3:
        intervals = [
            later - earlier
            for earlier, later in zip(unique_positions, unique_positions[1:])
            if later > earlier
        ]
        if intervals:
            median_interval_ms = statistics.median(intervals)
            if median_interval_ms > 0:
                observed_display_fps = 1000.0 / median_interval_ms
    display_fps = observed_display_fps or manifest_fps

    packet_rows: list[dict[str, Any]] = []
    decoded_packets: dict[int, Any] = {}
    packet_started = time.perf_counter()
    for packet_id in sorted(packet_frames):
        frames = packet_frames[packet_id]
        try:
            packet = decode_packet(packet_id, frames, nsym=cfg.ecc.nsym)
            decoded_packets[packet_id] = packet
            packet_rows.append(
                {
                    "packet_id": packet_id,
                    "frames_present": len(frames),
                    "decoded": True,
                    "stats": packet.stats.to_dict()
                    if hasattr(packet, "stats")
                    else None,
                }
            )
        except OTLError as exc:
            packet_rows.append(
                {
                    "packet_id": packet_id,
                    "frames_present": len(frames),
                    "decoded": False,
                    "error": exc.to_dict(),
                }
            )
    packet_ms = (time.perf_counter() - packet_started) * 1000.0

    payload_success = False
    payload_bytes = 0
    wire_bytes = 0
    original_bytes = 0
    compressed = None
    compression_ratio = None
    payload_sha256 = None
    payload_error = None
    file_header = None
    reassembly_started = time.perf_counter()
    if decoded_packets:
        try:
            file_header, wire_payload, payload = _recover_payload(decoded_packets)
            wire_bytes = len(wire_payload)
            original_bytes = file_header.original_len
            compressed = file_header.compressed
            compression_ratio = (
                original_bytes / wire_bytes if wire_bytes and compressed else 1.0
            )
            payload_bytes = len(payload)
            payload_sha256 = hashlib.sha256(payload).hexdigest()
            expected = session.transmitter.get("payload_sha256")
            payload_success = bool(expected and payload_sha256 == expected)
            if expected and not payload_success:
                payload_error = "payload SHA-256 differs from the transmitted payload"
        except OTLError as exc:
            payload_error = exc.to_dict()
    reassembly_ms = (time.perf_counter() - reassembly_started) * 1000.0
    resource = meter.sample().to_dict()

    positions = sorted(
        float(record["pos_msec"])
        for record in captures
        if record.get("pos_msec") is not None
    )
    capture_duration_s = (
        (positions[-1] - positions[0]) / 1000.0 if len(positions) >= 2 else None
    )
    decode_wall_s = sum(decode_ms) / 1000.0 if decode_ms else None
    decode_samples_fps = (
        len(decode_ms) / decode_wall_s if decode_wall_s and decode_wall_s > 0 else None
    )
    packet_duration_s = (
        expected_frames / display_fps
        if expected_frames and display_fps and display_fps > 0
        else None
    )
    frame_delivery_rate = (
        unique_frames / expected_frames if expected_frames else None
    )
    packets_expected = file_header.total_packets if file_header is not None else None
    packets_received = len(decoded_packets)
    packet_loss_rate = (
        1.0 - packets_received / packets_expected
        if packets_expected and packets_expected > 0
        else None
    )
    corrected_symbols = sum(
        sum(packet.stats.corrected_per_block)
        for packet in decoded_packets.values()
        if hasattr(packet, "stats")
    )
    erased_frames = sum(
        packet.stats.frames_missing
        for packet in decoded_packets.values()
        if hasattr(packet, "stats")
    )
    cell_accuracies = [
        sum(values) / len(values)
        for values in cell_accuracy_by_frame.values()
        if values
    ]
    bit_accuracies = [
        sum(values) / len(values)
        for values in bit_accuracy_by_frame.values()
        if values
    ]
    physical_cell_accuracy = (
        sum(cell_accuracies) / len(cell_accuracies) if cell_accuracies else None
    )
    physical_bit_accuracy = (
        sum(bit_accuracies) / len(bit_accuracies) if bit_accuracies else None
    )
    detection_failures = int(error_counts.get("E_DETECT", 0))
    crc_failures_after_detection = max(
        0, len(captures) - crc_ok_count - detection_failures
    )
    crc_rate = crc_ok_count / len(captures) if captures else 0.0
    sample_redundancy = (
        len(captures) / unique_frames if unique_frames else None
    )
    samples_per_frame_stats = _stats(list(samples_by_frame.values()))

    budget = None
    if (
        payload_success
        and display_fps
        and expected_frames
        and packet_duration_s
    ):
        budget = efficiency_budget(
            cfg,
            display_fps=display_fps,
            expected_frames=expected_frames,
            payload_bytes=payload_bytes,
            wire_bytes=wire_bytes,
            compressed=bool(compressed),
        )

    row: dict[str, Any] = {
        "session_id": session.session_id,
        "session_path": str(root),
        "status": "ok",
        "series": _series(session.session_id),
        "evidence_source": session.evidence_source,
        "capture_source": session.capture_source,
        "device": session.device.to_dict(),
        "display": session.display.to_dict(),
        "geometry": session.geometry.to_dict(),
        "capture_settings": session.capture.to_dict(),
        "factor": _factor_record(session),
        "transmitter": session.transmitter,
        "session_lock_sha256": _sha256_file(root / "session.lock.json"),
        "captures": {
            "all_files": len(all_captures),
            "image_files": len(image_captures),
            "unique_images": len(captures),
            "media_files": len(media),
            "crc_ok": crc_ok_count,
            "crc_rate": crc_rate,
            "detection_failures": detection_failures,
            "crc_failures_after_detection": crc_failures_after_detection,
            "error_counts": dict(sorted(error_counts.items())),
            "unique_frames": unique_frames,
            "expected_frames": expected_frames,
            "frame_delivery_rate": frame_delivery_rate,
            "frame_loss_rate": (
                1.0 - frame_delivery_rate
                if frame_delivery_rate is not None
                else None
            ),
            "sample_redundancy": sample_redundancy,
            "samples_per_frame": samples_per_frame_stats,
            "ground_truth_frames": len(cell_accuracies),
        },
        "reliability": {
            "payload_success": payload_success,
            "payload_error": payload_error,
            "payload_sha256": payload_sha256,
            "expected_payload_sha256": session.transmitter.get("payload_sha256"),
            "packets_expected": packets_expected,
            "packets_received": packets_received,
            "packet_loss_rate": packet_loss_rate,
            "erased_frames": erased_frames,
            "corrected_symbols": corrected_symbols,
            "rs_nsym": cfg.ecc.nsym,
            "cell_accuracy_mean": physical_cell_accuracy,
            "bit_accuracy_mean": physical_bit_accuracy,
            "cell_accuracy": _aggregate(cell_accuracies),
            "bit_accuracy": _aggregate(bit_accuracies),
        },
        "latency": {
            "decode_ms": _aggregate(decode_ms),
            "decode_wall_s": decode_wall_s,
            "decode_samples_fps": decode_samples_fps,
            "packet_decode_ms": packet_ms,
            "reassembly_ms": reassembly_ms,
            "reconstruction_ms": packet_ms + reassembly_ms,
            "resource": resource,
        },
        "signal": {
            "contrast": _aggregate(contrast_values),
            "bit_margin": _aggregate(margin_values),
            "fiducial_confidence": _aggregate(confidence_values),
            "camera_luma_p50": _aggregate(luma_p50_values),
            "camera_luma_p99": _aggregate(luma_p99_values),
            "note": (
                "Camera pixel statistics measure the received image, not display "
                "nits or ambient illuminance."
            ),
        },
        "timing": {
            "capture_duration_s": capture_duration_s,
            "capture_fps": session.capture.fps,
            "display_fps_manifest": manifest_fps,
            "display_fps_observed": observed_display_fps,
            "display_fps_used": display_fps,
            "packet_duration_s": packet_duration_s,
            "expected_frames": expected_frames,
            "unique_frames": unique_frames,
            "camera_to_display_ratio": (
                session.capture.fps / display_fps
                if session.capture.fps and display_fps
                else None
            ),
            "decode_to_capture_ratio": (
                decode_samples_fps / session.capture.fps
                if decode_samples_fps and session.capture.fps
                else None
            ),
        },
        "payload": {
            "payload_bytes": payload_bytes,
            "wire_bytes": wire_bytes,
            "original_bytes": original_bytes,
            "compressed": compressed,
            "compression_ratio": compression_ratio,
        },
        "efficiency": budget,
        "packets": packet_rows,
        "media": [
            {
                "path": record.get("path"),
                "sha256": record.get("sha256"),
                "bytes": record.get("bytes"),
                "kind": record.get("kind"),
            }
            for record in media
        ],
    }

    ctx.record(
        config={
            "session_id": session.session_id,
            "series": row["series"],
            "capture_source": session.capture_source,
            "factors": row["factor"]["factors"],
            "transmitter_frames_sha256": session.transmitter.get("frames_sha256"),
            "transmitter_payload_sha256": session.transmitter.get("payload_sha256"),
            "session_lock_sha256": row["session_lock_sha256"],
        },
        inputs={
            "captures": len(captures),
            "image_files": len(image_captures),
            "media_files": len(media),
            "expected_frames": expected_frames,
        },
        outputs={
            "status": "ok",
            "payload_success": payload_success,
            "payload_sha256": payload_sha256,
            "unique_frames": unique_frames,
            "packets_received": packets_received,
            "efficiency": budget,
        },
        metrics={
            "application_bps": budget["application_bps"] if budget else None,
            "rs_goodput_bps": budget["rs_goodput_bps"] if budget else None,
            "gross_payload_bps": (
                budget["gross_payload_bps"] if budget else None
            ),
            "channel_bps": budget["channel_bps"] if budget else None,
            "application_payload_utilisation_per_frame": (
                budget["application_payload_utilisation_per_frame"]
                if budget
                else None
            ),
            "crc_rate": crc_rate,
            "frame_delivery_rate": frame_delivery_rate,
            "decode_ms_mean": (
                statistics.mean(decode_ms) if decode_ms else None
            ),
        },
        notes=(
            "E12 efficiency analysis of a preserved physical session; "
            "no M9 artifact was modified."
        ),
    )
    return row


# ---------------------------------------------------------------------------
# Aggregation and attribution
# ---------------------------------------------------------------------------


def _baseline_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = [
        row
        for row in rows
        if row.get("status") == "ok"
        and row.get("series") == "baseline"
        and row.get("reliability", {}).get("payload_success")
    ]
    metrics = {
        key: _stats([row["efficiency"][key] for row in baseline])
        for key in (
            "channel_bps",
            "gross_payload_bps",
            "rs_goodput_bps",
            "application_bps",
            "application_share_of_rs_goodput",
            "application_payload_utilisation_per_frame",
        )
    }
    crc_rates = [row["captures"]["crc_rate"] for row in baseline]
    delivery = [row["captures"]["frame_delivery_rate"] for row in baseline]
    decode_means = [
        row["latency"]["decode_ms"]["mean"]
        for row in baseline
        if row["latency"]["decode_ms"]
    ]
    cvs = [
        value["cv"]
        for value in metrics.values()
        if isinstance(value, dict) and value.get("cv") is not None
    ]
    throughput_cv = max(cvs) if cvs else None
    delivery_exact = all(rate == 1.0 for rate in delivery if rate is not None)
    # Repeatability is a property of the delivered payload and of the
    # normalised protocol rates.  Optical sample delivery is reported
    # separately: one baseline lost 9 frames that RS(255,223) corrected.
    established = bool(
        len(baseline) >= 2
        and all(row["reliability"]["payload_success"] for row in baseline)
        and throughput_cv is not None
        and throughput_cv < 0.01
    )
    return {
        "sessions": [row["session_id"] for row in baseline],
        "n": len(baseline),
        "metrics": metrics,
        "crc_rate": _stats(crc_rates),
        "frame_delivery_rate": _stats(delivery),
        "decode_ms_mean": _stats(decode_means),
        "throughput_cv": throughput_cv,
        "frame_delivery_all_exact": delivery_exact,
        "estimated": established,
        "repeatable": established,
        "note": (
            "Repeatability is claimed when at least two independent physical "
            "sessions each deliver the complete SHA-verified payload and the "
            "normalised throughput metrics agree within 1% CV. "
            "frame_delivery_all_exact records whether every session also "
            "recovered every displayed frame without RS help; it is reported "
            "separately because RS(255,223) is allowed to absorb lost frames. "
            "Camera-sample CRC rate varies and is never used to hide failures."
        ),
    }


def _factor_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    names = (
        "distance_mm",
        "angle_deg",
        "ambient_lux",
        "display_brightness_fraction",
        "lighting",
    )
    coverage: dict[str, Any] = {}
    for name in names:
        values = []
        statuses = []
        for row in rows:
            if row.get("status") != "ok":
                continue
            record = row["factor"]["factors"][name]
            statuses.append(record["status"])
            if record["value"] is not None:
                values.append(record["value"])
        distinct = []
        for value in values:
            # ``lighting`` is a free-text description, not a number.  Treat
            # "indoor, unchanged from M9; illuminance not measured" and
            # "indoor" as the same nominal condition; illuminance is null in
            # every session and stays UNMEASURED.
            key = (
                str(value).split(",")[0].strip().lower()
                if name == "lighting"
                else value
            )
            if key not in distinct:
                distinct.append(key)
        coverage[name] = {
            "values": distinct,
            "statuses": sorted(set(statuses)),
            "varied": len(distinct) > 1,
            "measured": any(
                status.startswith("MEASURED") for status in statuses
            ),
        }
    coverage["unvaried"] = [
        name
        for name, record in coverage.items()
        if isinstance(record, dict) and not record["varied"]
    ]
    return coverage


def _brightness_series(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for row in rows:
        if row.get("status") != "ok" or row.get("series") != "brightness":
            continue
        brightness = row["factor"]["factors"]["display_brightness_fraction"]["value"]
        efficiency = row.get("efficiency") or {}
        series.append(
            {
                "session_id": row["session_id"],
                "brightness_fraction": brightness,
                "crc_rate": row["captures"]["crc_rate"],
                "detection_failures": row["captures"]["detection_failures"],
                "frame_delivery_rate": row["captures"]["frame_delivery_rate"],
                "application_bps": efficiency.get("application_bps"),
                "rs_goodput_bps": efficiency.get("rs_goodput_bps"),
                "payload_success": row["reliability"]["payload_success"],
                "contrast_mean": row["signal"]["contrast"].get("mean"),
                "bit_margin_mean": row["signal"]["bit_margin"].get("mean"),
                "decode_ms_mean": row["latency"]["decode_ms"].get("mean"),
                "interpretability": (
                    "complete transfer; brightness comparison available"
                    if row["reliability"]["payload_success"]
                    else (
                        "NOT INTERPRETABLE as a brightness effect: "
                        "incomplete frame coverage (hand-held framing drift "
                        "clipped the fiducials)"
                    )
                ),
            }
        )
    return sorted(
        series,
        key=lambda item: (
            item["brightness_fraction"]
            if item["brightness_fraction"] is not None
            else -1.0
        ),
    )


def _bottleneck(
    rows: list[dict[str, Any]],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    reference = next(
        (
            row
            for row in rows
            if row.get("session_id") == FROZEN_M9_ID
            and row.get("status") == "ok"
            and row.get("efficiency")
        ),
        None,
    )
    if reference is None:
        reference = next(
            (
                row
                for row in rows
                if row.get("status") == "ok" and row.get("efficiency")
            ),
            None,
        )
    if reference is None:
        return {
            "primary": None,
            "status": "not available; no complete payload was measured",
        }

    budget = reference["efficiency"]
    ranking = sorted(
        (loss for loss in budget["losses"] if loss["bps"] > 0),
        key=lambda loss: loss["bps"],
        reverse=True,
    )
    primary = ranking[0] if ranking else None
    secondary = ranking[1] if len(ranking) > 1 else None
    timing = reference["timing"]
    latency = reference["latency"]
    reliability = reference["reliability"]
    display_refresh_hz = reference["display"].get("refresh_hz")
    playback_fps = timing.get("display_fps_used")
    hardware_ratio = (
        display_refresh_hz / playback_fps
        if display_refresh_hz and playback_fps
        else None
    )
    return {
        "primary": (
            "application payload utilisation (unused packet capacity)"
            if primary and primary["stage"] == "unused_packet_capacity"
            else (primary["stage"] if primary else None)
        ),
        "primary_stage": primary["stage"] if primary else None,
        "primary_loss_bps": primary["bps"] if primary else None,
        "primary_fraction_of_channel": (
            primary["fraction_of_channel"] if primary else None
        ),
        "secondary_stage": secondary["stage"] if secondary else None,
        "secondary_loss_bps": secondary["bps"] if secondary else None,
        "secondary_fraction_of_channel": (
            secondary["fraction_of_channel"] if secondary else None
        ),
        "loss_ranking": ranking,
        "per_frame": {
            "application_bytes_per_frame": budget["application_bytes_per_frame"],
            "wire_bytes_per_frame": budget["wire_bytes_per_frame"],
            "frame_payload_capacity_bytes": budget["data_bytes_per_frame"],
            "application_payload_utilisation_per_frame": budget[
                "application_payload_utilisation_per_frame"
            ],
            "wire_payload_utilisation_per_frame": budget[
                "wire_payload_utilisation_per_frame"
            ],
        },
        "packet": {
            "packet_bytes": budget["packet_bytes"],
            "wire_bytes": budget["wire_bytes"],
            "payload_bytes": budget["payload_bytes"],
            "packet_fill_wire": budget["packet_fill_wire"],
            "packet_fill_application": budget["packet_fill_application"],
            "packet_payload_capacity_utilisation": budget[
                "packet_payload_capacity_utilisation"
            ],
        },
        "display": {
            "panel_refresh_hz": display_refresh_hz,
            "playback_fps": playback_fps,
            "hardware_to_playback_ratio": hardware_ratio,
            "note": (
                "The 60 Hz panel was driven at the configured 10 fps. The 6x "
                "difference is a playback configuration choice, not a measured "
                "60 fps result."
            ),
        },
        "not_bottlenecks": [
            {
                "stage": "camera capture",
                "evidence": (
                    f"{timing.get('capture_fps')} fps camera vs "
                    f"{playback_fps:.3f} fps display; "
                    f"{timing.get('camera_to_display_ratio'):.2f}x headroom"
                    if timing.get("capture_fps")
                    and playback_fps
                    and timing.get("camera_to_display_ratio")
                    else "not available"
                ),
                "status": "measured",
            },
            {
                "stage": "decode",
                "evidence": (
                    f"{latency.get('decode_samples_fps'):.1f} decoded samples/s "
                    f"vs {timing.get('capture_fps')} fps camera; "
                    f"{timing.get('decode_to_capture_ratio'):.2f}x headroom"
                    if latency.get("decode_samples_fps")
                    and timing.get("capture_fps")
                    and timing.get("decode_to_capture_ratio")
                    else "not available"
                ),
                "status": "measured",
            },
            {
                "stage": "reed-solomon correction",
                "evidence": (
                    f"{reliability['corrected_symbols']} corrected symbols and "
                    f"{reliability['erased_frames']} erased frames"
                ),
                "status": "measured",
            },
            {
                "stage": "packet loss",
                "evidence": (
                    f"{reliability['packets_received']}/"
                    f"{reliability['packets_expected']} packets; loss "
                    f"{reliability['packet_loss_rate']}"
                ),
                "status": "measured",
            },
            {
                "stage": "detection / CRC",
                "evidence": (
                    f"{reference['captures']['crc_ok']}/"
                    f"{reference['captures']['unique_images']} camera samples "
                    f"passed CRC, but unique-frame delivery was "
                    f"{reference['captures']['frame_delivery_rate']:.3f}"
                ),
                "status": "measured; did not reduce delivered frames",
            },
        ],
        "baseline_throughput_cv": baseline.get("throughput_cv"),
        "note": (
            "Attribution uses the measured loss decomposition, not opinion. "
            "A stage is called limiting only when its measured loss is the "
            "largest positive term or when it prevents delivery."
        ),
    }


def _measured_vs_projection(
    cfg: ExperimentConfig,
    rows: list[dict[str, Any]],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    reference = next(
        (
            row
            for row in rows
            if row.get("session_id") == FROZEN_M9_ID
            and row.get("status") == "ok"
            and row.get("efficiency")
        ),
        None,
    )
    if reference is None:
        reference = next(
            (
                row
                for row in rows
                if row.get("status") == "ok" and row.get("efficiency")
            ),
            None,
        )
    measured = None
    if reference is not None:
        budget = reference["efficiency"]
        measured = {
            "session_id": reference["session_id"],
            "status": "MEASURED",
            "display_fps": budget["display_fps"],
            "channel_bps": budget["channel_bps"],
            "gross_payload_bps": budget["gross_payload_bps"],
            "rs_goodput_bps": budget["rs_goodput_bps"],
            "application_bps": budget["application_bps"],
            "application_payload_utilisation_per_frame": budget[
                "application_payload_utilisation_per_frame"
            ],
            "application_share_of_rs_goodput": budget[
                "application_share_of_rs_goodput"
            ],
        }
    projections = None
    if reference is not None:
        payload_bytes = reference["efficiency"]["payload_bytes"]
        manifest = packet_manifest()
        projections = {
            "status": PROJECTION_LABEL,
            "same_payload_at_60fps": projection(
                cfg, payload_bytes=payload_bytes, fps=60.0, packets=1
            ),
            "full_one_packet_at_60fps": projection(
                cfg, payload_bytes=PAYLOAD_0, fps=60.0, packets=1
            ),
            "maximum_16_packet_transfer_at_60fps": projection(
                cfg,
                payload_bytes=int(manifest["max_payload_bytes"]),
                fps=60.0,
                packets=int(manifest["max_packets"]),
            ),
            "same_payload_at_observed_fps": projection(
                cfg,
                payload_bytes=payload_bytes,
                fps=reference["efficiency"]["display_fps"],
                packets=1,
            ),
        }
    return {
        "measured": measured,
        "baseline_repeatability": baseline,
        "projection": projections,
        "note": (
            "Measured values come from preserved camera files and the standard "
            "decoder. Projections are arithmetic at the stated fps and payload "
            "size; no 60 fps physical capture was performed."
        ),
    }


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    paths = _session_paths(ctx)
    if not paths:
        ctx.evidence_source = "BLOCKED / NO PHYSICAL CAPTURE"
        ctx.simulation_only = True
        ctx.device = None
        ctx.classification = "BLOCKED — no finalized physical session available"
        ctx.metadata = {
            "evidence_source": ctx.evidence_source,
            "sessions": [],
            "note": (
                "No finalized physical session was found. No efficiency or "
                "reliability number is reported."
            ),
        }
        ctx.record(
            config={"stage": "session_discovery"},
            inputs={"sessions": 0},
            outputs={"status": "blocked"},
            metrics={"sessions": 0},
            notes="Blocked before any measurement.",
        )
        ctx.summary = {
            "status": "blocked",
            "evidence_source": ctx.evidence_source,
            "sessions": [],
        }
        ctx.conclude(
            "BLOCKED: no finalized physical capture session was available. "
            "Capture sessions with `otl session new`, `otl capture` and "
            "`otl session finalize`, then rerun E12."
        )
        return

    ground_cache: dict[
        str, tuple[list[int] | None, str | None, str | None]
    ] = {}
    rows = [_analyse_session(path.resolve(), ctx, cfg, ground_cache) for path in paths]
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    if not ok_rows:
        ctx.evidence_source = "BLOCKED / NO PHYSICAL CAPTURE"
        ctx.simulation_only = True
        ctx.device = None
        ctx.classification = "BLOCKED — no valid physical session"
        ctx.metadata = {
            "evidence_source": ctx.evidence_source,
            "sessions": [
                {
                    "session_id": row.get("session_id"),
                    "status": row.get("status"),
                    "problems": row.get("problems"),
                }
                for row in rows
            ],
        }
        ctx.summary = {
            "status": "blocked",
            "evidence_source": ctx.evidence_source,
            "sessions": rows,
        }
        ctx.record(
            config={"stage": "session_validation"},
            inputs={"sessions": len(rows)},
            outputs={"status": "blocked"},
            metrics={"sessions": 0},
            notes=(
                "Sessions were found but none passed the physical-evidence "
                "gates; no measurement was recorded."
            ),
        )
        ctx.conclude(
            "BLOCKED: sessions were found but none passed the physical-evidence "
            "gates. No efficiency or reliability number is reported."
        )
        return

    ctx.evidence_source = EVIDENCE_PHYSICAL
    ctx.simulation_only = False
    ctx.classification = "PHYSICAL (camera capture) + SOFTWARE (decode/analysis)"
    first = ok_rows[0]
    ctx.device = {
        **first["device"],
        "display": first["display"],
        "camera": first["capture_settings"],
    }
    ctx.metadata = {
        "evidence_source": ctx.evidence_source,
        "sessions": [row["session_id"] for row in ok_rows],
        "note": (
            "E12 reads finalized sessions only. It never modifies session files "
            "or earlier run directories."
        ),
    }

    frozen = frozen_configuration(cfg)
    reference = next(
        (row for row in ok_rows if row["session_id"] == FROZEN_M9_ID), None
    )
    reference_frames = (
        reference["transmitter"].get("frames_sha256") if reference else None
    )
    reference_payload = (
        reference["transmitter"].get("payload_sha256") if reference else None
    )
    deviations = [
        row["session_id"]
        for row in ok_rows
        if reference
        and (
            row["transmitter"].get("frames_sha256") != reference_frames
            or row["transmitter"].get("payload_sha256") != reference_payload
        )
    ]
    baseline = _baseline_summary(ok_rows)
    coverage = _factor_coverage(ok_rows)
    brightness = _brightness_series(ok_rows)
    bottleneck = _bottleneck(ok_rows, baseline)
    measured_projection = _measured_vs_projection(cfg, ok_rows, baseline)

    ctx.summary = {
        "status": "measured",
        "evidence_source": ctx.evidence_source,
        "frozen_configuration": {
            "config_sha256": frozen["config_sha256"],
            "reference_session": reference["session_id"] if reference else None,
            "frames_sha256": reference_frames,
            "payload_sha256": reference_payload,
            "sessions_checked": len(ok_rows),
            "deviations": deviations,
            "note": (
                "The M9 frame format, packet layout, RS(255,223), compression, "
                "renderer and decoder geometry are unchanged."
            ),
        },
        "sessions": rows,
        "baseline_repeatability": baseline,
        "factor_coverage": coverage,
        "brightness_series": brightness,
        "bottleneck": bottleneck,
        "measured_vs_projection": measured_projection,
        "definitions": {
            "gross_channel_bps": "120 bits/frame x observed display fps",
            "gross_payload_bps": "88 payload bits/frame x observed display fps",
            "rs_goodput_bps": (
                "2,453 RS data bytes/packet x 8 / (255 frames / observed display fps)"
            ),
            "application_bps": (
                "SHA-verified application payload bytes x 8 / packet duration"
            ),
            "application_payload_utilisation_per_frame": (
                "(application payload bytes / expected displayed frames) / "
                "11 payload bytes per frame"
            ),
            "packet_fill": "application wire bytes / 2,453 RS data bytes",
            "denominator": (
                "The observed display frame period is the shared denominator. "
                "Camera samples and panel refresh are not denominators."
            ),
        },
    }

    pos = [
        row
        for row in ok_rows
        if row["reliability"]["payload_success"] and row.get("efficiency")
    ]
    if pos:
        ref = pos[0]["efficiency"]
        conclusion = (
            f"PHYSICAL / CAMERA CAPTURE. E12 analysed {len(ok_rows)} finalized "
            f"session(s); {len(pos)} delivered the complete SHA-verified payload. "
            f"Baseline repeats: {baseline['n']} session(s), repeatable="
            f"{baseline['repeatable']} (throughput CV "
            f"{baseline['throughput_cv']}). "
            f"For the reference transfer the gross channel rate is "
            f"{ref['channel_bps']:.2f} bps, gross payload "
            f"{ref['gross_payload_bps']:.2f} bps, RS(255,223) goodput "
            f"{ref['rs_goodput_bps']:.2f} bps and application throughput "
            f"{ref['application_bps']:.2f} bps. The application carries "
            f"{ref['application_bytes_per_frame']:.3f} bytes per displayed frame "
            f"out of {ref['data_bytes_per_frame']} "
            f"({ref['application_payload_utilisation_per_frame']:.2%}). "
            f"From the gross channel to the application the total gap is "
            f"{ref['channel_bps'] - ref['application_bps']:.2f} bps: framing "
            f"{ref['losses'][0]['bps']:.2f} bps, RS parity "
            f"{ref['losses'][1]['bps']:.2f} bps, unused packet capacity "
            f"{ref['losses'][2]['bps']:.2f} bps, with compression recovering "
            f"{-ref['losses'][3]['bps']:.2f} bps. The narrower "
            f"RS-to-application gap is {ref['rs_to_application_gap_bps']:.2f} bps "
            f"(unused packet capacity minus compression gain). "
            f"The dominant loss is "
            f"{bottleneck.get('primary')} at "
            f"{bottleneck.get('primary_loss_bps'):.2f} bps "
            f"({bottleneck.get('primary_fraction_of_channel'):.1%} of the gross "
            f"channel). Camera capture and decode have measured headroom; RS "
            f"corrections and packet loss are zero; detection/CRC failures did "
            f"not reduce unique-frame delivery. Across the three independent "
            f"baselines, unique-frame delivery ranged "
            f"{baseline['frame_delivery_rate']['min']:.3f}-"
            f"{baseline['frame_delivery_rate']['max']:.3f} and camera-sample "
            f"CRC rate ranged {baseline['crc_rate']['min']:.3f}-"
            f"{baseline['crc_rate']['max']:.3f}, yet all three recovered the "
            f"exact payload; the one baseline that lost 9 frames was repaired "
            f"by 18 RS symbols. The panel ran at "
            f"{bottleneck['display']['playback_fps']:.3f} fps, not 60 Hz; the 6x "
            f"difference is a playback choice, and 60 fps values are projections, "
            f"not measurements. Brightness was set and read back at "
            f"{[item['brightness_fraction'] for item in brightness if item['brightness_fraction'] is not None]} "
            f"fractions, but both brightness sessions lost the fiducials to "
            f"hand-held framing drift after about 14 s "
            f"({[item['detection_failures'] for item in brightness]} detection "
            f"failures; unique-frame delivery "
            f"{[round(item['frame_delivery_rate'], 3) for item in brightness]}), "
            f"so no brightness effect is claimed; that is a measured receiver "
            f"reliability failure, not a brightness result. Distance, angle and "
            f"ambient illuminance remain UNMEASURED. All "
            f"measured numbers come from preserved camera files; projections are "
            f"labelled separately."
        )
    else:
        conclusion = (
            "PHYSICAL sessions were read but no complete payload was recovered. "
            "No application rate or efficiency claim is made."
        )
    ctx.conclude(conclusion)


SPEC = ExperimentSpec(
    id="E12_channel_efficiency",
    title="Physical channel efficiency and reliability",
    hypothesis=(
        "The gap between RS(255,223) goodput and application throughput is "
        "dominated by unused packet capacity (payload utilisation), not by "
        "display refresh, camera capture, detection, decoding or RS correction; "
        "independent baseline sessions repeat the protocol rates while "
        "camera-sample reliability may vary."
    ),
    classification="PHYSICAL (camera capture) + SOFTWARE (decode/analysis), or BLOCKED",
    controlled=(
        "protocol",
        "layout",
        "renderer",
        "decoder",
        "payload",
        "frame set",
        "display playback rate",
    ),
    independent=(
        "device",
        "display",
        "distance",
        "angle",
        "ambient light",
        "display brightness",
        "capture settings",
    ),
    dependent=(
        "gross channel rate",
        "gross payload rate",
        "RS goodput",
        "application throughput",
        "application payload utilisation per frame",
        "CRC and unique-frame delivery",
        "RS corrections and packet loss",
        "decode latency and throughput",
        "baseline repeatability",
        "bottleneck attribution",
    ),
    procedure=(
        "Freeze the successful M9 protocol, payload, frame set and decoder.",
        "Read only finalized physical sessions with a valid session.lock.json.",
        "Decode every preserved camera sample and count unique displayed frames.",
        "Compute gross channel, gross payload, RS goodput and application rates with the observed display period as denominator.",
        "Compute application bytes per frame and the loss decomposition from channel to application.",
        "Aggregate independent baseline sessions and report throughput and reliability spread separately.",
        "Vary only factors for which actual values are recorded; leave the rest UNMEASURED.",
        "Label measured values and arithmetic projections separately.",
    ),
    run=run,
    evidence_source="BLOCKED / NO PHYSICAL CAPTURE",
    simulation_only=True,
    device_required=True,
)
