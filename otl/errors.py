"""Structured errors used across every OTL layer.

Every failure that can be caused by data, configuration or a physical channel
is represented by a subclass of :class:`OTLError` with a stable machine code.
Callers must not rely on exception text, only on ``code`` and ``details``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorContext:
    component: str = "core"
    operation: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class OTLError(Exception):
    """Base class for all expected OTL failures."""

    code = "E_OTL"

    def __init__(
        self,
        message: str,
        *,
        component: str = "core",
        operation: str = "",
        **details: Any,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.component = component
        self.operation = operation
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "component": self.component,
            "operation": self.operation,
            "details": self.details,
        }

    def __str__(self) -> str:  # pragma: no cover - formatting only
        ctx = f"{self.component}.{self.operation}" if self.operation else self.component
        extra = f" {self.details}" if self.details else ""
        return f"[{self.code}] {ctx}: {self.message}{extra}"


class ConfigError(OTLError):
    code = "E_CONFIG"


class ProtocolError(OTLError):
    code = "E_PROTOCOL"


class FrameFormatError(OTLError):
    code = "E_FRAME_FORMAT"


class CRCError(OTLError):
    code = "E_CRC"


class DetectionError(OTLError):
    code = "E_DETECT"


class SyncError(OTLError):
    code = "E_SYNC"


class DecodeError(OTLError):
    code = "E_DECODE"


class ECCError(OTLError):
    code = "E_ECC"


class CompressionError(OTLError):
    code = "E_COMPRESSION"


class ChannelError(OTLError):
    code = "E_CHANNEL"


class ReconstructionError(OTLError):
    code = "E_RECONSTRUCT"


class MeasurementError(OTLError):
    code = "E_MEASUREMENT"


class CaptureError(OTLError):
    code = "E_CAPTURE"


class UnsupportedFeatureError(OTLError):
    code = "E_UNSUPPORTED"
