"""Evidence-gate tests for E11 physical validation.

These tests never claim a physical measurement.  The fixture session is
explicitly labelled ``fixture`` so E11 must report SOFTWARE FIXTURE, and the
missing-session path must report BLOCKED.
"""

from __future__ import annotations

import io

from PIL import Image

from experiments import e11_physical
from experiments.harness import RunContext
from otl.compress.dictionary import compress
from otl.config import ExperimentConfig
from otl.protocol.frame import pack_frame
from otl.protocol.packet import build_file, decode_packet
from otl.rx.capture import ingest_image
from otl.rx.session import (
    CaptureSettings,
    DeviceInfo,
    DisplayInfo,
    add_captures,
    attach_transmitter,
    finalize_session,
    new_session,
)
from otl.tx.player import PlayerConfig, build_player
from otl.tx.renderer import render_frame, save_frame
from otl.types import FrameHeader


def _context(tmp_path, session=None) -> RunContext:
    ctx = RunContext(
        spec=e11_physical.SPEC,
        run_id="test-run",
        out_dir=tmp_path,
        options={"session": str(session)} if session is not None else {},
    )
    ctx._raw = io.StringIO()
    return ctx


def test_blocked_when_session_is_missing(tmp_path) -> None:
    ctx = _context(tmp_path, tmp_path / "does-not-exist")
    e11_physical.run(ctx)
    assert ctx.summary["status"] == "blocked"
    assert ctx.evidence_source == "BLOCKED / NO PHYSICAL CAPTURE"
    assert ctx.simulation_only is True
    assert ctx.device is None
    assert len(ctx.trials) == 1
    assert "BLOCKED" in ctx.conclusion
    assert "No camera images were available" in ctx.summary["note"]


def _fixture_session(tmp_path, *, display_file="display/p00_f000.png", duplicates=0):
    cfg = ExperimentConfig()
    frames = tmp_path / "rendered"
    frames.mkdir()
    frame = frames / "p00_f000.png"
    cells = pack_frame(FrameHeader(0, 0), bytes(11), cfg.protocol)
    save_frame(str(frame), render_frame(cells, cfg.layout(), cfg.screen))
    build_player([frame], tmp_path / "player.html")

    root = new_session(
        tmp_path / "sessions",
        "fixture-session",
        device=DeviceInfo(model="Synthetic camera"),
        display=DisplayInfo(model="Synthetic display"),
        capture=CaptureSettings(mode="photo", resolution="2560x1664"),
        capture_source="fixture",
    )
    attach_transmitter(
        root,
        frames,
        tmp_path / "player_manifest.json",
        payload_name="fixture.bin",
        payload_sha256="0" * 64,
    )
    record = ingest_image(root, frame, source="fixture")
    row = record.to_dict()
    row.update(
        {
            "kind": "still",
            "frame": {"packet_id": 0, "frame_index": 0},
            "display_file": display_file,
        }
    )
    rows = [row]
    for index in range(duplicates):
        copy = tmp_path / f"duplicate_{index}.png"
        copy.write_bytes(frame.read_bytes())
        duplicate = ingest_image(root, copy, source="fixture").to_dict()
        duplicate.update(
            {
                "kind": "still",
                "frame": {"packet_id": 0, "frame_index": 0},
                "display_file": display_file,
            }
        )
        rows.append(duplicate)
    add_captures(root, rows)
    finalize_session(root)
    return root


def test_fixture_session_is_never_reported_as_physical(tmp_path) -> None:
    session = _fixture_session(tmp_path)
    ctx = _context(tmp_path / "run", session)
    e11_physical.run(ctx)
    assert ctx.summary["status"] == "fixture"
    assert ctx.evidence_source == "SOFTWARE FIXTURE (NOT PHYSICAL)"
    assert ctx.simulation_only is True
    assert ctx.device is None
    assert ctx.trials
    assert ctx.trials[0]["metrics"]["crc_ok"] == 1.0
    assert ctx.trials[0]["metrics"]["cell_accuracy"] == 1.0
    assert "NOT PHYSICAL EVIDENCE" in ctx.conclusion
    # A fixture must not produce a throughput claim.
    assert ctx.summary["throughput"]["net_bps"] is None


