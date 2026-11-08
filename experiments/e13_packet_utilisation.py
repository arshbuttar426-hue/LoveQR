"""E13 — M11 packet-utilisation optimisation.

E13 answers six questions with measured denominators:

1. Why is the frozen transfer only 11.99% packet-fill?
2. Can several logical payloads share one packet?
3. Can packet headers shrink without losing reliability?
4. Can the shared OTL1 instruction dictionary replace repeated data?
5. Should compression be adaptive rather than always applied?
6. Can RS parity be adjusted to the measured channel?

The experiment has two halves.  The **software** half builds every M11 arm,
decodes it through the real packet/RS/container code and verifies SHA-256.  The
**physical** half consumes locked ``m11-*`` camera sessions and reports the
observed display rate, net application throughput, packet fill, erasures and
corrections.  Nothing physical is invented: when no M11 session exists the
report says so and keeps the software numbers separate.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from otl.compress.dictionary import decompress
from otl.config import ExperimentConfig
from otl.decoder.spatial import decode_image
from otl.errors import OTLError
from otl.metrics import Aggregate, ResourceMeter
from otl.protocol.m11 import (
    COMPACT_HEADER_SIZE,
    M11_HEADER_KIND,
    M9_HEADER_KIND,
    decode_packet_v2,
    max_payload_bytes,
    packet_data_bytes,
    reassemble_v2,
    unpack_bundle,
)
from otl.protocol.packet import (
    FRAMES_PER_PACKET,
    PACKET_BYTES,
    PAYLOAD_0,
    decode_packet,
    reassemble,
)
from otl.rx.session import (
    EVIDENCE_PHYSICAL,
    load_captures,
    load_session,
    validate_session,
)
from otl.tx.renderer import load_frame

from .e12_channel_efficiency import (
    _aggregate,
    _cached_ground_cells,
    _factor_record,
    _sha256_file,
    _stats,
)
from .harness import ROOT, ExperimentSpec, RunContext
from .m11_payloads import ARM_IDS, ArmBuild, all_arms, build_arm

SESSIONS_ROOT = ROOT / "datasets" / "physical"
RESULTS_INDEX = ROOT / "results" / "index.json"
REFERENCE_SESSION_ID = "m9-iphone14-2-packet-20261108T104529Z"
REFERENCE_APPLICATION_BPS = 99.44103628852598
REFERENCE_PACKET_FILL_WIRE = 0.11985324092947411
REFERENCE_APPLICATION_BYTES_PER_FRAME = 317 / 255
REFERENCE_FRAME_BITS = 120
REFERENCE_PAYLOAD_BITS = 88
PROJECTION_LABEL = "PROJECTION — not measured"
M11_HEADER_KINDS = {M9_HEADER_KIND, M11_HEADER_KIND}


# ---------------------------------------------------------------------------
# Exact accounting
# ---------------------------------------------------------------------------


def utilisation_budget(
    *,
    display_fps: float,
    expected_frames: int,
    application_bytes: int,
    wire_bytes: int,
    compressed: bool,
    nsym: int,
    header_bytes: int,
    total_packets: int,
    packet_data_bytes: int,
) -> dict[str, Any]:
    """Return the exact rate/utilisation decomposition for one M11 transfer.

    Unlike E12 this version exposes the file header separately from packet
    padding, because M11 changes the header size.  The identity is::

        channel - application
            = framing (frame header + CRC)
            + RS parity
            + file header
            + unused packet padding
            + encoding overhead (wire - application)

    ``encoding overhead`` is negative when OTL1 compresses (a gain) and
    positive when a bundle or an always-on compressor adds bytes.
    """
    if display_fps <= 0:
        raise ValueError("display_fps must be positive")
    if expected_frames <= 0:
        raise ValueError("expected_frames must be positive")
    if application_bytes < 0 or wire_bytes < 0:
        raise ValueError("byte counts must be non-negative")
    if total_packets <= 0:
        raise ValueError("total_packets must be positive")
    data_region = total_packets * packet_data_bytes
    if header_bytes + wire_bytes > data_region:
        raise ValueError("header and wire payload exceed the packet data region")

    duration_s = expected_frames / display_fps
    channel_bps = REFERENCE_FRAME_BITS * display_fps
    gross_payload_bps = REFERENCE_PAYLOAD_BITS * display_fps
    rs_goodput_bps = data_region * 8.0 / duration_s
    wire_payload_bps = wire_bytes * 8.0 / duration_s
    application_bps = application_bytes * 8.0 / duration_s

    framing_bps = channel_bps - gross_payload_bps
    rs_parity_bps = gross_payload_bps - rs_goodput_bps
    header_bps = header_bytes * 8.0 / duration_s
    padding_bytes = data_region - header_bytes - wire_bytes
    padding_bps = padding_bytes * 8.0 / duration_s
    encoding_overhead_bytes = wire_bytes - application_bytes
    encoding_overhead_bps = encoding_overhead_bytes * 8.0 / duration_s
    residual_bps = channel_bps - (
        application_bps
        + framing_bps
        + rs_parity_bps
        + header_bps
        + padding_bps
        + encoding_overhead_bps
    )

    losses = [
        {
            "stage": "framing_header_and_crc",
            "bps": framing_bps,
            "fraction_of_channel": framing_bps / channel_bps,
        },
        {
            "stage": "reed_solomon_parity",
            "bps": rs_parity_bps,
            "fraction_of_channel": rs_parity_bps / channel_bps,
        },
        {
            "stage": "file_header",
            "bps": header_bps,
            "fraction_of_channel": header_bps / channel_bps,
        },
        {
            "stage": "unused_packet_padding",
            "bps": padding_bps,
            "fraction_of_channel": padding_bps / channel_bps,
        },
        {
            "stage": "encoding_overhead",
            "bps": encoding_overhead_bps,
            "fraction_of_channel": encoding_overhead_bps / channel_bps,
        },
    ]

    return {
        "display_fps": display_fps,
        "expected_frames": expected_frames,
        "packet_duration_s": duration_s,
        "total_packets": total_packets,
        "packet_data_bytes": packet_data_bytes,
        "data_region_bytes": data_region,
        "rs_nsym": nsym,
        "rs_code_rate": (255 - nsym) / 255.0,
        "file_header_bytes": header_bytes,
        "application_bytes": application_bytes,
        "wire_bytes": wire_bytes,
        "compressed": compressed,
        "channel_bps": channel_bps,
        "gross_payload_bps": gross_payload_bps,
        "rs_goodput_bps": rs_goodput_bps,
        "wire_payload_bps": wire_payload_bps,
        "application_bps": application_bps,
        "framing_bps": framing_bps,
        "rs_parity_bps": rs_parity_bps,
        "file_header_bps": header_bps,
        "padding_bps": padding_bps,
        "encoding_overhead_bytes": encoding_overhead_bytes,
        "encoding_overhead_bps": encoding_overhead_bps,
        "compression_gain_bps": -encoding_overhead_bps,
        "compression_ratio": (
            application_bytes / wire_bytes if compressed and wire_bytes else 1.0
        ),
        "packet_fill_payload": wire_bytes / data_region,
        "packet_fill_incl_header": (header_bytes + wire_bytes) / data_region,
        "packet_fill_application": application_bytes / data_region,
        "application_bytes_per_frame": application_bytes / expected_frames,
        "wire_bytes_per_frame": wire_bytes / expected_frames,
        "application_payload_utilisation_per_frame": (
            application_bytes / expected_frames / 11.0
        ),
        "wire_payload_utilisation_per_frame": (
            wire_bytes / expected_frames / 11.0
        ),
        "application_share_of_channel": application_bps / channel_bps,
        "application_share_of_rs_goodput": application_bps / rs_goodput_bps,
        "application_share_of_gross_payload": application_bps / gross_payload_bps,
        "rs_to_application_gap_bps": rs_goodput_bps - application_bps,
        "losses": losses,
        "residual_bps": residual_bps,
        "dominant_loss": max(
            (loss for loss in losses if loss["bps"] > 0),
            key=lambda loss: loss["bps"],
        ),
        "note": (
            "Rates use the observed display period. Packet data capacity is "
            "11*(255-nsym) bytes per packet. The identity closes to "
            "floating-point rounding; residual_bps is reported explicitly."
        ),
    }


# ---------------------------------------------------------------------------
# Arm encoding/decoding helpers
# ---------------------------------------------------------------------------


def _decode_arm_frames(
    frames: dict[int, dict[int, bytes]],
    *,
    header_kind: str,
    nsym: int,
) -> dict[int, Any]:
    decoded: dict[int, Any] = {}
    for packet_id in sorted(frames):
        if header_kind == M9_HEADER_KIND:
            decoded[packet_id] = decode_packet(
                packet_id, frames[packet_id], nsym=nsym
            )
        elif header_kind == M11_HEADER_KIND:
            decoded[packet_id] = decode_packet_v2(
                packet_id, frames[packet_id], nsym=nsym
            )
        else:
            raise ValueError(f"unknown header kind {header_kind!r}")
    return decoded


def _recover_arm(
    decoded: dict[int, Any],
    *,
    header_kind: str,
) -> tuple[Any, bytes, bytes]:
    if header_kind == M9_HEADER_KIND:
        header, wire = reassemble(decoded)
    else:
        header, wire = reassemble_v2(decoded)
    raw = decompress(wire) if header.compressed else wire
    return header, wire, raw


def _verify_arm(
    arm_meta: dict[str, Any],
    *,
    header: Any,
    wire: bytes,
    raw: bytes,
) -> dict[str, Any]:
    wire_sha = hashlib.sha256(wire).hexdigest()
    expected_wire = arm_meta.get("wire_sha256")
    wire_ok = wire_sha == expected_wire
    header_ok = (
        int(header.original_len) == int(arm_meta["original_len"])
        and int(header.payload_len) == len(wire)
    )
    bundle_ok = None
    entries: list[dict[str, Any]] = []
    if arm_meta.get("bundle"):
        try:
            unpacked = unpack_bundle(raw)
        except OTLError as exc:
            return {
                "payload_success": False,
                "wire_sha256": wire_sha,
                "wire_sha256_matches": wire_ok,
                "header_matches": header_ok,
                "bundle": {"status": "failed", "error": exc.to_dict()},
                "entries": [],
            }
        expected_entries = arm_meta["bundle"]["entries"]
        by_name = {entry.name: entry for entry in unpacked}
        bundle_ok = len(unpacked) == len(expected_entries)
        for expected in expected_entries:
            entry = by_name.get(expected["name"])
            actual_sha = (
                hashlib.sha256(entry.data).hexdigest() if entry is not None else None
            )
            ok = (
                entry is not None
                and len(entry.data) == expected["bytes"]
                and actual_sha == expected["sha256"]
            )
            bundle_ok = bundle_ok and ok
            entries.append(
                {
                    "name": expected["name"],
                    "expected_bytes": expected["bytes"],
                    "actual_bytes": len(entry.data) if entry else None,
                    "expected_sha256": expected["sha256"],
                    "actual_sha256": actual_sha,
                    "ok": ok,
                }
            )
        payload_success = bool(wire_ok and header_ok and bundle_ok)
        return {
            "payload_success": payload_success,
            "wire_sha256": wire_sha,
            "wire_sha256_matches": wire_ok,
            "header_matches": header_ok,
            "bundle_ok": bundle_ok,
            "entries": entries,
        }
    application_sha = hashlib.sha256(raw).hexdigest()
    payload_success = bool(
        wire_ok
        and header_ok
        and application_sha == arm_meta.get("application_sha256")
    )
    return {
        "payload_success": payload_success,
        "wire_sha256": wire_sha,
        "wire_sha256_matches": wire_ok,
        "header_matches": header_ok,
        "application_sha256": application_sha,
        "application_sha256_matches": application_sha
        == arm_meta.get("application_sha256"),
        "entries": entries,
    }


# ---------------------------------------------------------------------------
# Software arm validation
# ---------------------------------------------------------------------------


def validate_arm_software(ctx: RunContext, arm: ArmBuild, *, fps: float = 10.0) -> dict[str, Any]:
    frames: dict[int, dict[int, bytes]] = {}
    for header, data in arm.frames:
        frames.setdefault(header.packet_id, {})[header.frame_index] = data

    started = time.perf_counter()
    decoded = _decode_arm_frames(
        frames, header_kind=arm.header_kind, nsym=arm.nsym
    )
    decode_ms = (time.perf_counter() - started) * 1000.0
    header, wire, raw = _recover_arm(decoded, header_kind=arm.header_kind)
    verification = _verify_arm(
        arm.to_dict(), header=header, wire=wire, raw=raw
    )
    budget = utilisation_budget(
        display_fps=fps,
        expected_frames=arm.frame_count,
        application_bytes=arm.application_bytes,
        wire_bytes=len(wire),
        compressed=arm.compressed,
        nsym=arm.nsym,
        header_bytes=arm.header_size,
        total_packets=arm.total_packets,
        packet_data_bytes=arm.packet_data_bytes,
    )
    row = {
        "arm_id": arm.arm_id,
        "title": arm.title,
        "description": arm.description,
        "status": "ok" if verification["payload_success"] else "failed",
        "header_kind": arm.header_kind,
        "header_bytes": arm.header_size,
        "nsym": arm.nsym,
        "compressed": arm.compressed,
        "total_packets": arm.total_packets,
        "frame_count": arm.frame_count,
        "application_bytes": arm.application_bytes,
        "wire_bytes": len(wire),
        "application_sha256": arm.application_sha256,
        "wire_sha256": arm.wire_sha256,
        "verification": verification,
        "decode_ms": decode_ms,
        "budget": budget,
        "bundle": arm.to_dict().get("bundle"),
    }
    ctx.record(
        config={
            "arm_id": arm.arm_id,
            "nsym": arm.nsym,
            "header_kind": arm.header_kind,
            "compressed": arm.compressed,
            "total_packets": arm.total_packets,
        },
        inputs={
            "application_bytes": arm.application_bytes,
            "wire_bytes": len(wire),
            "frame_count": arm.frame_count,
        },
        outputs={
            "status": row["status"],
            "payload_success": verification["payload_success"],
            "wire_sha256_matches": verification["wire_sha256_matches"],
            "bundle_ok": verification.get("bundle_ok"),
            "application_sha256_matches": verification.get(
                "application_sha256_matches"
            ),
        },
        metrics={
            "application_bps_at_10fps": budget["application_bps"],
            "packet_fill_payload": budget["packet_fill_payload"],
            "packet_fill_incl_header": budget["packet_fill_incl_header"],
            "application_bytes_per_frame": budget["application_bytes_per_frame"],
            "residual_bps": budget["residual_bps"],
            "decode_ms": decode_ms,
        },
        notes="E13 software validation through the real packet codec; no camera data.",
    )
    return row


# ---------------------------------------------------------------------------
# Physical session discovery and analysis
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
        if child.name.startswith("m11-"):
            paths.append(child)
    return paths


def _m11_metadata(session: Any) -> dict[str, Any] | None:
    metadata = session.transmitter.get("m11")
    if isinstance(metadata, dict):
        return metadata
    return None


def _analyse_physical_session(
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
    arm_meta = _m11_metadata(session)
    if arm_meta is None:
        return {
            "session_id": session.session_id,
            "session_path": str(root),
            "status": "skipped",
            "problems": ["transmitter.m11 metadata is missing"],
        }
    if arm_meta.get("header_kind") not in M11_HEADER_KINDS:
        return {
            "session_id": session.session_id,
            "session_path": str(root),
            "status": "skipped",
            "problems": [
                f"unknown header_kind {arm_meta.get('header_kind')!r}"
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
        record
        for record in all_captures
        if record.get("kind") not in {"still", "video-frame"}
    ]

    layout = cfg.layout()
    decode_ms: list[float] = []
    first_seen: dict[tuple[int, int], float] = {}
    packet_frames: dict[int, dict[int, bytes]] = {}
    error_counts: dict[str, int] = {}
    crc_ok_count = 0
    meter = ResourceMeter()
    contrast_values: list[float] = []
    margin_values: list[float] = []
    confidence_values: list[float] = []
    cell_accuracy_by_frame: dict[tuple[int, int], list[float]] = {}

    for record in captures:
        decode_path = record.get("decode_path") or record.get("path")
        image_path = root / decode_path
        if not image_path.is_file():
            error_counts["E_IO"] = error_counts.get("E_IO", 0) + 1
            continue
        image = load_frame(str(image_path))
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
            code = str(error.get("code", "unknown"))
            error_counts[code] = error_counts.get(code, 0) + 1
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

    unique_frame_keys = {
        (packet_id, frame_index)
        for packet_id, frames in packet_frames.items()
        for frame_index in frames
    }
    unique_frames = len(unique_frame_keys)
    expected_frames = int(arm_meta.get("frame_count") or 0)
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
            if arm_meta["header_kind"] == M9_HEADER_KIND:
                packet = decode_packet(
                    packet_id, frames, nsym=int(arm_meta["nsym"])
                )
            else:
                packet = decode_packet_v2(
                    packet_id, frames, nsym=int(arm_meta["nsym"])
                )
            decoded_packets[packet_id] = packet
            packet_rows.append(
                {
                    "packet_id": packet_id,
                    "frames_present": len(frames),
                    "decoded": True,
                    "stats": packet.stats.to_dict(),
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
    payload_error = None
    verification: dict[str, Any] = {}
    header = None
    wire = b""
    raw = b""
    reassembly_started = time.perf_counter()
    if decoded_packets:
        try:
            header, wire, raw = _recover_arm(
                decoded_packets, header_kind=arm_meta["header_kind"]
            )
            verification = _verify_arm(
                arm_meta, header=header, wire=wire, raw=raw
            )
            payload_success = bool(verification["payload_success"])
            if not payload_success:
                payload_error = "recovered payload does not match the arm manifest"
        except OTLError as exc:
            payload_error = exc.to_dict()
    reassembly_ms = (time.perf_counter() - reassembly_started) * 1000.0
    resource = meter.sample().to_dict()

    packet_duration_s = (
        expected_frames / display_fps
        if expected_frames and display_fps and display_fps > 0
        else None
    )
    frame_delivery_rate = (
        unique_frames / expected_frames if expected_frames else None
    )
    packets_expected = int(arm_meta.get("total_packets") or 0) or None
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

    budget = None
    if payload_success and display_fps and expected_frames:
        budget = utilisation_budget(
            display_fps=display_fps,
            expected_frames=expected_frames,
            application_bytes=int(arm_meta["application_bytes"]),
            wire_bytes=len(wire),
            compressed=bool(arm_meta.get("compressed")),
            nsym=int(arm_meta["nsym"]),
            header_bytes=int(arm_meta["header_bytes"]),
            total_packets=int(arm_meta["total_packets"]),
            packet_data_bytes=int(arm_meta["packet_data_bytes"]),
        )

    row: dict[str, Any] = {
        "session_id": session.session_id,
        "session_path": str(root),
        "status": "ok" if payload_success else "failed",
        "arm_id": arm_meta.get("arm_id"),
        "title": arm_meta.get("title"),
        "evidence_source": session.evidence_source,
        "capture_source": session.capture_source,
        "device": session.device.to_dict(),
        "display": session.display.to_dict(),
        "geometry": session.geometry.to_dict(),
        "capture_settings": session.capture.to_dict(),
        "factor": _factor_record(session),
        "transmitter": session.transmitter,
        "session_lock_sha256": _sha256_file(root / "session.lock.json"),
        "arm": arm_meta,
        "captures": {
            "all_files": len(all_captures),
            "image_files": len(image_captures),
            "unique_images": len(captures),
            "media_files": len(media),
            "crc_ok": crc_ok_count,
            "crc_rate": crc_ok_count / len(captures) if captures else 0.0,
            "error_counts": dict(sorted(error_counts.items())),
            "unique_frames": unique_frames,
            "expected_frames": expected_frames,
            "frame_delivery_rate": frame_delivery_rate,
            "ground_truth_frames": len(cell_accuracies),
        },
        "reliability": {
            "payload_success": payload_success,
            "payload_error": payload_error,
            "verification": verification,
            "packets_expected": packets_expected,
            "packets_received": packets_received,
            "packet_loss_rate": packet_loss_rate,
            "erased_frames": erased_frames,
            "corrected_symbols": corrected_symbols,
            "rs_nsym": int(arm_meta["nsym"]),
            "rs_erasure_margin": int(arm_meta["nsym"]) - erased_frames,
            "cell_accuracy_mean": (
                sum(cell_accuracies) / len(cell_accuracies)
                if cell_accuracies
                else None
            ),
            "cell_accuracy": _aggregate(cell_accuracies),
        },
        "latency": {
            "decode_ms": _aggregate(decode_ms),
            "packet_decode_ms": packet_ms,
            "reassembly_ms": reassembly_ms,
            "reconstruction_ms": packet_ms + reassembly_ms,
            "resource": resource,
        },
        "signal": {
            "contrast": _aggregate(contrast_values),
            "bit_margin": _aggregate(margin_values),
            "fiducial_confidence": _aggregate(confidence_values),
        },
        "timing": {
            "display_fps_manifest": manifest_fps,
            "display_fps_observed": observed_display_fps,
            "display_fps_used": display_fps,
            "packet_duration_s": packet_duration_s,
            "expected_frames": expected_frames,
            "unique_frames": unique_frames,
        },
        "payload": {
            "application_bytes": int(arm_meta["application_bytes"]),
            "wire_bytes": len(wire),
            "compressed": bool(arm_meta.get("compressed")),
            "wire_sha256": hashlib.sha256(wire).hexdigest() if wire else None,
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
            "arm_id": arm_meta.get("arm_id"),
            "nsym": int(arm_meta["nsym"]),
            "header_kind": arm_meta["header_kind"],
            "session_lock_sha256": row["session_lock_sha256"],
        },
        inputs={
            "captures": len(captures),
            "expected_frames": expected_frames,
            "application_bytes": int(arm_meta["application_bytes"]),
        },
        outputs={
            "status": row["status"],
            "payload_success": payload_success,
            "unique_frames": unique_frames,
            "packets_received": packets_received,
            "efficiency": budget,
        },
        metrics={
            "application_bps": budget["application_bps"] if budget else None,
            "packet_fill_payload": (
                budget["packet_fill_payload"] if budget else None
            ),
            "frame_delivery_rate": frame_delivery_rate,
            "erased_frames": erased_frames,
            "corrected_symbols": corrected_symbols,
        },
        notes="E13 physical analysis of a locked M11 session; no session file was modified.",
    )
    return row


# ---------------------------------------------------------------------------
# Reference and comparisons
# ---------------------------------------------------------------------------


def _latest_e12_reference() -> dict[str, Any] | None:
    if not RESULTS_INDEX.is_file():
        return None
    try:
        index = json.loads(RESULTS_INDEX.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    entry = index.get("experiments", {}).get("E12_channel_efficiency")
    if not entry:
        return None
    report = entry.get("report")
    if not report:
        return None
    summary_path = Path(report).parent / "processed" / "summary.json"
    if not summary_path.is_file():
        return None
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    for row in summary.get("summary", {}).get("sessions", []):
        if row.get("session_id") == REFERENCE_SESSION_ID:
            return row.get("efficiency")
    return None


def _reference_block() -> dict[str, Any]:
    efficiency = _latest_e12_reference()
    if efficiency:
        return {
            "source": "E12 reference session",
            "session_id": REFERENCE_SESSION_ID,
            "application_bps": efficiency["application_bps"],
            "packet_fill_wire": efficiency["packet_fill_wire"],
            "application_bytes_per_frame": efficiency[
                "application_bytes_per_frame"
            ],
            "display_fps": efficiency["display_fps"],
            "verified": True,
        }
    return {
        "source": "frozen M10 documented baseline",
        "session_id": REFERENCE_SESSION_ID,
        "application_bps": REFERENCE_APPLICATION_BPS,
        "packet_fill_wire": REFERENCE_PACKET_FILL_WIRE,
        "application_bytes_per_frame": REFERENCE_APPLICATION_BYTES_PER_FRAME,
        "display_fps": 9.999,
        "verified": False,
    }


def _capacity_table() -> list[dict[str, Any]]:
    rows = []
    for nsym in (16, 24, 32):
        data = packet_data_bytes(nsym)
        rows.append(
            {
                "nsym": nsym,
                "block_data_bytes": 255 - nsym,
                "packet_data_bytes": data,
                "packet0_compact": data - COMPACT_HEADER_SIZE,
                "packet0_m9": data - 32,
                "max_payload_compact": max_payload_bytes(
                    nsym=nsym, header_size=COMPACT_HEADER_SIZE
                ),
                "correctable_erasures": nsym,
                "correctable_errors": nsym // 2,
                "capacity_vs_nsym32": data / packet_data_bytes(32) - 1.0,
            }
        )
    return rows


def _comparison(name: str, left: dict[str, Any], right: dict[str, Any], *, note: str) -> dict[str, Any]:
    left_bps = left.get("application_bps")
    right_bps = right.get("application_bps")
    ratio = left_bps / right_bps if left_bps and right_bps else None
    return {
        "name": name,
        "left": left.get("arm_id") or left.get("session_id"),
        "right": right.get("arm_id") or right.get("session_id"),
        "left_application_bps": left_bps,
        "right_application_bps": right_bps,
        "application_ratio": ratio,
        "left_packet_fill": left.get("packet_fill_payload"),
        "right_packet_fill": right.get("packet_fill_payload"),
        "note": note,
    }


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    software_rows = [
        validate_arm_software(ctx, build_arm(arm_id)) for arm_id in ARM_IDS
    ]
    software_by_id = {row["arm_id"]: row for row in software_rows}

    ground_cache: dict[str, tuple[list[int] | None, str | None, str | None]] = {}
    physical_rows = [
        _analyse_physical_session(path, ctx, cfg, ground_cache)
        for path in _session_paths(ctx)
    ]
    physical_ok = [row for row in physical_rows if row.get("status") == "ok"]
    reference = _reference_block()

    software_summary = []
    for row in software_rows:
        budget = row["budget"]
        software_summary.append(
            {
                "arm_id": row["arm_id"],
                "title": row["title"],
                "status": row["status"],
                "nsym": row["nsym"],
                "header_kind": row["header_kind"],
                "header_bytes": row["header_bytes"],
                "compressed": row["compressed"],
                "total_packets": row["total_packets"],
                "frames": row["frame_count"],
                "application_bytes": row["application_bytes"],
                "wire_bytes": row["wire_bytes"],
                "application_sha256": row["application_sha256"],
                "payload_success": row["verification"]["payload_success"],
                "bundle_ok": row["verification"].get("bundle_ok"),
                "application_bps_at_10fps": budget["application_bps"],
                "packet_fill_payload": budget["packet_fill_payload"],
                "packet_fill_incl_header": budget["packet_fill_incl_header"],
                "application_bytes_per_frame": budget[
                    "application_bytes_per_frame"
                ],
                "residual_bps": budget["residual_bps"],
                "dominant_loss": budget["dominant_loss"]["stage"],
            }
        )

    physical_summary = []
    for row in physical_rows:
        if row.get("status") != "ok":
            physical_summary.append(
                {
                    "session_id": row.get("session_id"),
                    "arm_id": row.get("arm_id"),
                    "status": row.get("status"),
                    "problems": row.get("problems"),
                    "reason": (
                        row.get("problems")
                        or (
                            "payload verification failed"
                            if row.get("reliability")
                            else "session not analysable"
                        )
                    ),
                    "payload_success": (
                        row.get("reliability", {}).get("payload_success")
                    ),
                    "unique_frames": row.get("captures", {}).get("unique_frames"),
                    "expected_frames": row.get("captures", {}).get(
                        "expected_frames"
                    ),
                }
            )
            continue
        budget = row["efficiency"]
        physical_summary.append(
            {
                "session_id": row["session_id"],
                "arm_id": row["arm_id"],
                "status": row["status"],
                "display_fps": row["timing"]["display_fps_used"],
                "frames": row["captures"]["expected_frames"],
                "unique_frames": row["captures"]["unique_frames"],
                "frame_delivery_rate": row["captures"]["frame_delivery_rate"],
                "payload_success": row["reliability"]["payload_success"],
                "erased_frames": row["reliability"]["erased_frames"],
                "corrected_symbols": row["reliability"]["corrected_symbols"],
                "rs_nsym": row["reliability"]["rs_nsym"],
                "rs_erasure_margin": row["reliability"]["rs_erasure_margin"],
                "application_bps": budget["application_bps"],
                "wire_payload_bps": budget["wire_payload_bps"],
                "packet_fill_payload": budget["packet_fill_payload"],
                "packet_fill_incl_header": budget["packet_fill_incl_header"],
                "application_bytes_per_frame": budget[
                    "application_bytes_per_frame"
                ],
                "application_share_of_channel": budget[
                    "application_share_of_channel"
                ],
                "residual_bps": budget["residual_bps"],
                "dominant_loss": budget["dominant_loss"]["stage"],
            }
        )

    comparisons: list[dict[str, Any]] = []
    if "A0_reference" in software_by_id:
        reference_soft = software_by_id["A0_reference"]["budget"]
        for arm_id in ("A1_fill_adaptive", "A2_bundle", "A3_dictionary"):
            budget = software_by_id[arm_id]["budget"]
            note = "Software-encoded exact comparison at the same 10 fps."
            if arm_id == "A3_dictionary":
                note = (
                    "Software-encoded comparison. The A3 application rate counts "
                    "pre-compression bytes; its wire payload rate is much lower."
                )
            comparisons.append(
                _comparison(
                    f"{arm_id}_vs_A0",
                    {"arm_id": arm_id, **budget},
                    {"arm_id": "A0_reference", **reference_soft},
                    note=note,
                )
            )
    if "A4_always_on" in software_by_id and "A1_fill_adaptive" in software_by_id:
        comparisons.append(
            _comparison(
                "A1_adaptive_vs_A4_always_on",
                {
                    "arm_id": "A1_fill_adaptive",
                    **software_by_id["A1_fill_adaptive"]["budget"],
                },
                {
                    "arm_id": "A4_always_on",
                    **software_by_id["A4_always_on"]["budget"],
                },
                note=(
                    "Same 2,421-byte payload. A4 always-on compression grows "
                    "the wire payload to 2,450 bytes and needs two packets."
                ),
            )
        )
    if "A5_rs24" in software_by_id and "A1_fill_adaptive" in software_by_id:
        comparisons.append(
            _comparison(
                "A5_rs24_vs_A1_rs32",
                {
                    "arm_id": "A5_rs24",
                    **software_by_id["A5_rs24"]["budget"],
                },
                {
                    "arm_id": "A1_fill_adaptive",
                    **software_by_id["A1_fill_adaptive"]["budget"],
                },
                note=(
                    "A5 carries 105 more payload bytes in the same 255 frames "
                    "(88 from RS parity, 17 from the compact header)."
                ),
            )
        )

    # A bundle is compared with the original one-file-per-packet model: four
    # 570-byte payloads would each occupy a 255-frame packet.
    if "A2_bundle" in software_by_id:
        bundle = software_by_id["A2_bundle"]
        four_packets_bps = (
            bundle["application_bytes"] * 8.0 / (4 * FRAMES_PER_PACKET / 10.0)
        )
        comparisons.append(
            {
                "name": "A2_bundle_vs_four_separate_packets",
                "left": "A2_bundle",
                "right": "four separate 255-frame packets",
                "left_application_bps": bundle["budget"]["application_bps"],
                "right_application_bps": four_packets_bps,
                "application_ratio": bundle["budget"]["application_bps"]
                / four_packets_bps,
                "note": (
                    "The original model sends one logical payload per packet. "
                    "A bundle amortises one 255-frame packet across four files."
                ),
            }
        )

    # Physical rows take precedence for the same arm when available.
    physical_by_arm = {
        row["arm_id"]: row for row in physical_ok if row.get("arm_id")
    }
    physical_comparisons = []
    for arm_id, row in physical_by_arm.items():
        budget = row["efficiency"]
        physical_comparisons.append(
            {
                "name": f"{arm_id}_vs_reference",
                "arm_id": arm_id,
                "session_id": row["session_id"],
                "application_bps": budget["application_bps"],
                "reference_application_bps": reference["application_bps"],
                "application_ratio": budget["application_bps"]
                / reference["application_bps"]
                if reference["application_bps"]
                else None,
                "packet_fill_payload": budget["packet_fill_payload"],
                "reference_packet_fill_wire": reference["packet_fill_wire"],
                "erased_frames": row["reliability"]["erased_frames"],
                "corrected_symbols": row["reliability"]["corrected_symbols"],
                "rs_nsym": row["reliability"]["rs_nsym"],
            }
        )
    if "A1_fill_adaptive" in physical_by_arm and "A4_always_on" in physical_by_arm:
        left = physical_by_arm["A1_fill_adaptive"]["efficiency"]
        right = physical_by_arm["A4_always_on"]["efficiency"]
        physical_comparisons.append(
            {
                "name": "A1_adaptive_vs_A4_always_on_physical",
                "application_ratio": left["application_bps"]
                / right["application_bps"],
                "left_application_bps": left["application_bps"],
                "right_application_bps": right["application_bps"],
                "note": "Same payload, measured in two physical sessions.",
            }
        )
    if "A5_rs24" in physical_by_arm and "A1_fill_adaptive" in physical_by_arm:
        left = physical_by_arm["A5_rs24"]["efficiency"]
        right = physical_by_arm["A1_fill_adaptive"]["efficiency"]
        physical_comparisons.append(
            {
                "name": "A5_rs24_vs_A1_rs32_physical",
                "application_ratio": left["application_bps"]
                / right["application_bps"],
                "left_application_bps": left["application_bps"],
                "right_application_bps": right["application_bps"],
                "note": "Same 255 frames; A5 uses the larger RS(255,231) data region.",
            }
        )

    baseline_fill = reference["packet_fill_wire"]
    root_cause = {
        "frozen_packet_data_bytes": PACKET_BYTES,
        "frozen_packet0_payload_capacity": PAYLOAD_0,
        "frozen_wire_bytes": 294,
        "frozen_application_bytes": 317,
        "frozen_wire_packet_fill": baseline_fill,
        "frozen_application_packet_fill": 317 / PACKET_BYTES,
        "frozen_application_bytes_per_frame": reference[
            "application_bytes_per_frame"
        ],
        "frame_payload_bytes": 11,
        "explanation": (
            "The packet is always 255 frames x 11 bytes = 2,453 RS data "
            "bytes. The frozen payload is only 317 application bytes (294 "
            "wire bytes after OTL1), so 2,159 of the 2,453 data bytes are "
            "zero padding. 11.99% is unused capacity, not loss: the packet "
            "is shorter than its container, and the padding is still "
            "RS-encoded and transmitted."
        ),
    }

    reliability = {
        "reference_worst_erased_frames": 9,
        "reference_nsym": 32,
        "capacity_table": _capacity_table(),
        "physical": [
            {
                "session_id": row["session_id"],
                "arm_id": row["arm_id"],
                "payload_success": row["reliability"]["payload_success"],
                "erased_frames": row["reliability"]["erased_frames"],
                "corrected_symbols": row["reliability"]["corrected_symbols"],
                "rs_nsym": row["reliability"]["rs_nsym"],
                "rs_erasure_margin": row["reliability"]["rs_erasure_margin"],
                "packets_received": row["reliability"]["packets_received"],
                "packets_expected": row["reliability"]["packets_expected"],
            }
            for row in physical_ok
        ],
        "note": (
            "nsym is the number of correctable erasures per RS block. The "
            "frozen M10 baseline needed at most 9 erasures, so nsym=24 keeps "
            "15 erasures of measured headroom and nsym=16 keeps 7. Reliability "
            "is only claimed for arms whose payload SHA-256 matched."
        ),
    }

    measured = bool(physical_ok)
    if measured:
        first = physical_ok[0]
        ctx.simulation_only = False
        ctx.evidence_source = EVIDENCE_PHYSICAL
        ctx.classification = (
            "PHYSICAL (camera capture) + SOFTWARE (packet/RS validation)"
        )
        ctx.device = {
            **first["device"],
            "display": first["display"],
            "camera": first["capture_settings"],
        }
        ctx.metadata = {
            "evidence_source": ctx.evidence_source,
            "sessions": [row["session_id"] for row in physical_ok],
            "failed_sessions": [
                row["session_id"]
                for row in physical_summary
                if row.get("status") != "ok"
            ],
            "note": (
                "E13 analyses locked m11-* sessions read-only and never edits "
                "a session or earlier run. Software arms without a locked "
                "physical session remain software observations."
            ),
        }
    else:
        ctx.classification = "SOFTWARE (packet/RS validation)"
    summary = {
        "status": (
            "MEASURED PHYSICAL M11 SESSIONS"
            if measured
            else "SOFTWARE VALIDATION ONLY — no locked m11-* sessions"
        ),
        "evidence_source": (
            EVIDENCE_PHYSICAL
            if measured
            else "SIMULATED / SOFTWARE (no M11 physical capture)"
        ),
        "reference": reference,
        "root_cause": root_cause,
        "software_arms": software_summary,
        "physical_sessions": physical_summary,
        "comparisons_software": comparisons,
        "comparisons_physical": physical_comparisons,
        "reliability": reliability,
        "measured_vs_projection": {
            "measured": [
                "software packet/RS/container round-trips and SHA-256 matches",
                "physical application throughput and packet fill for locked m11-* sessions",
                "physical erasures, corrections and packet success",
            ],
            "projection_label": PROJECTION_LABEL,
            "projections": [
                "60 fps rates",
                "rates for arms without a physical session",
            ],
            "note": (
                "Software rows are exact protocol round-trips at a stated 10 fps; "
                "they are not camera measurements. Physical rows use the observed "
                "display period and a SHA-verified payload."
            ),
        },
    }
    ctx.summary = summary

    if measured:
        best_wire = max(
            physical_ok,
            key=lambda row: row["efficiency"]["wire_payload_bps"],
        )
        dictionary = next(
            (
                row
                for row in physical_ok
                if row["arm_id"] == "A3_dictionary"
            ),
            None,
        )
        measured_arms = {row["arm_id"] for row in physical_ok}
        missing_arms = [arm for arm in ARM_IDS if arm not in measured_arms]
        ctx.conclude(
            "PHYSICAL / CAMERA CAPTURE. "
            f"E13 analysed {len(physical_ok)} successful locked M11 session(s). "
            f"The frozen 317-byte transfer uses {baseline_fill * 100:.2f}% of the "
            f"{PACKET_BYTES}-byte packet data region; the rest is zero padding. "
            f"The highest measured wire-limited application throughput was "
            f"{best_wire['efficiency']['application_bps']:.2f} bps in "
            f"{best_wire['session_id']} ({best_wire['arm_id']}), a "
            f"{best_wire['efficiency']['application_bps'] / reference['application_bps']:.2f}x "
            f"gain over the frozen {reference['application_bps']:.2f} bps. "
            + (
                "The dictionary arm recovered 145,745 application bytes in one "
                f"packet at {dictionary['efficiency']['application_bps']:.2f} bps "
                "of pre-compression application bytes (its wire payload rate is "
                f"{dictionary['efficiency']['wire_payload_bps']:.2f} bps); the "
                "higher application figure is compression gain, not extra wire "
                "capacity. "
                if dictionary
                else ""
            )
            + (
                f"Arms without a successful physical session: {', '.join(missing_arms)}. "
                if missing_arms
                else ""
            )
            + "Every successful arm matched its SHA-256 manifest; erasures and "
            "RS corrections are reported per session. Software arms that have "
            "no locked physical session are not promoted to measurements."
        )
    else:
        ctx.conclude(
            "SOFTWARE VALIDATION ONLY. E13 built and round-tripped all six M11 "
            f"arms; the frozen transfer uses {baseline_fill * 100:.2f}% of the "
            f"{PACKET_BYTES}-byte packet data region because the payload is "
            "smaller than the packet. Filling packet 0 with 2,421 bytes raises "
            "the software application rate from "
            f"{reference['application_bps']:.2f} bps to "
            f"{software_by_id['A1_fill_adaptive']['budget']['application_bps']:.2f} "
            "bps at 10 fps. No locked m11-* camera session exists yet, so no "
            "physical throughput, erasure or reliability number is claimed."
        )


SPEC = ExperimentSpec(
    id="E13_packet_utilisation",
    title="M11 packet utilisation optimisation",
    hypothesis=(
        "The 11.99% wire-packet fill is unused payload capacity, not protocol "
        "loss. Filling the packet with useful bytes, bundling logical payloads, "
        "choosing raw/compressed adaptively, using the OTL1 dictionary on "
        "repeated data and sizing RS parity to the measured channel can raise "
        "net application throughput while keeping SHA-256 exact reconstruction."
    ),
    classification="PHYSICAL (camera capture) + SOFTWARE (packet/RS validation)",
    controlled=(
        "frozen frame format, renderer, player and decoder geometry",
        "255 frames per packet and 11 bytes per frame",
        "application payload and manifest hashes",
    ),
    independent=(
        "packet fill",
        "bundle container",
        "file header size",
        "compression policy",
        "RS nsym",
    ),
    dependent=(
        "application throughput",
        "packet fill",
        "frame delivery",
        "erasures and RS corrections",
        "SHA-256 exact reconstruction",
    ),
    procedure=(
        "Build the frozen reference and five deterministic M11 arms.",
        "Round-trip every arm through the real packet, RS and container code.",
        "Render frames and capture one locked camera session per measured arm.",
        "Decode captured frames, verify the wire and application SHA-256, and measure rates from the observed display period.",
        "Compare each arm with the frozen reference and report measured values separately from projections.",
    ),
    run=run,
)
