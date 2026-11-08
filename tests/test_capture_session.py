"""Tests for physical capture ingestion and session locking."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from otl.config import ExperimentConfig
from otl.errors import CaptureError
from otl.rx.capture import ingest_image, ingest_video
from otl.rx.session import (
    CaptureSettings,
    DeviceInfo,
    DisplayInfo,
    add_captures,
    attach_transmitter,
    finalize_session,
    list_sessions,
    load_captures,
    load_session,
    new_session,
    newest_session,
    require_valid_session,
    validate_session,
)
from otl.tx.player import PlayerConfig, build_player
from otl.tx.renderer import render_frame, save_frame


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rendered(tmp_path: Path) -> tuple[Path, Path]:
    cfg = ExperimentConfig()
    frames = tmp_path / "rendered"
    frames.mkdir()
    path = frames / "p00_f000.png"
    save_frame(str(path), render_frame([7] * 30, cfg.layout(), cfg.screen))
    build_player([path], tmp_path / "player.html", PlayerConfig())
    return path, frames


# Imported late so the helper above stays readable.
from otl.tx.player import PlayerConfig  # noqa: E402


def _session(tmp_path: Path, *, source: str = "fixture"):
    return new_session(
        tmp_path / "sessions",
        "s1",
        device=DeviceInfo(model="Test Phone", os="test", camera="rear"),
        display=DisplayInfo(model="Test Display", width_px=2560, height_px=1664),
        capture=CaptureSettings(mode="photo", resolution="4032x3024"),
        capture_source=source,
        notes="unit test",
    )


def _attached_session(tmp_path: Path, *, source: str = "fixture"):
    image, frames = _rendered(tmp_path)
    root = _session(tmp_path, source=source)
    attach_transmitter(
        root,
        frames,
        tmp_path / "player_manifest.json",
        payload_name="demo.txt",
        payload_sha256="0" * 64,
    )
    return root, image


def test_ingest_image_preserves_original_bytes(tmp_path) -> None:
    image, _ = _rendered(tmp_path)
    root = _session(tmp_path)
    original = image.read_bytes()

    record = ingest_image(root, image)
    preserved = root / record.path
    assert preserved.is_file()
    assert preserved.read_bytes() == original
    assert image.read_bytes() == original
    assert record.sha256 == _sha(preserved)
    assert record.original_sha256 is None
    assert record.source == "camera"

    # A second import of the same name must not overwrite the first.
    second = ingest_image(root, image)
    assert second.path != record.path
    assert (root / second.path).read_bytes() == original


def test_add_captures_verifies_hash_and_appends_log(tmp_path) -> None:
    image, _ = _rendered(tmp_path)
    root = _session(tmp_path)
    record = ingest_image(root, image)
    row = record.to_dict()
    row["kind"] = "still"
    row["frame"] = {"packet_id": 0, "frame_index": 0}
    row["display_file"] = "display/p00_f000.png"
    added = add_captures(root, [row])
    assert len(added) == 1
    assert load_captures(root)[0]["path"] == record.path
    log = (root / "captures" / "index.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(log) == 1
    assert json.loads(log[0])["sha256"] == record.sha256

    bad = dict(row)
    bad["sha256"] = "0" * 64
    with pytest.raises(CaptureError):
        add_captures(root, [bad])


def test_attach_transmitter_copies_hashed_display_frames(tmp_path) -> None:
    root, image = _attached_session(tmp_path)
    session = load_session(root)
    assert session.transmitter["frame_count"] == 1
    assert session.transmitter["payload_sha256"] == "0" * 64
    copied = root / "display" / "p00_f000.png"
    assert copied.read_bytes() == image.read_bytes()
    assert (root / "display" / "player_manifest.json").is_file()


def test_session_validation_reports_missing_pieces(tmp_path) -> None:
    root = _session(tmp_path)
    problems = validate_session(root)
    assert "transmitter is not attached" in problems
    assert "no captures recorded" in problems
    with pytest.raises(CaptureError):
        require_valid_session(root)


def test_valid_fixture_session_can_be_finalized_and_locked(tmp_path) -> None:
    root, image = _attached_session(tmp_path)
    record = ingest_image(root, image)
    row = record.to_dict()
    row.update(
        {
            "kind": "still",
            "frame": {"packet_id": 0, "frame_index": 0},
            "display_file": "display/p00_f000.png",
        }
    )
    add_captures(root, [row])
    assert validate_session(root) == []

    lock = finalize_session(root)
    assert lock["capture_count"] == 1
    assert lock["evidence_source"] == "SOFTWARE FIXTURE (NOT PHYSICAL)"
    assert (root / "session.lock.json").is_file()
    session = load_session(root)
    assert session.status == "final"
    assert session.evidence_source == "SOFTWARE FIXTURE (NOT PHYSICAL)"

    with pytest.raises(CaptureError):
        add_captures(root, [row])
    with pytest.raises(CaptureError):
        finalize_session(root)


def test_new_session_refuses_reuse_and_bad_ids(tmp_path) -> None:
    _session(tmp_path)
    with pytest.raises(CaptureError):
        _session(tmp_path)
    with pytest.raises(CaptureError):
        new_session(tmp_path / "sessions", "../escape")


def test_list_and_newest_session(tmp_path) -> None:
    first = _session(tmp_path)
    second = new_session(
        tmp_path / "sessions",
        "s2",
        device=DeviceInfo(model="Other"),
        display=DisplayInfo(model="Other display"),
    )
    rows = list_sessions(tmp_path / "sessions")
    assert {row["session_id"] for row in rows} == {"s1", "s2"}
    assert newest_session(tmp_path / "sessions") == second
    assert first != second


def test_ingest_video_extracts_lossless_frames(tmp_path) -> None:
    cv2 = pytest.importorskip("cv2")
    video = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(
        str(video), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48)
    )
    if not writer.isOpened():  # pragma: no cover - codec availability
        pytest.skip("mp4v writer unavailable")
    for index in range(5):
        frame = np.full((48, 64, 3), index * 40, dtype=np.uint8)
        writer.write(frame)
    writer.release()

    root = _session(tmp_path)
    record, frames = ingest_video(root, video, stride=2)
    assert record.sha256 == _sha(root / record.path)
    assert len(frames) == 3
    for row in frames:
        assert (root / row["path"]).is_file()
        assert row["sha256"] == _sha(root / row["path"])
        assert row["pos_msec"] >= 0