def test_bare_display_name_and_duplicate_burst_are_handled(tmp_path) -> None:
    """A burst of identical files is one observation, not N trials.

    The operator normally records ``p00_f000.png`` (relative to ``display/``),
    and a camera burst can repeat the same frame.  Ground truth must still be
    found and the CRC rate must not be inflated by byte-identical copies.
    """
    session = _fixture_session(
        tmp_path, display_file="p00_f000.png", duplicates=2
    )
    ctx = _context(tmp_path / "run", session)
    e11_physical.run(ctx)
    captures = ctx.summary["captures"]
    assert captures["count"] == 1
    assert captures["files"] == 3
    assert captures["duplicate_files"] == 2
    assert captures["crc_rate"] == 1.0
    assert captures["ground_truth_frames"] == 1
    assert ctx.trials[0]["metrics"]["cell_accuracy"] == 1.0


def test_recovered_payload_is_decompressed_before_hashing() -> None:
    """A compressed packet must be compared after decompression.

    The first M9 video attempt reassembled the exact compressed bytes and then
    compared their SHA-256 with the original file, producing a false payload
    mismatch.
    """
    payload = b"OTL physical validation payload\n" * 40
    packed, _stats = compress(payload)
    header, packets = build_file(
        packed, "payload.txt", compressed=True, original_len=len(payload)
    )
    frames = {
        index: data
        for index, (_frame_header, data) in enumerate(packets[0].iter_frames())
    }
    decoded = decode_packet(0, frames)
    recovered_header, wire, raw = e11_physical._recover_payload({0: decoded})
    assert recovered_header.compressed is True
    assert wire == packed
    assert wire != raw
    assert raw == payload
    assert recovered_header.original_len == len(payload)


def test_video_repeats_count_as_one_delivered_frame(tmp_path) -> None:
    """Distinct camera samples of one displayed frame are one frame of data.

    A 30 fps camera sees each 10 fps display frame about three times.  Those
    samples have different SHA-256 values (sensor noise) but the same OTL
    header; throughput must count the frame once, not three times.
    """
    cfg = ExperimentConfig()
    frames = tmp_path / "rendered"
    frames.mkdir()
    frame = frames / "p00_f000.png"
    cells = pack_frame(FrameHeader(0, 0), bytes(11), cfg.protocol)
    save_frame(str(frame), render_frame(cells, cfg.layout(), cfg.screen))
    build_player([frame], tmp_path / "player.html", PlayerConfig(fps=10.0))

    root = new_session(
        tmp_path / "sessions",
        "video-session",
        device=DeviceInfo(model="Synthetic camera"),
        display=DisplayInfo(model="Synthetic display"),
        capture=CaptureSettings(mode="video", resolution="1920x1440"),
        capture_source="fixture",
    )
    attach_transmitter(
        root,
        frames,
        tmp_path / "player_manifest.json",
        payload_name="fixture.bin",
        payload_sha256="0" * 64,
    )
    rows = []
    base = render_frame(cells, cfg.layout(), cfg.screen)
    for index, (value, position) in enumerate(((255, 0.0), (254, 100.0))):
        sample = tmp_path / f"sample_{index}.png"
        # Change a margin pixel so the SHA-256 differs without touching a cell.
        image = base.copy()
        image[2, 2] = value
        Image.fromarray(image).save(sample)
        record = ingest_image(root, sample, source="fixture").to_dict()
        record.update(
            {
                "kind": "video-frame",
                "pos_msec": position,
            }
        )
        rows.append(record)
    add_captures(root, rows)
    finalize_session(root)

    ctx = _context(tmp_path / "run", root)
    e11_physical.run(ctx)
    captures = ctx.summary["captures"]
    assert captures["count"] == 2
    assert captures["unique_frames"] == 1
    assert captures["expected_frames"] == 1
    assert captures["frame_delivery_rate"] == 1.0
    assert captures["ground_truth_frames"] == 1
    throughput = ctx.summary["throughput"]
    assert throughput["frames_captured"] == 2
    assert throughput["unique_frames"] == 1
    assert throughput["display_fps_used"] == 10.0
    # This fixture has no matching payload, so rate metrics are withheld.
    assert throughput["raw_payload_bps"] is None
    assert throughput["net_bps"] is None
