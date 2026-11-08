"""Typed, validated configuration and the canonical screen geometry.

All geometry is derived from a small number of parameters so that the
transmitter, the synthetic channel and the decoder cannot disagree about where
a triangle is.  The layout is serialised into experiment metadata.
"""

from __future__ import annotations

import dataclasses
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from .errors import ConfigError
from .types import PatternSet


# ---------------------------------------------------------------------------
# Canonical cell geometry (unit square, origin top-left)
# ---------------------------------------------------------------------------

# Triangle index: 0=top, 1=right, 2=bottom, 3=left.
TRIANGLE_UNIT: dict[int, tuple[tuple[float, float], ...]] = {
    0: ((0.0, 0.0), (1.0, 0.0), (0.5, 0.5)),
    1: ((1.0, 0.0), (1.0, 1.0), (0.5, 0.5)),
    2: ((1.0, 1.0), (0.0, 1.0), (0.5, 0.5)),
    3: ((0.0, 1.0), (0.0, 0.0), (0.5, 0.5)),
}

# Sampling point for each triangle, safely inside the triangle and far from
# the diagonal boundaries where blur mixes two colours.
TRIANGLE_CENTROID: dict[int, tuple[float, float]] = {
    0: (0.5, 1.0 / 6.0),
    1: (5.0 / 6.0, 0.5),
    2: (0.5, 5.0 / 6.0),
    3: (1.0 / 6.0, 0.5),
}

TRIANGLE_NAMES: tuple[str, ...] = ("top", "right", "bottom", "left")


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


@dataclass(frozen=True)
class Layout:
    """Pixel geometry of a canonical rendered screen."""

    canvas_w: int
    canvas_h: int
    cols: int
    rows: int
    cell_px: int
    gap_px: int
    margin_px: int
    fiducial_px: int
    border_px: int
    origin_x: int
    origin_y: int
    data_w: int
    data_h: int

    def cell_rect(self, row: int, col: int) -> Rect:
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            raise ConfigError(
                f"cell out of range row={row} col={col}",
                component="config",
                operation="cell_rect",
            )
        x = self.origin_x + col * (self.cell_px + self.gap_px)
        y = self.origin_y + row * (self.cell_px + self.gap_px)
        return Rect(x, y, self.cell_px, self.cell_px)

    def triangle_polygon(self, row: int, col: int, tri: int) -> tuple[tuple[float, float], ...]:
        r = self.cell_rect(row, col)
        return tuple((r.x + ux * r.w, r.y + uy * r.h) for ux, uy in TRIANGLE_UNIT[tri])

    def triangle_centroid(self, row: int, col: int, tri: int) -> tuple[float, float]:
        r = self.cell_rect(row, col)
        ux, uy = TRIANGLE_CENTROID[tri]
        return (r.x + ux * r.w, r.y + uy * r.h)

    def fiducial_rects(self) -> dict[str, Rect]:
        f = self.fiducial_px
        g = self.gap_px
        return {
            "tl": Rect(self.origin_x - f - g, self.origin_y - f - g, f, f),
            "tr": Rect(self.origin_x + self.data_w + g, self.origin_y - f - g, f, f),
            "bl": Rect(self.origin_x - f - g, self.origin_y + self.data_h + g, f, f),
            "br": Rect(self.origin_x + self.data_w + g, self.origin_y + self.data_h + g, f, f),
        }

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def compute_layout(cfg: "ScreenConfig") -> Layout:
    usable_w = cfg.canvas_width - 2 * cfg.margin_px
    usable_h = cfg.canvas_height - 2 * cfg.margin_px
    cell_w = (usable_w - (cfg.cols - 1) * cfg.gap_px) / cfg.cols
    cell_h = (usable_h - (cfg.rows - 1) * cfg.gap_px) / cfg.rows
    cell_px = int(math.floor(min(cell_w, cell_h)))
    if cell_px < 8:
        raise ConfigError(
            "cell size too small; increase canvas or reduce margins/gaps",
            component="config",
            operation="compute_layout",
            cell_px=cell_px,
        )
    data_w = cfg.cols * cell_px + (cfg.cols - 1) * cfg.gap_px
    data_h = cfg.rows * cell_px + (cfg.rows - 1) * cfg.gap_px
    origin_x = (cfg.canvas_width - data_w) // 2
    origin_y = (cfg.canvas_height - data_h) // 2
    return Layout(
        canvas_w=cfg.canvas_width,
        canvas_h=cfg.canvas_height,
        cols=cfg.cols,
        rows=cfg.rows,
        cell_px=cell_px,
        gap_px=cfg.gap_px,
        margin_px=cfg.margin_px,
        fiducial_px=cfg.fiducial_px,
        border_px=cfg.border_px,
        origin_x=origin_x,
        origin_y=origin_y,
        data_w=data_w,
        data_h=data_h,
    )


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScreenConfig:
    canvas_width: int = 1080
    canvas_height: int = 1350
    cols: int = 6
    rows: int = 5
    gap_px: int = 8
    margin_px: int = 90
    fiducial_px: int = 48
    border_px: int = 10
    supersample: int = 4
    background: int = 255
    foreground: int = 0
    gap_level: int = 255

    def __post_init__(self) -> None:
        if self.cols * self.rows != 30:
            raise ConfigError(
                "the proposed protocol requires exactly 30 cells",
                component="config",
                operation="ScreenConfig",
                cols=self.cols,
                rows=self.rows,
            )
        if self.supersample < 1:
            raise ConfigError("supersample must be >= 1", component="config")


