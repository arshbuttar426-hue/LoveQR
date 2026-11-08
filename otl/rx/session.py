"""Physical capture sessions: metadata, preservation and validation.

A session is the unit of physical evidence.  It lives under
``datasets/physical/<session_id>/`` and contains:

``session.json``
    Device, display, geometry, capture settings, transmitter fingerprint and
    the list of captures.
``display/``
    The exact PNG frames that were shown, plus ``player_manifest.json``.
``captures/originals/``
    Camera files copied byte-for-byte (JPEG, HEIC, MOV, ...).
``captures/derived/``
    Lossless PNG conversions used only when the decoder cannot read the
    original; both hashes are recorded.
``captures/index.json`` / ``index.jsonl``
    Machine-readable capture records; the JSONL log is append-only.

Nothing here decodes an image.  The experiment layer does that, so a session
can be captured once and re-analysed after a decoder change.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..errors import CaptureError

SCHEMA = "otl-session/1"
CAPTURE_SOURCES = ("camera", "manual-import", "fixture")
EVIDENCE_PHYSICAL = "PHYSICAL / CAMERA CAPTURE"


# ---------------------------------------------------------------------------
# Metadata blocks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceInfo:
    model: str = ""
    os: str = ""
    camera: str = ""
    serial: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DisplayInfo:
    model: str = ""
    kind: str = "phone"
    width_px: int | None = None
    height_px: int | None = None
    refresh_hz: float | None = None
    brightness: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeometryInfo:
    distance_mm: float | None = None
    angle_deg: float | None = None
    ambient_lux: float | None = None
    lighting: str = ""
    hand_held: bool | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CaptureSettings:
    mode: str = "photo"
    resolution: str = ""
    fps: float | None = None
    exposure: str = ""
    iso: str = ""
    focus: str = ""
    zoom: str = ""
    stabilization: str = ""
    format: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Session:
    schema: str
    session_id: str
    created_utc: str
    status: str
    capture_source: str
    device: DeviceInfo
    display: DisplayInfo
    geometry: GeometryInfo
    capture: CaptureSettings
    transmitter: dict[str, Any] = field(default_factory=dict)
    captures: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    evidence_source: str = "BLOCKED / NO PHYSICAL CAPTURE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "session_id": self.session_id,
            "created_utc": self.created_utc,
            "status": self.status,
            "capture_source": self.capture_source,
            "device": self.device.to_dict(),
            "display": self.display.to_dict(),
            "geometry": self.geometry.to_dict(),
            "capture": self.capture.to_dict(),
            "transmitter": self.transmitter,
            "captures": self.captures,
            "notes": self.notes,
            "evidence_source": self.evidence_source,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Session":
        if payload.get("schema") != SCHEMA:
            raise CaptureError(
                "not an OTL capture session",
                component="rx",
                operation="load_session",
                schema=payload.get("schema"),
            )
        return cls(
            schema=payload["schema"],
            session_id=payload["session_id"],
            created_utc=payload.get("created_utc", ""),
            status=payload.get("status", "draft"),
            capture_source=payload.get("capture_source", "camera"),
            device=DeviceInfo(**payload.get("device", {})),
            display=DisplayInfo(**payload.get("display", {})),
            geometry=GeometryInfo(**payload.get("geometry", {})),
            capture=CaptureSettings(**payload.get("capture", {})),
            transmitter=payload.get("transmitter", {}),
            captures=payload.get("captures", []),
            notes=payload.get("notes", ""),
            evidence_source=payload.get("evidence_source", "BLOCKED / NO PHYSICAL CAPTURE"),
        )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def session_dir(path: Path | str) -> Path:
    candidate = Path(path)
    if candidate.is_file() and candidate.name == "session.json":
        return candidate.parent
    return candidate


def load_session(path: Path | str) -> Session:
    root = session_dir(path)
    manifest = root / "session.json"
    if not manifest.is_file():
        raise CaptureError(
            "session.json is missing",
            component="rx",
            operation="load_session",
            path=str(root),
        )
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CaptureError(
            "session.json is not valid JSON",
            component="rx",
            operation="load_session",
            path=str(manifest),
        ) from exc
    return Session.from_dict(payload)


def save_session(path: Path | str, session: Session) -> Path:
    root = session_dir(path)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "session.json", session.to_dict())
    return root / "session.json"


def new_session(
    root: Path | str,
    session_id: str,
    *,
    device: DeviceInfo | None = None,
    display: DisplayInfo | None = None,
    geometry: GeometryInfo | None = None,
    capture: CaptureSettings | None = None,
    capture_source: str = "camera",
    notes: str = "",
) -> Path:
    """Create a fresh session directory.  An existing directory is refused."""
    if capture_source not in CAPTURE_SOURCES:
        raise CaptureError(
            "unknown capture_source",
            component="rx",
            operation="new_session",
            capture_source=capture_source,
            allowed=list(CAPTURE_SOURCES),
        )
    if not session_id or "/" in session_id or "\\" in session_id:
        raise CaptureError(
            "session_id must be a single path component",
            component="rx",
            operation="new_session",
            session_id=session_id,
        )
    base = Path(root)
    target = base / session_id
    if target.exists():
        raise CaptureError(
            "session directory already exists",
            component="rx",
            operation="new_session",
            path=str(target),
        )
    for directory in (
        target / "display",
        target / "captures" / "originals",
        target / "captures" / "derived",
        target / "captures" / "frames",
    ):
        directory.mkdir(parents=True, exist_ok=False)
    session = Session(
        schema=SCHEMA,
        session_id=session_id,
        created_utc=_utc_now(),
        status="draft",
        capture_source=capture_source,
        device=device or DeviceInfo(),
        display=display or DisplayInfo(),
        geometry=geometry or GeometryInfo(),
        capture=capture or CaptureSettings(),
        transmitter={},
        captures=[],
        notes=notes,
        evidence_source="BLOCKED / NO PHYSICAL CAPTURE",
    )
    save_session(target, session)
    (target / "README.md").write_text(
        f"# Capture session `{session_id}`\n\n"
        "This directory is the unit of physical evidence. Do not edit or delete\n"
        "files after `session.lock.json` exists. See `docs/PHYSICAL_CAPTURE.md`.\n",
        encoding="utf-8",
    )
    return target


# ---------------------------------------------------------------------------
# Transmitter attachment
# ---------------------------------------------------------------------------


def attach_transmitter(
    path: Path | str,
    frames_dir: Path | str,
    player_manifest: Path | str,
    *,
    payload_name: str = "",
    payload_sha256: str = "",
) -> dict[str, Any]:
    """Copy the exact displayed frames and player manifest into the session."""
    root = session_dir(path)
    session = load_session(root)
    if session.status == "final":
        raise CaptureError(
            "session is locked",
            component="rx",
            operation="attach_transmitter",
            path=str(root),
        )
    source_frames = Path(frames_dir)
    manifest_path = Path(player_manifest)
    if not manifest_path.is_file():
        raise CaptureError(
            "player manifest is missing",
            component="rx",
            operation="attach_transmitter",
            path=str(manifest_path),
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    display_dir = root / "display"
    display_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, Any]] = []
    for record in manifest.get("frames", []):
        name = record.get("file")
        if not name:
            continue
        source = source_frames / name
        if not source.is_file():
            raise CaptureError(
                "display frame referenced by the manifest is missing",
                component="rx",
                operation="attach_transmitter",
                frame=name,
            )
        target = display_dir / name
        if target.exists():
            raise CaptureError(
                "refusing to overwrite a display frame",
                component="rx",
                operation="attach_transmitter",
                frame=name,
            )
        shutil.copy2(source, target)
        digest = _sha256_file(target)
        if digest != record.get("sha256"):
            raise CaptureError(
                "display frame hash does not match the player manifest",
                component="rx",
                operation="attach_transmitter",
                frame=name,
            )
        copied.append({"file": name, "sha256": digest})
    target_manifest = display_dir / "player_manifest.json"
    if target_manifest.exists():
        raise CaptureError(
            "refusing to overwrite player_manifest.json",
            component="rx",
            operation="attach_transmitter",
        )
    shutil.copy2(manifest_path, target_manifest)
    session.transmitter = {
        "player_manifest": "display/player_manifest.json",
        "player_manifest_sha256": _sha256_file(target_manifest),
        "frames_sha256": manifest.get("frames_sha256"),
        "fps": manifest.get("fps"),
        "hold": manifest.get("hold"),
        "frame_count": len(copied),
        "payload_name": payload_name,
        "payload_sha256": payload_sha256,
        "attached_utc": _utc_now(),
    }
    save_session(root, session)
    return session.transmitter


# ---------------------------------------------------------------------------
# Captures
# ---------------------------------------------------------------------------


def _normalise_capture(record: dict[str, Any]) -> dict[str, Any]:
    required = ("path", "sha256")
    missing = [key for key in required if not record.get(key)]
    if missing:
        raise CaptureError(
            "capture record is incomplete",
            component="rx",
            operation="add_captures",
            missing=missing,
        )
    normalised = dict(record)
    normalised.setdefault("kind", "still")
    normalised.setdefault("decode_path", record["path"])
    normalised.setdefault("original_path", None)
    normalised.setdefault("original_sha256", None)
    normalised.setdefault("width", None)
    normalised.setdefault("height", None)
    normalised.setdefault("frame", None)
    normalised.setdefault("display_file", None)
    normalised.setdefault("captured_utc", None)
    normalised.setdefault("pos_msec", None)
    normalised.setdefault("notes", "")
    return normalised


def add_captures(
    path: Path | str,
    records: Iterable[dict[str, Any]],
    *,
    kind: str = "still",
    notes: str = "",
) -> list[dict[str, Any]]:
    """Append capture records to the session and to an append-only JSONL log."""
    root = session_dir(path)
    session = load_session(root)
    if session.status == "final":
        raise CaptureError(
            "session is locked",
            component="rx",
            operation="add_captures",
            path=str(root),
        )
    normalised = []
    for record in records:
        item = _normalise_capture(record)
        item["kind"] = record.get("kind", kind)
        if notes and not item.get("notes"):
            item["notes"] = notes
        file_path = root / item["path"]
        if not file_path.is_file():
            raise CaptureError(
                "capture file is missing",
                component="rx",
                operation="add_captures",
                path=item["path"],
            )
        actual = _sha256_file(file_path)
        if actual != item["sha256"]:
            raise CaptureError(
                "capture hash does not match the file",
                component="rx",
                operation="add_captures",
                path=item["path"],
            )
        normalised.append(item)

    index_path = root / "captures" / "index.json"
    existing: list[dict[str, Any]] = []
    if index_path.is_file():
        existing = json.loads(index_path.read_text(encoding="utf-8")).get("captures", [])
    combined = existing + normalised
    _write_json(
        index_path,
        {
            "schema": "otl-captures/1",
            "session_id": session.session_id,
            "updated_utc": _utc_now(),
            "captures": combined,
        },
    )
    log_path = root / "captures" / "index.jsonl"
    with log_path.open("a", encoding="utf-8") as handle:
        for item in normalised:
            handle.write(json.dumps(item, sort_keys=True, default=str) + "\n")
    session.captures = combined
    save_session(root, session)
    return normalised


def load_captures(path: Path | str) -> list[dict[str, Any]]:
    root = session_dir(path)
    index_path = root / "captures" / "index.json"
    if index_path.is_file():
        return json.loads(index_path.read_text(encoding="utf-8")).get("captures", [])
    return load_session(root).captures


# ---------------------------------------------------------------------------
# Validation and locking
# ---------------------------------------------------------------------------


def validate_session(path: Path | str) -> list[str]:
    """Return a list of problems; an empty list means the session is usable."""
    root = session_dir(path)
    problems: list[str] = []
    try:
        session = load_session(root)
    except CaptureError as exc:
        return [f"cannot load session: {exc.message}"]
    if session.capture_source not in CAPTURE_SOURCES:
        problems.append(f"unknown capture_source {session.capture_source!r}")
    if not session.device.model:
        problems.append("device.model is empty")
    if not session.display.model:
        problems.append("display.model is empty")
    if session.capture_source in {"camera", "manual-import"}:
        if not session.capture.mode:
            problems.append("capture.mode is empty")
        if not session.capture.resolution:
            problems.append("capture.resolution is empty")
    if not session.transmitter:
        problems.append("transmitter is not attached")
    elif not (root / session.transmitter.get("player_manifest", "")).is_file():
        problems.append("transmitter player manifest is missing")
    captures = load_captures(root)
    if not captures:
        problems.append("no captures recorded")
    for record in captures:
        for key in ("path", "decode_path"):
            value = record.get(key)
            if value and not (root / value).is_file():
                problems.append(f"capture file is missing: {value}")
        if record.get("frame") is not None:
            frame = record["frame"]
            if not isinstance(frame, dict) or "packet_id" not in frame or "frame_index" not in frame:
                problems.append(f"invalid ground-truth frame on {record.get('path')}")
    return problems


def require_valid_session(path: Path | str) -> Session:
    problems = validate_session(path)
    if problems:
        raise CaptureError(
            "capture session is not valid",
            component="rx",
            operation="validate_session",
            problems=problems,
        )
    return load_session(path)


def finalize_session(path: Path | str) -> dict[str, Any]:
    """Lock a validated session and fingerprint everything it contains."""
    root = session_dir(path)
    session = load_session(root)
    if session.status == "final":
        raise CaptureError(
            "session is already final",
            component="rx",
            operation="finalize_session",
            path=str(root),
        )
    problems = validate_session(root)
    if problems:
        raise CaptureError(
            "cannot finalize an invalid session",
            component="rx",
            operation="finalize_session",
            problems=problems,
        )
    captures = load_captures(root)
    capture_rows = [
        f"{record.get('path')}:{record.get('sha256')}" for record in captures
    ]
    if session.capture_source in {"camera", "manual-import"}:
        session.evidence_source = EVIDENCE_PHYSICAL
    elif session.capture_source == "fixture":
        session.evidence_source = "SOFTWARE FIXTURE (NOT PHYSICAL)"
    lock = {
        "schema": "otl-session-lock/1",
        "session_id": session.session_id,
        "locked_utc": _utc_now(),
        "manifest_sha256": _sha256_bytes(
            json.dumps(session.to_dict(), sort_keys=True, default=str).encode("utf-8")
        ),
        "captures_sha256": _sha256_bytes("\n".join(sorted(capture_rows)).encode("utf-8")),
        "capture_count": len(captures),
        "evidence_source": session.evidence_source,
    }
    _write_json(root / "session.lock.json", lock)
    session.status = "final"
    save_session(root, session)
    return lock


def list_sessions(root: Path | str) -> list[dict[str, Any]]:
    base = Path(root)
    rows: list[dict[str, Any]] = []
    if not base.is_dir():
        return rows
    for candidate in sorted(base.iterdir()):
        manifest = candidate / "session.json"
        if not manifest.is_file():
            continue
        try:
            session = load_session(candidate)
        except CaptureError:
            continue
        rows.append(
            {
                "session_id": session.session_id,
                "path": str(candidate),
                "status": session.status,
                "capture_source": session.capture_source,
                "device": session.device.model,
                "display": session.display.model,
                "captures": len(load_captures(candidate)),
                "evidence_source": session.evidence_source,
            }
        )
    return rows


def newest_session(root: Path | str) -> Path | None:
    base = Path(root)
    candidates = [
        candidate
        for candidate in base.iterdir()
        if candidate.is_dir() and (candidate / "session.json").is_file()
    ] if base.is_dir() else []
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.name, reverse=True)
    return candidates[0]
