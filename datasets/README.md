# Datasets

This directory holds the M9/M10 transmitter artifacts, physical capture
sessions, failed setup probes and non-physical fixtures.

| Directory | Purpose | Contents |
| --- | --- | --- |
| `physical/demo/` | Reproducible transmitter artifact | 255 rendered PNGs, `player.html`, `player_hold.html`, `player_manifest.json`, `payload.txt` |
| `physical/attempts/` | Raw evidence of setup probes that did **not** produce a link | camera frames, stimulus HTML, `analysis.json`, README |
| `physical/<session_id>/` | Finalized physical capture sessions | `session.json`, `session.lock.json`, displayed frames, raw camera originals |
| `fixtures/` | Non-physical ingestion/decoder fixtures | screen-capture sessions, explicitly labelled `SOFTWARE FIXTURE` |

At the time of writing there are **seven finalized physical sessions**, all from
an iPhone14,2 viewing the macOS display:

- `physical/m9-iphone14-2-20261108T103717Z/` — still burst, 15 files (one
  unique image), CRC 1/1, cell/bit accuracy 1.000.
- `physical/m9-iphone14-2-packet-20261108T104529Z/` — full 255-frame packet
  video, 869 camera frames, 255/255 unique frames, payload SHA-256 matched.
- `physical/m10-baseline-01-20261108T112241Z/`,
  `physical/m10-baseline-02-20261108T112441Z/` and
  `physical/m10-baseline-03-20261108T112602Z/` — three independent baseline
  repeats; all recovered the 317-byte payload at identical normalised rates;
  unique-frame delivery 255/255, 255/255, 246/255.
- `physical/m10-brightness-065-20261108T112854Z/` and
  `physical/m10-brightness-090-20261108T113031Z/` — measured brightness
  attempts; both lost fiducials to hand-held framing drift and failed the
  packet. They are preserved as failed captures, not brightness evidence.

See `docs/M10_CHANNEL_EFFICIENCY.md`.

The earlier failed probe is preserved under
`physical/attempts/20261108T101729Z-line-of-sight/`; it is not a link.

## Rules

1. Do not add a dataset without recording its source, licence and SHA-256 in
   `docs/LICENCES.md` (for third-party content) and in the session manifest
   (for captures).
2. Physical captures are never edited in place. Keep originals under
   `physical/<session>/captures/originals/`; derived PNGs go under
   `captures/derived/` only when the original format cannot be decoded.
3. A capture is only `PHYSICAL / CAMERA CAPTURE` when it comes from a camera or
   a manual phone import **and** the session is finalized. A rendered PNG, an OS
   screen capture or a re-encoded fixture is `SOFTWARE FIXTURE (NOT PHYSICAL)`.
4. Personal content (notifications, messages, faces) must be removed before a
   screen is captured. The M9 player is full-screen and the fixture capture was
   reviewed for this.
5. Raw frames in `physical/attempts/` are evidence of a failed setup, not of an
   optical link. Do not ingest them into a physical session.
