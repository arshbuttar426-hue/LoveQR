"""CLI smoke tests: JSON output and exit codes."""

from __future__ import annotations

import json

from otl.cli import main


def test_manifest_command(capsys) -> None:
    assert main(["manifest"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["frame"]["total_bits"] == 120
    assert payload["packet"]["frames_per_packet"] == 255


def test_info_command(capsys) -> None:
    assert main(["info"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["cells"]["cols"] * payload["cells"]["rows"] == 30
    assert payload["display"]["symbol_period_us"] > 0


def test_render_then_decode(capsys, tmp_path) -> None:
    out = tmp_path / "frames"
    assert main(["render", "--text", "cli payload", "--out", str(out), "--limit", "1"]) == 0
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["frames_written"] == 1
    image = out / rendered["frames"][0]["file"]
    assert image.exists()

    assert main(["decode", str(image)]) == 0
    decoded = json.loads(capsys.readouterr().out)
    assert decoded["frame"]["crc_ok"] is True
    assert decoded["frame"]["data_hex"] == "4f00000000000000000000"


def test_selftest_command(capsys) -> None:
    assert main(["selftest"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert {check["check"] for check in payload["checks"]} == {
        "compression",
        "frame",
        "packet",
        "pipeline",
    }


def test_expected_error_is_json_on_stderr(capsys) -> None:
    assert main(["decode", "/nonexistent/frame.png"]) == 2
    err = json.loads(capsys.readouterr().err)
    assert err["code"] in {"E_IO", "E_CHANNEL"}


def test_play_command_builds_player(capsys, tmp_path) -> None:
    frames = tmp_path / "frames"
    assert main(["render", "--text", "play", "--out", str(frames), "--limit", "2"]) == 0
    capsys.readouterr()
    player = tmp_path / "player.html"
    assert main(
        [
            "play",
            str(frames),
            "--out",
            str(player),
            "--no-embed",
            "--hold",
            "--autostart",
            "--frame",
            "0",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["frames"] == 2
    assert player.is_file()
    assert (tmp_path / "player_manifest.json").is_file()
    assert "frames/p00_f000.png" in player.read_text(encoding="utf-8")


def test_session_commands_roundtrip(capsys, tmp_path) -> None:
    root = tmp_path / "sessions"
    assert main(
        [
            "session",
            "new",
            "s1",
            "--root",
            str(root),
            "--source",
            "fixture",
            "--device-model",
            "test camera",
            "--display-model",
            "test display",
        ]
    ) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["capture_source"] == "fixture"

    assert main(["session", "list", "--root", str(root)]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert [row["session_id"] for row in listed["sessions"]] == ["s1"]

    # A draft with no transmitter or captures is invalid and exits 3.
    assert main(["session", "validate", str(root / "s1")]) == 3
    validated = json.loads(capsys.readouterr().out)
    assert validated["valid"] is False
    assert validated["capture_source"] == "fixture"
