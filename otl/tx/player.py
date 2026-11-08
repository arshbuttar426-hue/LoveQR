"""Deterministic full-screen player for rendered OTL frames.

The player is the *transmitter interface*.  It is a single HTML file that shows
the PNG frames produced by :mod:`otl.tx.renderer` on a phone, tablet or monitor
at a fixed display rate, with no browser chrome and no scaling artefacts.

Two modes matter for physical work:

``play``
    Frames advance on a ``performance.now()`` schedule.  The schedule is derived
    from the wall clock, not from ``requestAnimationFrame`` callbacks, so a
    dropped animation frame skips a symbol instead of slowing the stream down.

``hold``
    One frame is displayed indefinitely (``?frame=N`` or ``--hold``).  This is
    the reliable mode for still-photo capture: the operator knows exactly which
    frame is on screen for every photograph.

The generated file embeds the PNGs as data URIs by default, so it can be copied
to a phone or opened from a USB stick without a web server.  A sidecar
``player_manifest.json`` records the frame order, SHA-256 of every PNG and the
display rate; that manifest is the ground truth for a physical session.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from .. import __version__
from ..errors import OTLError

FRAME_RE = re.compile(r"p(?P<packet>\d+)_f(?P<frame>\d+)\.png$")


@dataclass(frozen=True)
class PlayerConfig:
    """Display parameters for the transmitter page."""

    fps: float = 60.0
    loop: bool = True
    hold: bool = False
    embed: bool = True
    title: str = "OTL transmitter"
    start_delay_s: float = 1.0
    show_hud: bool = False
    autostart: bool = False
    background: str = "#000000"

    def __post_init__(self) -> None:
        if self.fps <= 0:
            raise OTLError(
                "fps must be positive",
                component="tx",
                operation="PlayerConfig",
                fps=self.fps,
            )
        if self.start_delay_s < 0:
            raise OTLError(
                "start_delay_s must be >= 0",
                component="tx",
                operation="PlayerConfig",
                start_delay_s=self.start_delay_s,
            )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _frame_record(path: Path, index: int) -> dict[str, Any]:
    data = path.read_bytes()
    match = FRAME_RE.search(path.name)
    record: dict[str, Any] = {
        "index": index,
        "file": path.name,
        "sha256": _sha256(data),
        "bytes": len(data),
    }
    if match:
        record["packet_id"] = int(match.group("packet"))
        record["frame_index"] = int(match.group("frame"))
    return record


def _mime(path: Path) -> str:
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"


def _data_uri(path: Path) -> str:
    return f"data:{_mime(path)};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; background: {background}; overflow: hidden; }}
  #stage {{ position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; }}
  #frame {{ width: 100%; height: 100%; object-fit: contain; image-rendering: pixelated; }}
  #hud {{ position: fixed; left: 10px; top: 10px; z-index: 20; display: {hud_display};
         color: #00ff66; background: rgba(0,0,0,.55); font: 12px/1.4 ui-monospace, monospace;
         padding: 4px 7px; border-radius: 4px; white-space: pre; pointer-events: none; }}
  #curtain {{ position: fixed; inset: 0; z-index: 30; display: flex; flex-direction: column;
             align-items: center; justify-content: center; gap: 14px; background: #000; color: #fff;
             font: 16px/1.5 -apple-system, system-ui, sans-serif; text-align: center; padding: 24px; }}
  #curtain h1 {{ font-size: 20px; margin: 0; font-weight: 600; }}
  #curtain p {{ margin: 0; max-width: 34em; color: #bbb; }}
  #curtain button {{ font: 16px -apple-system, system-ui, sans-serif; padding: 12px 22px;
                     border: 0; border-radius: 10px; background: #fff; color: #000; cursor: pointer; }}
  #curtain small {{ color: #777; }}
  body.running #curtain {{ display: none; }}
</style>
</head>
<body>
<div id="stage"><img id="frame" alt="OTL frame"></div>
<div id="hud"></div>
<div id="curtain">
  <h1>{title}</h1>
  <p>{count} frame(s) at {fps} fps. Press Start, then allow full screen. Keep the
     screen at full brightness and do not let it sleep.</p>
  <button id="start" autofocus>Start</button>
  <small>space = start/pause &nbsp;·&nbsp; ←/→ = step &nbsp;·&nbsp; f = full screen &nbsp;·&nbsp; h = HUD</small>
</div>
<script>
const FRAMES = {frames};
const META = {meta};
const img = document.getElementById('frame');
const hud = document.getElementById('hud');
const curtain = document.getElementById('curtain');
const params = new URLSearchParams(location.search);
const N = FRAMES.length;
const fps = Math.max(0.1, parseFloat(params.get('fps') || META.fps));
const loop = params.has('loop') ? params.get('loop') !== '0' : META.loop;
const holdParam = params.get('frame');
const stepMode = params.has('step') || holdParam !== null;
const hudOn = params.has('hud') ? params.get('hud') !== '0' : META.show_hud;
let idx = holdParam !== null ? Math.max(0, Math.min(N - 1, parseInt(holdParam, 10) || 0)) : 0;
let playing = false, paused = false, start = 0, last = -1;

function show(i) {{
  idx = ((i % N) + N) % N;
  img.src = FRAMES[idx];
  hud.textContent = `frame ${{idx + 1}}/${{N}}\\n${{META.frames[idx].file}}`;
}}
function tick(now) {{
  if (!playing) return;
  if (!paused && !stepMode) {{
    const elapsed = now - start;
    const target = Math.floor(elapsed / (1000 / fps));
    if (target !== last) {{
      last = target;
      show(loop ? target : Math.min(target, N - 1));
      if (!loop && target >= N - 1) playing = false;
    }}
  }}
  requestAnimationFrame(tick);
}}
function begin() {{
  document.body.classList.add('running');
  if (document.documentElement.requestFullscreen) {{
    document.documentElement.requestFullscreen().catch(() => {{}});
  }}
  playing = true; paused = false;
  start = performance.now() + META.start_delay_s * 1000;
  last = -1;
  requestAnimationFrame(tick);
}}
document.getElementById('start').addEventListener('click', begin);
curtain.addEventListener('click', begin);
window.addEventListener('keydown', (e) => {{
  if (e.code === 'Space') {{ e.preventDefault(); if (!playing) begin(); else paused = !paused; }}
  else if (e.code === 'ArrowRight') {{ e.preventDefault(); show(idx + 1); }}
  else if (e.code === 'ArrowLeft') {{ e.preventDefault(); show(idx - 1); }}
  else if (e.key === 'f') {{ document.documentElement.requestFullscreen?.().catch(() => {{}}); }}
  else if (e.key === 'h') {{ hud.style.display = hud.style.display === 'none' ? 'block' : 'none'; }}
}});
hud.style.display = hudOn ? 'block' : 'none';
if (holdParam !== null) {{ show(idx); document.body.classList.add('running'); }}
else if (META.hold) {{ show(0); document.body.classList.add('running'); }}
else if (META.autostart) {{ begin(); }}
else {{ img.src = FRAMES[0]; }}
</script>
</body>
</html>
"""


