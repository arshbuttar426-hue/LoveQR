"""Accounting and evidence-gate tests for E12.

These tests never claim a physical measurement.  They lock the arithmetic that
M10 reports (rates, utilisation, loss decomposition), the measured-versus-
projection split, the brightness parser, and the rule that a fixture session can
never be analysed as physical evidence.
"""

from __future__ import annotations

import io

import pytest

from experiments import e12_channel_efficiency as e12
from experiments.harness import RunContext
from otl.config import ExperimentConfig
from otl.protocol.frame import pack_frame
from otl.protocol.packet import (
    DATA_BYTES_PER_FRAME,
    FRAMES_PER_PACKET,
    PACKET_BYTES,
    PAYLOAD_0,
)
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
from otl.tx.player import build_player
from otl.tx.renderer import render_frame, save_frame
from otl.types import FrameHeader


def _context(tmp_path, sessions=None) -> RunContext:
    ctx = RunContext(
        spec=e12.SPEC,
        run_id="test-run",
        out_dir=tmp_path,
        options={"sessions": [str(item) for item in sessions]} if sessions else {},
    )
    ctx._raw = io.StringIO()
    return ctx


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


def test_efficiency_budget_matches_the_m9_transfer() -> None:
    cfg = ExperimentConfig()
    budget = e12.efficiency_budget(
        cfg,
        display_fps=10.0,
        expected_frames=FRAMES_PER_PACKET,
        payload_bytes=317,
        wire_bytes=294,
        compressed=True,
    )
    packet_duration = FRAMES_PER_PACKET / 10.0
    assert budget["packet_duration_s"] == pytest.approx(packet_duration)
    assert budget["channel_bps"] == pytest.approx(120 * 10.0)
    assert budget["gross_payload_bps"] == pytest.approx(88 * 10.0)
    assert budget["rs_goodput_bps"] == pytest.approx(
        PACKET_BYTES * 8.0 / packet_duration
    )
    assert budget["application_bps"] == pytest.approx(317 * 8.0 / packet_duration)
    # 317 bytes spread over 255 displayed frames, against 11 payload bytes.
    assert budget["application_bytes_per_frame"] == pytest.approx(317 / 255)
    assert budget["application_payload_utilisation_per_frame"] == pytest.approx(
        (317 / 255) / DATA_BYTES_PER_FRAME
    )
    assert budget["packet_fill_wire"] == pytest.approx(294 / PACKET_BYTES)
    assert budget["packet_fill_application"] == pytest.approx(317 / PACKET_BYTES)
    assert budget["application_payload_capacity_utilisation"] == pytest.approx(
        317 / PAYLOAD_0
    )
    assert budget["frame_payload_utilisation"] == pytest.approx(88 / 120)
    assert budget["frame_protocol_overhead"] == pytest.approx(32 / 120)


def test_loss_decomposition_is_an_exact_identity() -> None:
    cfg = ExperimentConfig()
    budget = e12.efficiency_budget(
        cfg,
        display_fps=10.0,
        expected_frames=255,
        payload_bytes=317,
        wire_bytes=294,
        compressed=True,
    )
    losses = {item["stage"]: item["bps"] for item in budget["losses"]}
    # compression_gain is stored negated; adding it back must close the gap.
    reconstructed = (
        budget["application_bps"]
        + losses["framing_header_and_crc"]
        + losses["reed_solomon_parity"]
        + losses["unused_packet_capacity"]
        + losses["compression_gain"]
    )
    assert reconstructed == pytest.approx(budget["channel_bps"])
    assert budget["residual_bps"] == pytest.approx(0.0, abs=1e-9)
    assert budget["dominant_loss"]["stage"] == "unused_packet_capacity"
    # The narrower RS-to-application gap excludes framing and RS parity.
    assert budget["rs_to_application_gap_bps"] == pytest.approx(
        losses["unused_packet_capacity"] + losses["compression_gain"]
    )


def test_projection_is_labelled_and_never_measured() -> None:
    cfg = ExperimentConfig()
    projected = e12.projection(cfg, payload_bytes=317, fps=60.0, packets=1)
    assert projected["status"] == e12.PROJECTION_LABEL
    assert "not measured" in projected["status"]
    assert projected["frames"] == FRAMES_PER_PACKET
    assert projected["channel_bps"] == pytest.approx(120 * 60.0)
    assert projected["rs_goodput_bps"] == pytest.approx(
        PACKET_BYTES * 8.0 / (FRAMES_PER_PACKET / 60.0)
    )
    assert projected["payload_capacity_utilisation"] == pytest.approx(317 / PAYLOAD_0)


