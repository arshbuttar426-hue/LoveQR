"""Synchronisation facade tests: separate spatial and temporal locks."""

from __future__ import annotations

from otl.config import ExperimentConfig
from otl.protocol.blink import encode_word
from otl.protocol.frame import pack_frame
from otl.rx.sync import spatial_sync, sync_manifest, temporal_sync
from otl.tx.renderer import render_frame
from otl.types import FrameHeader


def test_spatial_sync_locks_on_rendered_frame() -> None:
    cfg = ExperimentConfig()
    cells = pack_frame(FrameHeader(1, 2), bytes(range(11)), cfg.protocol)
    image = render_frame(cells, cfg.layout(), cfg.screen)
    sync = spatial_sync(image, cfg.layout(), cfg.receiver)
    assert sync.locked
    assert sync.confidence > 0.5
    assert sync.to_dict()["method"] == "components"


def test_temporal_sync_locks_on_blink_word() -> None:
    bits = encode_word(2)
    values = [240.0 if bit else 10.0 for bit in bits]
    sync = temporal_sync(values)
    assert sync.locked
    assert sync.id_index == 2
    assert sync.score > 0.7


def test_temporal_sync_reports_no_lock_on_noise() -> None:
    sync = temporal_sync([128.0] * 26)
    assert not sync.locked
    assert sync.id_index is None


def test_sync_manifest_describes_both_locks() -> None:
    manifest = sync_manifest()
    assert "fiducials" in str(manifest["spatial"])
    assert "Barker" in str(manifest["temporal"])