@dataclass(frozen=True)
class ProtocolConfig:
    """Frame arithmetic for the 30-cell / 4-bit-per-cell proposal."""

    cols: int = 6
    rows: int = 5
    bits_per_cell: int = 4
    header_bits: int = 16          # 4-bit packet id + 12-bit frame index
    crc_bits: int = 16             # CRC-16/CCITT over header+data
    data_bytes_per_frame: int = 11
    packet_frames: int = 255       # 255 * 11 == 11 * 255 (exact RS alignment)
    blocks_per_packet: int = 11
    rs_nsym: int = 32              # RS(255,223): 16 errors or 32 erasures
    pattern_set: PatternSet = PatternSet.FULL16

    def __post_init__(self) -> None:
        total_bits = self.cols * self.rows * self.bits_per_cell
        if total_bits != 120:
            raise ConfigError(
                "proposed frame must carry 120 raw bits",
                component="config",
                operation="ProtocolConfig",
                total_bits=total_bits,
            )
        payload_bits = total_bits - self.header_bits - self.crc_bits
        if payload_bits != self.data_bytes_per_frame * 8:
            raise ConfigError(
                "frame payload arithmetic mismatch",
                component="config",
                operation="ProtocolConfig",
                payload_bits=payload_bits,
                data_bytes=self.data_bytes_per_frame,
            )
        if self.packet_frames * self.data_bytes_per_frame != self.blocks_per_packet * 255:
            raise ConfigError(
                "packet frames do not align with RS blocks",
                component="config",
                operation="ProtocolConfig",
                frames=self.packet_frames,
                data_bytes=self.data_bytes_per_frame,
                blocks=self.blocks_per_packet,
            )
        if not 0 < self.rs_nsym < 255:
            raise ConfigError("rs_nsym must be in 1..254", component="config")

    @property
    def total_bits(self) -> int:
        return self.cols * self.rows * self.bits_per_cell

    @property
    def payload_bits(self) -> int:
        return self.total_bits - self.header_bits - self.crc_bits

    @property
    def payload_bytes(self) -> int:
        return self.data_bytes_per_frame


@dataclass(frozen=True)
class ChannelConfig:
    """Synthetic optical channel.  Every value is a *simulation* parameter."""

    blur_sigma: float = 0.0
    motion_blur_px: int = 0
    motion_angle_deg: float = 0.0
    noise_sigma: float = 0.0
    ambient: float = 0.0
    brightness: float = 1.0
    gamma: float = 1.0
    vignette: float = 0.0
    perspective: float = 0.0
    jpeg_quality: int = 100
    seed: int = 0

    def __post_init__(self) -> None:
        if self.brightness < 0:
            raise ConfigError("brightness must be >= 0", component="config")
        if self.jpeg_quality < 1 or self.jpeg_quality > 100:
            raise ConfigError("jpeg_quality must be 1..100", component="config")


@dataclass(frozen=True)
class CameraConfig:
    width: int = 1080
    height: int = 1350
    fps: float = 30.0
    row_time_us: float = 20.0
    exposure_us: float = 8000.0
    display_fps: float = 60.0
    readout_direction: int = 1       # +1 top->bottom, -1 bottom->top
    assume_cropped: bool = True
    random_phase: bool = True

    def __post_init__(self) -> None:
        if self.fps <= 0:
            raise ConfigError("fps must be > 0", component="config")
        if self.row_time_us <= 0:
            raise ConfigError("row_time_us must be > 0", component="config")
        if self.exposure_us <= 0:
            raise ConfigError("exposure_us must be > 0", component="config")
        if self.display_fps <= 0:
            raise ConfigError("display_fps must be > 0", component="config")
        if self.readout_direction not in (-1, 1):
            raise ConfigError("readout_direction must be -1 or +1", component="config")

    @property
    def symbol_period_us(self) -> float:
        return 1e6 / self.display_fps

    @property
    def readout_us(self) -> float:
        return self.height * self.row_time_us