def build_player(
    frames: Sequence[Path | str],
    out: Path | str,
    cfg: PlayerConfig | None = None,
) -> dict[str, Any]:
    """Write a self-contained player page plus a ground-truth manifest."""
    cfg = cfg or PlayerConfig()
    out_path = Path(out)
    frame_paths = [Path(item) for item in frames]
    if not frame_paths:
        raise OTLError(
            "no frames to play",
            component="tx",
            operation="build_player",
        )
    missing = [str(path) for path in frame_paths if not path.is_file()]
    if missing:
        raise OTLError(
            "frame files are missing",
            component="tx",
            operation="build_player",
            missing=missing[:5],
        )

    records = [_frame_record(path, index) for index, path in enumerate(frame_paths)]
    frames_payload: list[str] = []
    if cfg.embed:
        frames_payload = [_data_uri(path) for path in frame_paths]
    else:
        # Relative to the HTML file; the caller is responsible for keeping the
        # frame directory next to the player.
        frames_payload = [
            Path(__import__("os").path.relpath(path.resolve(), out_path.parent.resolve())).as_posix()
            for path in frame_paths
        ]

    manifest: dict[str, Any] = {
        "schema": "otl-player/1",
        "otl_version": __version__,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "title": cfg.title,
        "fps": cfg.fps,
        "loop": cfg.loop,
        "hold": cfg.hold,
        "embed": cfg.embed,
        "start_delay_s": cfg.start_delay_s,
        "show_hud": cfg.show_hud,
        "autostart": cfg.autostart,
        "frame_count": len(records),
        "frames": records,
        "frames_sha256": _sha256(
            "\n".join(f"{rec['index']}:{rec['sha256']}" for rec in records).encode("utf-8")
        ),
        "player_html_sha256": None,
    }

    meta = {
        "fps": cfg.fps,
        "loop": cfg.loop,
        "hold": cfg.hold,
        "start_delay_s": cfg.start_delay_s,
        "show_hud": cfg.show_hud,
        "autostart": cfg.autostart,
        "frames": records,
    }
    page = _HTML.format(
        title=html.escape(cfg.title),
        background=cfg.background,
        count=len(records),
        fps=cfg.fps,
        hud_display="block" if cfg.show_hud else "none",
        frames=json.dumps(frames_payload),
        meta=json.dumps(meta, sort_keys=True),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    manifest["player_html_sha256"] = _sha256(out_path.read_bytes())

    manifest_path = out_path.with_name(out_path.stem + "_manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "player": str(out_path),
        "manifest": str(manifest_path),
        "frames": len(records),
        "fps": cfg.fps,
        "embed": cfg.embed,
        "frames_sha256": manifest["frames_sha256"],
        "player_html_sha256": manifest["player_html_sha256"],
    }


def player_manifest(path: Path | str) -> dict[str, Any]:
    """Load and minimally validate a ``*_manifest.json`` sidecar."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != "otl-player/1":
        raise OTLError(
            "not an OTL player manifest",
            component="tx",
            operation="player_manifest",
            schema=payload.get("schema"),
        )
    return payload


def config_dict(cfg: PlayerConfig) -> dict[str, Any]:
    return asdict(cfg)
