"""E11 — Physical optical validation.

This experiment is the bridge between the simulated E01–E10 results and a real
screen→camera link.  It never creates optical data: it consumes a *capture
session* produced by `otl capture` or by importing phone photographs, decodes
the preserved images with the same decoder used everywhere else, and compares
the physical observations with the simulation baselines.

Evidence rules
--------------
* ``capture_source == "camera"`` or ``"manual-import"`` and a valid session
  (named device, display, transmitter, captures) → **PHYSICAL / CAMERA
  CAPTURE**.  The decode step is still software; that is stated explicitly.
* ``capture_source == "fixture"`` → **SOFTWARE FIXTURE (NOT PHYSICAL)**.  This
  exists so the ingestion path can be tested without pretending a rendered PNG
  is a camera measurement.
* No session, or an invalid one → **BLOCKED / NO PHYSICAL CAPTURE**.  One
  blocked trial is recorded and no success rate is invented.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from otl.compress.dictionary import decompress
from otl.config import ExperimentConfig
from otl.decoder.spatial import decode_image
from otl.errors import OTLError
from otl.metrics import Aggregate, ResourceMeter
from otl.protocol.packet import FileHeader, PACKET_BYTES, decode_packet, reassemble
from otl.rx.session import (
    load_captures,
    load_session,
    newest_session,
    validate_session,
)
from otl.tx.renderer import load_frame

from .harness import ROOT, ExperimentSpec, RunContext

SESSIONS_ROOT = ROOT / "datasets" / "physical"
RESULTS_INDEX = ROOT / "results" / "index.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _aggregate(values: list[float]) -> dict[str, float]:
    aggregate = Aggregate()
    for value in values:
        aggregate.add(value)
    return aggregate.to_dict()


def _resolve_session(ctx: RunContext) -> Path | None:
    explicit = ctx.options.get("session")
    if explicit:
        return Path(explicit)
    return newest_session(SESSIONS_ROOT)


def _blocked(ctx: RunContext, reason: str, problems: list[str] | None = None) -> None:
    problems = problems or []
    ctx.evidence_source = "BLOCKED / NO PHYSICAL CAPTURE"
    ctx.simulation_only = True
    ctx.device = None
    ctx.classification = "BLOCKED — no physical camera capture available"
    ctx.metadata = {
        "evidence_source": ctx.evidence_source,
        "session": str(ctx.options.get("session") or ""),
        "problems": problems,
        "note": (
            "No physical result was produced. Nothing in this run is a camera "
            "measurement; do not cite it as one."
        ),
    }
    ctx.record(
        config={"stage": "session", "session": ctx.options.get("session") or None},
        inputs={"captures": 0},
        outputs={"status": "blocked", "reason": reason, "problems": problems},
        metrics={"success": 0.0, "captures": 0, "crc_ok": 0},
        notes="Blocked before any optical measurement.",
    )
    ctx.summary = {
        "status": "blocked",
        "evidence_source": ctx.evidence_source,
        "reason": reason,
        "problems": problems,
        "captures": 0,
        "note": (
            "No camera images were available. This run is not a simulation of a "
            "link and it is not a physical measurement; it records the missing "
            "prerequisite."
        ),
    }
    ctx.conclude(
        "BLOCKED: no physical capture session was available. "
        f"Reason: {reason}. "
        + (f"Problems: {'; '.join(problems)}. " if problems else "")
        + "No decoding accuracy, throughput or latency is reported for a physical "
        "link because no physical link was measured. Capture a session with "
        "`otl session new`, `otl capture` or `otl session ingest`, then re-run "
        "`python3 -m experiments.run_all --only E11_physical --session <dir>`."
    )


def _ground_truth_cells(
    root: Path, record: dict[str, Any], cfg: ExperimentConfig
) -> tuple[list[int] | None, str | None, str | None]:
    """Return (cells, display_file, error) for an independently known frame."""
    display_file = record.get("display_file")
    frame = record.get("frame")
    if display_file is None and isinstance(frame, dict):
        display_file = f"display/p{int(frame['packet_id']):02d}_f{int(frame['frame_index']):03d}.png"
    if not display_file:
        return None, None, None
    # Sessions store the display file name the operator recorded (usually
    # ``p00_f000.png``), while the attached frames live under ``display/``.
    # Accept both forms so the ground truth is found without rewriting the
    # capture record after finalization.
    candidates = [root / display_file]
    if not display_file.startswith("display/"):
        candidates.insert(0, root / "display" / display_file)
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        return None, display_file, f"display frame missing: {display_file}"
    display_file = str(path.relative_to(root))
    try:
        decoded = decode_image(
            load_frame(str(path)), cfg.layout(), cfg.receiver, cfg.protocol
        )
    except OTLError as exc:
        return None, display_file, exc.to_dict()
    return list(decoded.observation.cells), display_file, None


def _bit_accuracy(observed: list[int], expected: list[int]) -> float:
    if len(observed) != len(expected) or not expected:
        return 0.0
    correct = sum(4 - int(a ^ b).bit_count() for a, b in zip(observed, expected))
    return correct / (4 * len(expected))


def _recover_payload(
    decoded_packets: dict[int, Any],
) -> tuple[FileHeader, bytes, bytes]:
    """Reassemble a file and undo the transmitter's compression.

    ``reassemble`` returns the bytes that were on the wire.  The file header
    records whether those bytes are compressed, so a SHA-256 comparison with
    the original payload must be made after decompression.  Reporting the
    compressed SHA instead was a real false negative in the first M9 video
    run.
    """
    header, wire = reassemble(decoded_packets)
    raw = decompress(wire) if header.compressed else wire
    return header, wire, raw


def _latest_index() -> dict[str, Any]:
    if not RESULTS_INDEX.is_file():
        return {}
    try:
        return json.loads(RESULTS_INDEX.read_text(encoding="utf-8")).get(
            "experiments", {}
        )
    except json.JSONDecodeError:
        return {}


def _sim(experiments: dict[str, Any], exp: str, *path: str) -> Any:
    node: Any = experiments.get(exp, {}).get("summary", {})
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------


def run(ctx: RunContext) -> None:
    session_path = _resolve_session(ctx)
    if session_path is None:
        _blocked(
            ctx,
            "no session directory under datasets/physical and no --session argument",
        )
        return

    problems = validate_session(session_path)
    if problems:
        _blocked(ctx, f"capture session is not valid: {session_path}", problems)
        return

    root = session_path
    session = load_session(root)
    if session.status != "final" or not (root / "session.lock.json").is_file():
        _blocked(
            ctx,
            "capture session is not finalized; run `otl session finalize` before analysis",
            ["session.status is not 'final' or session.lock.json is missing"],
        )
        return
    all_captures = load_captures(root)
    # The original video is preserved but is not an image; only pictures are
    # fed to the spatial decoder.
    image_captures = [
        record
        for record in all_captures
        if record.get("kind") in {"still", "video-frame"}
    ]
    media_files = len(all_captures) - len(image_captures)
    # A camera burst can contain byte-identical files (the sensor or capture
    # pipeline repeats a frame).  They are one observation, not N independent
    # trials, so aggregate over unique SHA-256 values only.  The duplicate
    # files stay on disk and are counted in the report.
    captures: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for record in image_captures:
        digest = record.get("sha256")
        if digest and digest in seen_hashes:
            continue
        if digest:
            seen_hashes.add(digest)
        captures.append(record)
    duplicate_files = len(image_captures) - len(captures)
    cfg = ExperimentConfig()
    layout = cfg.layout()
    physical = session.capture_source in {"camera", "manual-import"}
    fixture = session.capture_source == "fixture"

    if physical and session.evidence_source != "PHYSICAL / CAMERA CAPTURE":
        _blocked(
            ctx,
            "finalized session is not labelled as physical evidence",
            [f"session.evidence_source is {session.evidence_source!r}"],
        )
        return

    ctx.simulation_only = not physical
    if physical:
        ctx.evidence_source = "PHYSICAL / CAMERA CAPTURE"
        ctx.classification = "PHYSICAL (camera capture) + SOFTWARE (decode)"
        ctx.device = {
            **session.device.to_dict(),
            "display": session.display.to_dict(),
            "camera": session.capture.to_dict(),
        }
    elif fixture:
        ctx.evidence_source = "SOFTWARE FIXTURE (NOT PHYSICAL)"
        ctx.classification = "SOFTWARE FIXTURE — ingestion/decoder path only"
        ctx.device = None
    else:  # pragma: no cover - guarded by capture_source validation
        _blocked(ctx, f"unknown capture_source {session.capture_source!r}")
        return

    ctx.metadata = {
        "evidence_source": ctx.evidence_source,
        "session_id": session.session_id,
        "session_path": str(root),
        "capture_source": session.capture_source,
        "device": session.device.to_dict(),
        "display": session.display.to_dict(),
        "geometry": session.geometry.to_dict(),
        "capture_settings": session.capture.to_dict(),
        "transmitter": session.transmitter,
        "session_notes": session.notes,
        "captures": len(captures),
        "note": (
            "Decoding is software; the image bytes are physical camera output."
            if physical
            else "Fixture images are rendered PNGs, not camera output."
        ),
    }

    decode_ms: list[float] = []
    cell_accuracies: list[float] = []
    bit_accuracies: list[float] = []
    # Accuracy is averaged per displayed frame first, then across frames.  A
    # video shows each frame in several camera samples; weighting by samples
    # would let a frame that happened to be captured six times outvote one
    # captured twice.
    cell_accuracy_by_frame: dict[tuple[int, int], list[float]] = {}
    bit_accuracy_by_frame: dict[tuple[int, int], list[float]] = {}
    first_seen: dict[tuple[int, int], float] = {}
    error_counts: Counter[str] = Counter()
    crc_ok_count = 0
    index_matches = 0
    packet_frames: dict[int, dict[int, bytes]] = {}
    meter = ResourceMeter()

    for record in captures:
        decode_path = record.get("decode_path") or record.get("path")
        image_path = root / decode_path
        trial: dict[str, Any] = {
            "capture": record.get("path"),
            "decode_path": decode_path,
            "kind": record.get("kind", "still"),
            "sha256": record.get("sha256"),
            "width": record.get("width"),
            "height": record.get("height"),
            "ground_truth": record.get("frame"),
            "display_file": record.get("display_file"),
        }
        if not image_path.is_file():
            ctx.record(
                config=trial,
                inputs={"sha256": record.get("sha256")},
                outputs={"status": "missing"},
                metrics={"success": 0.0, "crc_ok": 0.0, "decode_ms": 0.0},
                errors=[{"stage": "io", "code": "E_IO", "message": "file missing"}],
                notes="Preserved capture is missing; nothing was decoded.",
            )
            continue
        image = load_frame(str(image_path))
        started = time.perf_counter()
        try:
            decoded = decode_image(image, layout, cfg.receiver, cfg.protocol)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            error: dict[str, Any] | None = None
        except OTLError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            decoded = None
            error = exc.to_dict()
        decode_ms.append(elapsed_ms)
        crc_ok = bool(decoded and decoded.crc_ok)
        if error is not None:
            error_counts[str(error.get("code", "unknown"))] += 1

        ground_cells, display_file, ground_error = _ground_truth_cells(
            root, record, cfg
        )
        # A video has no operator-recorded frame mapping.  Its frame identity
        # comes from the recovered OTL header, so only a CRC-valid header may
        # select the ground-truth PNG.
        if (
            ground_cells is None
            and decoded is not None
            and crc_ok
            and record.get("kind") == "video-frame"
        ):
            decoded_header = decoded.frame.header
            derived = dict(record)
            derived["display_file"] = (
                f"display/p{decoded_header.packet_id:02d}"
                f"_f{decoded_header.frame_index:03d}.png"
            )
            ground_cells, display_file, ground_error = _ground_truth_cells(
                root, derived, cfg
            )
        observed_cells = list(decoded.observation.cells) if decoded else None
        cell_accuracy = None
        bit_accuracy = None
        frame_key = None
        if decoded is not None:
            frame_key = (
                decoded.frame.header.packet_id,
                decoded.frame.header.frame_index,
            )
        if observed_cells is not None and ground_cells is not None:
            matches = sum(1 for a, b in zip(observed_cells, ground_cells) if a == b)
            cell_accuracy = matches / len(ground_cells)
            bit_accuracy = _bit_accuracy(observed_cells, ground_cells)
            cell_accuracies.append(cell_accuracy)
            bit_accuracies.append(bit_accuracy)
            if frame_key is not None:
                cell_accuracy_by_frame.setdefault(frame_key, []).append(cell_accuracy)
                bit_accuracy_by_frame.setdefault(frame_key, []).append(bit_accuracy)

        if crc_ok:
            crc_ok_count += 1
            header = decoded.frame.header
            packet_frames.setdefault(header.packet_id, {})[
                header.frame_index
            ] = decoded.frame.data
            position = record.get("pos_msec")
            if position is not None and frame_key is not None:
                first_seen.setdefault(frame_key, float(position))
        header = decoded.frame.header if decoded else None
        frame_match = None
        if header is not None and isinstance(record.get("frame"), dict):
            frame_match = (
                header.packet_id == int(record["frame"]["packet_id"])
                and header.frame_index == int(record["frame"]["frame_index"])
            )
            if frame_match:
                index_matches += 1

        ctx.record(
            config={
                **trial,
                "session_id": session.session_id,
                "capture_source": session.capture_source,
            },
            inputs={
                "sha256": record.get("sha256"),
                "original_sha256": record.get("original_sha256"),
                "decode_path": decode_path,
                "display_file": display_file,
                "image_px": int(image.shape[0] * image.shape[1]),
            },
            outputs={
                "status": "decoded" if decoded else "error",
                "crc_ok": crc_ok,
                "packet_id": header.packet_id if header else None,
                "frame_index": header.frame_index if header else None,
                "frame_index_matches_ground_truth": frame_match,
                "cells": observed_cells,
                "ground_truth_cells": ground_cells,
                "error": error,
                "ground_truth_error": ground_error,
            },
            metrics={
                "success": 1.0 if crc_ok else 0.0,
                "crc_ok": 1.0 if crc_ok else 0.0,
                "decode_ms": elapsed_ms,
                "cell_accuracy": cell_accuracy if cell_accuracy is not None else -1.0,
                "bit_accuracy": bit_accuracy if bit_accuracy is not None else -1.0,
                "fiducial_confidence": (
                    decoded.fiducials.confidence if decoded else -1.0
                ),
                "contrast": decoded.observation.contrast if decoded else -1.0,
                "bit_margin": decoded.observation.bit_margin if decoded else -1.0,
            },
            errors=[error] if error else [],
            notes=(
                "Physical camera image decoded by the standard OTL decoder."
                if physical
                else "Fixture image; not a camera measurement."
            ),
        )

    # -- frame delivery and observed display rate ---------------------------
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
    packet_duration_s = (
        expected_frames / display_fps
        if expected_frames and display_fps and display_fps > 0
        else None
    )

    # -- packet/file reconstruction ----------------------------------------
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
                    "stats": packet.stats.to_dict() if hasattr(packet, "stats") else None,
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
            payload_sha256 = _sha256(payload)
            expected = session.transmitter.get("payload_sha256")
            payload_success = bool(expected and payload_sha256 == expected)
            if expected and not payload_success:
                payload_error = "payload SHA-256 differs from the transmitted payload"
        except OTLError as exc:
            payload_error = exc.to_dict()
    reassembly_ms = (time.perf_counter() - reassembly_started) * 1000.0
    resource = meter.sample().to_dict()

    # -- throughput ---------------------------------------------------------
    positions = sorted(
        float(record["pos_msec"])
        for record in captures
        if record.get("pos_msec") is not None
    )
    capture_duration_s = (
        (positions[-1] - positions[0]) / 1000.0 if len(positions) >= 2 else None
    )
    decode_wall_s = sum(decode_ms) / 1000.0
    decoded_frames = crc_ok_count
    # Repeated camera samples of one displayed frame are not new bits.  Rate
    # calculations therefore use unique frame indices and the observed display
    # period, not the 30 fps camera rate.
    raw_bps = (
        unique_frames * cfg.protocol.payload_bits / packet_duration_s
        if payload_success and packet_duration_s and packet_duration_s > 0
        else None
    )
    channel_bps = (
        cfg.protocol.total_bits * display_fps
        if payload_success and display_fps and display_fps > 0
        else None
    )
    rs_goodput_bps = (
        PACKET_BYTES * 8.0 / packet_duration_s
        if payload_success and packet_duration_s and packet_duration_s > 0
        else None
    )
    net_bps = (
        payload_bytes * 8.0 / packet_duration_s
        if payload_success and packet_duration_s and packet_duration_s > 0
        else None
    )

    unique_cell_accuracies = [
        sum(values) / len(values)
        for values in cell_accuracy_by_frame.values()
        if values
    ]
    unique_bit_accuracies = [
        sum(values) / len(values)
        for values in bit_accuracy_by_frame.values()
        if values
    ]
    physical_cell_accuracy = (
        sum(unique_cell_accuracies) / len(unique_cell_accuracies)
        if unique_cell_accuracies
        else None
    )
    physical_bit_accuracy = (
        sum(unique_bit_accuracies) / len(unique_bit_accuracies)
        if unique_bit_accuracies
        else None
    )
    crc_rate = crc_ok_count / len(captures) if captures else 0.0
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

    # -- comparison with the simulation baselines ---------------------------
    experiments = _latest_index()
    comparisons: list[dict[str, Any]] = []

    def compare(
        metric: str,
        simulated: Any,
        observed: Any,
        unit: str,
        basis: str,
    ) -> None:
        delta = None
        if isinstance(simulated, (int, float)) and isinstance(observed, (int, float)):
            delta = float(observed) - float(simulated)
        comparisons.append(
            {
                "metric": metric,
                "simulated": simulated,
                "observed": observed,
                "delta": delta,
                "unit": unit,
                "basis": basis,
                "evidence_source": ctx.evidence_source,
            }
        )

    compare(
        "clean-cell accuracy",
        _sim(experiments, "E02_patterns", "mean_target_accuracy_by_severity", "clean"),
        physical_cell_accuracy,
        "fraction",
        "E02 clean simulated channel vs E11 observed captures with known frames",
    )
    compare(
        "file-transfer success",
        _sim(experiments, "E09_end_to_end", "success_rate"),
        1.0 if payload_success else 0.0,
        "fraction",
        "E09 64 simulated trials vs E11 one physical packet; sample sizes differ",
    )
    compare(
        "decode latency",
        _sim(experiments, "E10_determinism", "latency_ms", "decode_mean"),
        (sum(decode_ms) / len(decode_ms)) if decode_ms else None,
        "ms/frame",
        "E10 software decode mean vs E11 observed-image decode mean (same decoder)",
    )
    compare(
        "raw payload bit rate at 60 fps",
        _sim(experiments, "E01_capacity", "framed_payload_bps_at_60fps"),
        raw_bps,
        "bps",
        "E01 payload arithmetic at 60 fps vs E11 at the observed 10 fps; the rate ratio is mostly the display rate",
    )
    e01_payload_bits = _sim(experiments, "E01_capacity", "payload_bits")
    e01_rs_goodput = _sim(experiments, "E01_capacity", "rs_goodput_bps_at_60fps")
    if display_fps and raw_bps is not None and isinstance(e01_payload_bits, (int, float)):
        compare(
            "raw payload bit rate at the observed display rate",
            float(e01_payload_bits) * display_fps,
            raw_bps,
            "bps",
            "E01 arithmetic at E11's observed display rate vs E11 unique delivered frames",
        )
    if (
        display_fps
        and rs_goodput_bps is not None
        and isinstance(e01_rs_goodput, (int, float))
    ):
        compare(
            "RS goodput at the observed display rate",
            float(e01_rs_goodput) * display_fps / 60.0,
            rs_goodput_bps,
            "bps",
            "E01 arithmetic at E11's observed display rate vs E11 RS(255,223) packet capacity",
        )

    ctx.summary = {
        "status": "measured" if physical else "fixture",
        "evidence_source": ctx.evidence_source,
        "session_id": session.session_id,
        "capture_source": session.capture_source,
        "device": session.device.to_dict(),
        "display": session.display.to_dict(),
        "geometry": session.geometry.to_dict(),
        "capture_settings": session.capture.to_dict(),
        "captures": {
            "count": len(captures),
            "files": len(image_captures),
            "image_files": len(image_captures),
            "media_files": media_files,
            "duplicate_files": duplicate_files,
            "decoded_crc_ok": crc_ok_count,
            "crc_rate": crc_rate,
            "attempt_failure_rate": 1.0 - crc_rate,
            "detection_failures": int(error_counts.get("E_DETECT", 0)),
            "error_counts": dict(sorted(error_counts.items())),
            "unique_frames": unique_frames,
            "expected_frames": expected_frames,
            "frame_delivery_rate": frame_delivery_rate,
            "frame_loss_rate": (
                1.0 - frame_delivery_rate
                if frame_delivery_rate is not None
                else None
            ),
            "ground_truth_frames": len(unique_cell_accuracies),
            "ground_truth_attempts": len(cell_accuracies),
            "frame_index_matches": index_matches,
            "note": (
                "count is unique image SHA-256 values; files includes "
                "byte-identical duplicates from a burst. crc_rate is the "
                "fraction of camera samples that decoded with a valid frame "
                "CRC; frame_delivery_rate is unique displayed frames / "
                "expected packet frames."
            ),
        },
        "accuracy": {
            "cell_accuracy_mean": physical_cell_accuracy,
            "bit_accuracy_mean": physical_bit_accuracy,
            "cell_accuracy_per_capture_mean": (
                sum(cell_accuracies) / len(cell_accuracies)
                if cell_accuracies
                else None
            ),
            "bit_accuracy_per_capture_mean": (
                sum(bit_accuracies) / len(bit_accuracies)
                if bit_accuracies
                else None
            ),
            "cell_error_rate": (
                1.0 - physical_cell_accuracy
                if physical_cell_accuracy is not None
                else None
            ),
            "bit_error_rate": (
                1.0 - physical_bit_accuracy
                if physical_bit_accuracy is not None
                else None
            ),
            "cell_accuracy": _aggregate(unique_cell_accuracies),
            "bit_accuracy": _aggregate(unique_bit_accuracies),
        },
        "latency": {
            "decode_ms": _aggregate(decode_ms),
            "decode_wall_s": decode_wall_s,
            "decode_samples_fps": (
                len(captures) / decode_wall_s if decode_wall_s else None
            ),
            "decode_attempts": len(captures),
            "packet_decode_ms": packet_ms,
            "reassembly_ms": reassembly_ms,
            "reconstruction_ms": packet_ms + reassembly_ms,
            "resource": resource,
        },
        "throughput": {
            "capture_duration_s": capture_duration_s,
            "capture_fps": session.capture.fps,
            "display_fps_manifest": manifest_fps,
            "display_fps_observed": observed_display_fps,
            "display_fps_used": display_fps,
            "packet_duration_s": packet_duration_s,
            "expected_frames": expected_frames,
            "frames_captured": len(captures),
            "frames_decoded": decoded_frames,
            "unique_frames": unique_frames,
            "frame_delivery_rate": frame_delivery_rate,
            "frame_loss_rate": (
                1.0 - frame_delivery_rate
                if frame_delivery_rate is not None
                else None
            ),
            "raw_channel_bps": channel_bps,
            "raw_payload_bps": raw_bps,
            "rs_goodput_bps": rs_goodput_bps,
            "net_bps": net_bps,
            "payload_bytes": payload_bytes,
            "wire_bytes": wire_bytes,
            "original_bytes": original_bytes,
            "compressed": compressed,
            "compression_ratio": compression_ratio,
            "payload_success": payload_success,
            "payload_sha256": payload_sha256,
            "payload_error": payload_error,
            "note": (
                "All rates are reported only when the complete payload was "
                "reassembled and its SHA-256 matched. raw_channel_bps and "
                "raw_payload_bps are gross rates at the observed display rate; "
                "rs_goodput_bps is the packet capacity after RS(255,223); "
                "net_bps is the SHA-verified application payload. Repeated "
                "camera samples of one displayed frame are counted once."
            ),
        },
        "packet_summary": {
            "packets_expected": packets_expected,
            "packets_received": packets_received,
            "packet_loss_rate": packet_loss_rate,
            "corrected_symbols": corrected_symbols,
            "erased_frames": erased_frames,
            "rs_nsym": cfg.ecc.nsym,
        },
        "packets": packet_rows,
        "comparison": comparisons,
        "note": (
            "PHYSICAL camera bytes decoded by software. Accuracy is relative to "
            "the displayed frame only where the operator recorded an independent "
            "frame mapping; video frame identity comes from the OTL header."
            if physical
            else "SOFTWARE FIXTURE: the images are fixture captures, not camera data."
        ),
    }

    if physical:
        delivery = (
            f"{unique_frames}/{expected_frames} unique displayed frames "
            f"({frame_delivery_rate:.1%})"
            if frame_delivery_rate is not None
            else f"{unique_frames} unique displayed frames"
        )
        accuracy = (
            f"Mean cell accuracy {physical_cell_accuracy:.3f} and bit accuracy "
            f"{physical_bit_accuracy:.3f} over {len(unique_cell_accuracies)} unique "
            "frames with a display mapping. "
            if physical_cell_accuracy is not None
            else "No independent per-frame mapping was recorded, so cell "
            "accuracy is not claimed; only CRC and payload results are reported. "
        )
        payload = (
            f"A complete payload of {payload_bytes} bytes was recovered"
            + (
                f" from {wire_bytes} compressed bytes "
                f"({compression_ratio:.2f}x)"
                if compressed and wire_bytes and compression_ratio is not None
                else ""
            )
            + " and its SHA-256 matched the transmitted payload. "
            if payload_success
            else "No complete payload was reassembled from this session. "
        )
        rates = (
            f"At the observed {display_fps:.2f} display fps the gross channel rate "
            f"is {channel_bps:.0f} bps, the gross payload rate is {raw_bps:.0f} bps, "
            f"the RS(255,223) goodput is {rs_goodput_bps:.0f} bps and the "
            f"SHA-verified application rate is {net_bps:.0f} bps. "
            if payload_success
            and display_fps
            and channel_bps
            and raw_bps
            and rs_goodput_bps
            and net_bps
            else ""
        )
        latency = (
            f"Decode latency {sum(decode_ms)/len(decode_ms):.2f} ms per camera "
            f"sample, packet decode + reassembly {packet_ms + reassembly_ms:.2f} ms, "
            f"decode throughput {len(captures)/decode_wall_s:.1f} samples/s. "
            if decode_ms and decode_wall_s
            else ""
        )
        ctx.conclude(
            f"PHYSICAL / CAMERA CAPTURE. Session {session.session_id} from "
            f"{session.device.model or 'unnamed device'} capturing a "
            f"{session.display.model or 'unnamed display'}: {len(captures)} "
            f"camera samples, {crc_ok_count} passed the frame CRC "
            f"({crc_rate:.1%}); {delivery}. {accuracy}{payload}{rates}{latency}"
            "All physical numbers come from the preserved camera files; decoding "
            "is software. Compare with E01–E10 only through the comparison table, "
            "which states the basis of every pair."
        )
    else:
        ctx.conclude(
            f"SOFTWARE FIXTURE, NOT PHYSICAL EVIDENCE. Session {session.session_id} "
            f"contains {len(captures)} fixture images; {crc_ok_count} "
            f"passed the frame CRC ({crc_rate:.1%}). This run exercises the capture "
            "ingestion and E11 analysis path only. It must not be reported as a "
            "camera measurement or used to upgrade any claim to VERIFIED."
        )


SPEC = ExperimentSpec(
    id="E11_physical",
    title="Physical optical validation (screen → camera)",
    hypothesis=(
        "The existing OTL frame, renderer and decoder can recover FULL16 frames "
        "from real smartphone-camera images of a screen, with cell accuracy and "
        "CRC success lower than the simulated clean channel because of optics, "
        "exposure, rolling shutter, moiré and hand motion."
    ),
    classification="PHYSICAL (camera capture) + SOFTWARE (decode), or BLOCKED",
    controlled=(
        "protocol",
        "layout",
        "renderer",
        "decoder",
        "display frame sequence",
        "capture settings",
    ),
    independent=(
        "device",
        "display",
        "distance",
        "angle",
        "ambient light",
        "exposure/focus",
    ),
    dependent=(
        "frame CRC success",
        "cell/bit accuracy",
        "payload reconstruction",
        "decode latency",
        "capture/decode rate",
        "throughput",
    ),
    procedure=(
        "Render the payload to PNG frames and build a full-screen player.",
        "Record the exact displayed frames, their hashes and the player manifest.",
        "Capture the screen with a named smartphone camera, preserving originals.",
        "Import the originals into a session without re-encoding them.",
        "Decode every preserved image with the standard OTL decoder.",
        "Record CRC, cell/bit accuracy, packet reconstruction, latency and rate.",
        "Compare physical observations with the E01–E10 simulation baselines.",
    ),
    run=run,
    evidence_source="BLOCKED / NO PHYSICAL CAPTURE",
    simulation_only=True,
    device_required=True,
)
