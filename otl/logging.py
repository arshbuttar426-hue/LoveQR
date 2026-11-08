"""Minimal structured JSON-lines logging.

The lab must be reproducible, so logs are machine-readable and never contain
timestamps that affect decoded values.  Wall-clock timestamps are present for
diagnostics only and are excluded from regression hashes.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, TextIO

_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}


class StructuredLogger:
    def __init__(
        self,
        component: str,
        level: str | None = None,
        stream: TextIO | None = None,
    ) -> None:
        self.component = component
        self.level = (level or os.environ.get("OTL_LOG_LEVEL", "INFO")).upper()
        self.stream = stream or sys.stderr
        if self.level not in _LEVELS:
            self.level = "INFO"

    def _emit(self, level: str, event: str, **fields: Any) -> None:
        if _LEVELS[level] < _LEVELS[self.level]:
            return
        record = {
            "ts": round(time.time(), 6),
            "level": level,
            "component": self.component,
            "event": event,
            "fields": fields,
        }
        self.stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        self.stream.flush()

    def debug(self, event: str, **fields: Any) -> None:
        self._emit("DEBUG", event, **fields)

    def info(self, event: str, **fields: Any) -> None:
        self._emit("INFO", event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit("WARNING", event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit("ERROR", event, **fields)


def get_logger(component: str) -> StructuredLogger:
    return StructuredLogger(component)
