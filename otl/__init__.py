"""OPTICAL_TRANSMISSION_LAB (OTL).

A research-grade, deterministic toolkit for screen-to-camera optical data
transmission.  The package is deliberately split into independent layers so
that every layer can be tested without a physical camera:

    protocol   frame / packet / blink identifiers
    codec      cell pattern mapping and bit packing
    tx         frame and timeline rendering
    rx         channel simulation, detection, rolling-shutter capture
    decoder    spatial and temporal decoding
    ecc        CRC and Reed-Solomon
    compress   shared instruction dictionary

Nothing in this package claims a physical-world result unless the record is
explicitly tagged ``VERIFIED`` with a device, date and raw capture.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