def test_budget_rejects_impossible_denominators() -> None:
    cfg = ExperimentConfig()
    with pytest.raises(ValueError):
        e12.efficiency_budget(
            cfg,
            display_fps=0.0,
            expected_frames=255,
            payload_bytes=1,
            wire_bytes=1,
            compressed=False,
        )
    with pytest.raises(ValueError):
        e12.efficiency_budget(
            cfg,
            display_fps=10.0,
            expected_frames=0,
            payload_bytes=1,
            wire_bytes=1,
            compressed=False,
        )


# ---------------------------------------------------------------------------
# Parsing and coverage
# ---------------------------------------------------------------------------


def test_brightness_parser_never_invents_a_value() -> None:
    assert e12._parse_brightness(
        "start=0.650; end=0.650 (DisplayServicesGetBrightness fraction 0..1)"
    ) == pytest.approx(0.65)
    assert e12._parse_brightness("0.90") == pytest.approx(0.90)
    assert e12._parse_brightness("not measured (macOS default)") is None
    assert e12._parse_brightness("") is None
    # Percentages are not controller fractions and must not be guessed.
    assert e12._parse_brightness("100%, True Tone off") is None
    assert e12._parse_brightness("50% brightness") is None


def _factor(value, status, unit="") -> dict[str, object]:
    return {"value": value, "status": status, "unit": unit}


def _row(**factors) -> dict[str, object]:
    base = {
        "distance_mm": _factor(None, "UNMEASURED", "mm"),
        "angle_deg": _factor(None, "UNMEASURED", "deg"),
        "ambient_lux": _factor(None, "UNMEASURED", "lux"),
        "display_brightness_fraction": _factor(
            None, "UNMEASURED", "fraction"
        ),
        "lighting": _factor("indoor", "OPERATOR-RECORDED", "description"),
    }
    base.update(factors)
    return {"status": "ok", "factor": {"factors": base}}


def test_factor_coverage_separates_measured_from_unmeasured() -> None:
    rows = [
        _row(),
        _row(
            display_brightness_fraction=_factor(
                0.65, "MEASURED (DisplayServicesGetBrightness)", "fraction"
            ),
            lighting=_factor(
                "indoor, unchanged from baseline; illuminance not measured",
                "OPERATOR-RECORDED",
                "description",
            ),
        ),
        _row(
            display_brightness_fraction=_factor(
                0.90, "MEASURED (DisplayServicesGetBrightness)", "fraction"
            ),
            lighting=_factor(
                "indoor, unchanged from M9; illuminance not measured",
                "OPERATOR-RECORDED",
                "description",
            ),
        ),
    ]
    coverage = e12._factor_coverage(rows)
    assert coverage["display_brightness_fraction"]["varied"] is True
    assert coverage["display_brightness_fraction"]["measured"] is True
    assert coverage["display_brightness_fraction"]["values"] == [0.65, 0.9]
    # "indoor, ..." descriptions are the same nominal condition, and
    # illuminance was never measured.
    assert coverage["lighting"]["varied"] is False
    assert coverage["lighting"]["values"] == ["indoor"]
    assert set(coverage["unvaried"]) == {
        "distance_mm",
        "angle_deg",
        "ambient_lux",
        "lighting",
    }


# ---------------------------------------------------------------------------
# Evidence gates
# ---------------------------------------------------------------------------


def test_missing_session_is_blocked_and_invents_nothing(tmp_path) -> None:
    ctx = _context(tmp_path, [tmp_path / "does-not-exist"])
    e12.run(ctx)
    assert ctx.summary["status"] == "blocked"
    assert ctx.evidence_source == "BLOCKED / NO PHYSICAL CAPTURE"
    assert ctx.simulation_only is True
    assert ctx.device is None
    assert "BLOCKED" in ctx.conclusion
    assert len(ctx.trials) == 1


def _fixture_session(tmp_path):
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
    record = ingest_image(root, frame, source="fixture").to_dict()
    record.update(
        {
            "kind": "still",
            "frame": {"packet_id": 0, "frame_index": 0},
            "display_file": "display/p00_f000.png",
        }
    )
    add_captures(root, [record])
    finalize_session(root)
    return root


def test_fixture_session_is_never_analysed_as_physical(tmp_path) -> None:
    session = _fixture_session(tmp_path)
    ctx = _context(tmp_path / "run", [session])
    e12.run(ctx)
    assert ctx.summary["status"] == "blocked"
    assert ctx.evidence_source == "BLOCKED / NO PHYSICAL CAPTURE"
    assert "fixture" in ctx.summary["sessions"][0]["problems"][0]