@dataclass(frozen=True)
class ReceiverConfig:
    sample_radius_px: int = 6
    min_contrast: float = 0.08
    threshold: float = 0.5
    assume_cropped: bool = True
    use_inversion_pair: bool = False
    detection_min_area_fraction: float = 0.15
    # A cell may set its own black/white threshold only when its contrast is a
    # meaningful fraction of the frame's black-to-white span.  Camera noise in
    # a solid cell is easily 8% of 255, so the old absolute trigger turned
    # sensor noise into a false triangle.  A real cell that contains both
    # triangle colours spans most of the frame range and passes this test.
    local_threshold_fraction: float = 0.5

    def __post_init__(self) -> None:
        if self.sample_radius_px < 1:
            raise ConfigError("sample_radius_px must be >= 1", component="config")
        if not 0.0 < self.local_threshold_fraction <= 1.0:
            raise ConfigError(
                "local_threshold_fraction must be in (0, 1]",
                component="config",
            )


@dataclass(frozen=True)
class ECCConfig:
    nsym: int = 32
    interleave: bool = True

    def __post_init__(self) -> None:
        if not 0 < self.nsym < 255:
            raise ConfigError("nsym must be in 1..254", component="config")


@dataclass(frozen=True)
class CompressionConfig:
    enabled: bool = True
    min_match: int = 4
    window: int = 65535
    max_literal: int = 255
    use_invert_op: bool = True

    def __post_init__(self) -> None:
        if self.min_match < 3:
            raise ConfigError("min_match must be >= 3", component="config")
        if not 1 <= self.window <= 65535:
            raise ConfigError("window must be 1..65535", component="config")


@dataclass(frozen=True)
class ExperimentConfig:
    screen: ScreenConfig = field(default_factory=ScreenConfig)
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    channel: ChannelConfig = field(default_factory=ChannelConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    receiver: ReceiverConfig = field(default_factory=ReceiverConfig)
    ecc: ECCConfig = field(default_factory=ECCConfig)
    compression: CompressionConfig = field(default_factory=CompressionConfig)
    seed: int = 20261108
    quick: bool = False

    def layout(self) -> Layout:
        return compute_layout(self.screen)


# ---------------------------------------------------------------------------
# JSON (de)serialisation without an extra dependency
# ---------------------------------------------------------------------------


def _convert(value: Any, typ: Any) -> Any:
    if typ is Any or typ is None:
        return value
    origin = get_origin(typ)
    if origin is not None:
        args = get_args(typ)
        # Optional[T] / Union[T, None]
        if origin is type(None):
            return value
        if args and args[0] is type(None):
            return None if value is None else _convert(value, args[0])
        return value
    if isinstance(typ, type) and issubclass(typ, Enum):
        return typ(value)
    if dataclasses.is_dataclass(typ) and isinstance(value, dict):
        return dataclass_from_dict(typ, value)
    return value


def dataclass_from_dict(cls: type, data: dict[str, Any]) -> Any:
    if not isinstance(data, dict):
        raise ConfigError("configuration must be a JSON object", component="config")
    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(cls):
        if f.name in data:
            kwargs[f.name] = _convert(data[f.name], hints.get(f.name, Any))
    try:
        return cls(**kwargs)
    except TypeError as exc:
        raise ConfigError(
            f"cannot construct {cls.__name__}: {exc}",
            component="config",
            operation="dataclass_from_dict",
        ) from exc


def config_to_dict(cfg: Any) -> dict[str, Any]:
    def encode(obj: Any) -> Any:
        if dataclasses.is_dataclass(obj):
            return {f.name: encode(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, dict):
            return {k: encode(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [encode(v) for v in obj]
        return obj

    return encode(cfg)


def load_config(path: str | Path) -> ExperimentConfig:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(
            f"cannot read configuration: {exc}",
            component="config",
            operation="load_config",
            path=str(p),
        ) from exc
    return dataclass_from_dict(ExperimentConfig, data)


def save_config(cfg: ExperimentConfig, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config_to_dict(cfg), indent=2, sort_keys=True) + "\n", encoding="utf-8")
