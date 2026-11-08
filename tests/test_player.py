"""Tests for the deterministic HTML transmitter player."""

from __future__ import annotations

import json

import pytest

from otl.config import ExperimentConfig
from otl.errors import OTLError
from otl.tx.player import PlayerConfig, build_player, player_manifest
from otl.tx.renderer import render_frame, save_frame


def _frames(tmp_path, count: int = 3):
    cfg = ExperimentConfig()
    directory = tmp_path / "frames"
    directory.mkdir()
    paths = []
    for index in range(count):
        cells = [index % 16] * 30
        path = directory / f"p00_f{index:03d}.png"
        save_frame(str(path), render_frame(cells, cfg.layout(), cfg.screen))
        paths.append(path)
    return paths


def test_player_embeds_frames_and_writes_manifest(tmp_path) -> None:
    frames = _frames(tmp_path, 3)
    result = build_player(frames, tmp_path / "player.html", PlayerConfig(fps=30.0))
    page = (tmp_path / "player.html").read_text(encoding="utf-8")
    assert "data:image/png;base64," in page
    assert result["frames"] == 3
    manifest = player_manifest(result["manifest"])
    assert manifest["schema"] == "otl-player/1"
    assert manifest["fps"] == 30.0
    assert [record["frame_index"] for record in manifest["frames"]] == [0, 1, 2]
    assert all(len(record["sha256"]) == 64 for record in manifest["frames"])
    assert len(manifest["frames_sha256"]) == 64
    assert manifest["player_html_sha256"] == result["player_html_sha256"]


def test_player_can_reference_frames_without_embedding(tmp_path) -> None:
    frames = _frames(tmp_path, 2)
    result = build_player(
        frames, tmp_path / "player.html", PlayerConfig(embed=False, hold=True)
    )
    page = (tmp_path / "player.html").read_text(encoding="utf-8")
    assert "data:image/png;base64," not in page
    assert "frames/p00_f000.png" in page
    manifest = player_manifest(result["manifest"])
    assert manifest["embed"] is False
    assert manifest["hold"] is True


def test_player_rejects_missing_frames(tmp_path) -> None:
    with pytest.raises(OTLError) as info:
        build_player([tmp_path / "missing.png"], tmp_path / "player.html")
    assert info.value.code == "E_OTL"
    assert info.value.details["missing"]


def test_player_rejects_non_positive_fps(tmp_path) -> None:
    with pytest.raises(OTLError):
        PlayerConfig(fps=0)


def test_player_manifest_rejects_other_schema(tmp_path) -> None:
    path = tmp_path / "bad_manifest.json"
    path.write_text(json.dumps({"schema": "something/else"}), encoding="utf-8")
    with pytest.raises(OTLError):
        player_manifest(path)


def test_player_is_deterministic_except_timestamps(tmp_path) -> None:
    frames = _frames(tmp_path, 2)
    first = build_player(frames, tmp_path / "a.html", PlayerConfig())
    second = build_player(frames, tmp_path / "b.html", PlayerConfig())
    a = player_manifest(first["manifest"])
    b = player_manifest(second["manifest"])
    assert a["frames"] == b["frames"]
    assert a["frames_sha256"] == b["frames_sha256"]
    # The embedded page must be byte-identical for identical inputs.
    assert first["player_html_sha256"] == second["player_html_sha256"]
