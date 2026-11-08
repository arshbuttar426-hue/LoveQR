# Line-of-sight probe `20261108T101729Z`

This directory is **raw camera evidence of a failed setup**, not a physical OTL
capture and not an E11 result.

Question: can any attached camera see the built-in display well enough to
decode a frame?

Method: display a full-window white page, capture 10 frames; display black,
capture 10 frames; then display the M9 hold player and capture 10 frames.
Devices: `0` = MacBook Air Camera, `1` = Arsh Camera (iPhone14,2 Continuity).

Result: no frame contained four decodable fiducials. Device 0 looks at the
user/room. Device 1 sees the room/ceiling; its global brightness changes with
the display because of room light and auto-exposure, but the player frame is not
resolved. See `analysis.json` for per-frame hashes and brightness statistics.

The images here are preserved byte-for-byte from the camera. They are **not**
ingested into a session because doing so would mislabel a failed setup as a
physical link.
