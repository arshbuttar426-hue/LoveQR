# Physical capture root

This directory is the root for M9/M10 physical evidence.

```
demo/                 reproducible transmitter artifact (255 PNG frames + HTML player)
attempts/             raw setup probes that did not produce a link
<session_id>/         finalized capture sessions (immutable once locked)
```

Seven sessions are finalized and measured: two M9 reference sessions and five
M10 sessions.

| Session | Capture | Result |
| --- | --- | --- |
| `m9-iphone14-2-20261108T103717Z` | 15-frame 1920×1440 still burst | 1 unique image (14 duplicates); CRC 1/1; cell/bit accuracy 1.000 |
| `m9-iphone14-2-packet-20261108T104529Z` | 29 s 1920×1440/30 fps video, 10 fps display | 869 camera samples; 255/255 unique frames; payload SHA-256 matched |
| `m10-baseline-01-20261108T112241Z` | 30 s video, frozen M9 setup | 888 samples; 255/255 unique frames; payload matched |
| `m10-baseline-02-20261108T112441Z` | 30 s video, frozen M9 setup | 900 samples; 255/255 unique frames; payload matched |
| `m10-baseline-03-20261108T112602Z` | 30 s video, frozen M9 setup | 899 samples; 246/255 unique frames; 9 erasures / 18 RS corrections; payload matched |
| `m10-brightness-065-20261108T112854Z` | 30 s video, brightness 0.650 | 1,081 samples; 175/255 unique frames; packet failed (framing drift) |
| `m10-brightness-090-20261108T113031Z` | 30 s video, brightness 0.900 | 886 samples; 146/255 unique frames; packet failed (framing drift) |

All used an iPhone14,2 rear camera through Continuity Camera (AVFoundation
device 1) facing the macOS display. The three M10 baseline repeats recovered the
exact 317-byte payload at identical normalised rates; the brightness attempts
lost the top fiducials to hand-held drift after about 14 s and are preserved as
failed captures. Locked sessions are immutable: do not re-finalize or edit
them. See `docs/M10_CHANNEL_EFFICIENCY.md`.

The cameras exposed by this host are:

| Device | Name | Status |
| ---: | --- | --- |
| 0 | MacBook Air Camera | works; faces the user, not the display |
| 1 | Arsh Camera (iPhone14,2) | **used for the physical link**; rear camera facing the display |
| 2 | MacBook Air Desk View Camera | inconsistent |
| 3 | Arsh Desk View Camera | fails to open |
| 4 | Capture screen 0 | software screen capture, not a camera |

The earlier failed line-of-sight probe is preserved in
`attempts/20261108T101729Z-line-of-sight/`. It contains raw camera frames,
per-frame SHA-256, brightness statistics and the exact commands. It is not an
E11 session and must not be cited as an optical link.

To create a new session, place a phone so its camera sees the full player
canvas, then follow `docs/PHYSICAL_CAPTURE.md`. Session directories are created
by `otl session new`, never by hand. E12 analyses every locked `m9-*`/`m10-*`
session read-only; select a subset with
`python3 -m experiments.run_all --only E12_channel_efficiency --sessions <dir,...>`.
