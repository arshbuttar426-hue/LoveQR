# M9 — Physical optical validation report

**Date:** 2026-11-08
**Host:** Apple M5 macOS, Python 3.14.7, OpenCV 4.13.0, Pillow 12.2.0, ffmpeg
7.x (AVFoundation)
**Status:** **Physical capture achieved.** A real iPhone camera viewed the
macOS display, the preserved camera files were decoded by the standard decoder,
and one complete 255-frame packet was reconstructed with a matching payload
SHA-256.

> **Evidence summary**
>
> - **PHYSICAL / CAMERA CAPTURE:** two finalized sessions —
>   `m9-iphone14-2-20261108T103717Z` (still burst) and
>   `m9-iphone14-2-packet-20261108T104529Z` (full packet video).
> - **SOFTWARE FIXTURE:** one HTML-player → Safari → macOS screen capture. This
>   is retained as history and is **not** a camera measurement.
> - **BLOCKED:** the earlier E11 run with no session and the failed
>   line-of-sight probe, both retained as history.
> - **SIMULATED / SOFTWARE:** E01–E10, unchanged in kind; the M9 run also
>   re-ran the classifier-affected simulations.
>
> Physical decode is still software. Every physical number comes from preserved
> camera files; no optical data was synthesised.

## 1. What M9 added

| Layer | File | Purpose |
| --- | --- | --- |
| TX | `otl/tx/player.py` | Deterministic full-screen HTML player + `player_manifest.json`; hold and wall-clock playback modes |
| RX | `otl/rx/capture.py` | ffmpeg/AVFoundation still/video capture; byte-preserving image/video ingestion; HEIC derivation |
| Session | `otl/rx/session.py` | `session.json`, capture index, hash checks, validation, lock, evidence label |
| Experiment | `experiments/e11_physical.py` | Decode preserved captures, compute CRC/cell/bit accuracy, packet/payload reconstruction, latency, throughput, comparison, evidence gates |
| CLI | `otl/cli.py` | `otl play`, `otl capture list/probe/still/video`, `otl session new/attach/ingest/validate/finalize/list/show` |
| Harness | `experiments/harness.py`, `run_all.py` | Per-run evidence/device overrides and `--session` |
| Tests | `tests/test_player.py`, `test_capture_session.py`, `test_e11_physical.py`, `test_detect.py` | Player, preservation, locking, blocked/fixture gates, sensor-noise classifier regression |

**Protocol freeze:** the frame format, packet layout, Reed–Solomon, compression,
renderer and decoder geometry are unchanged. Two decoder/analysis corrections
were required by the physical evidence and are recorded in
[`DECISIONS.md`](DECISIONS.md):

- **D22 — cell threshold needs real cell contrast.** Sensor noise in a solid
  dark cell was being split into a false triangle. A cell now gets its own
  threshold only when its local span is at least `local_threshold_fraction`
  (0.5) of the frame's black–white span and at least `min_contrast`; otherwise
  the frame-global threshold is used. This is a classifier threshold, not a
  format change.
- **D23 — physical throughput counts displayed frames.** E11 counts unique
  `(packet_id, frame_index)` values, measures the display rate from first
  appearances, and decompresses the reassembled payload before comparing
  SHA-256. This fixed a false payload mismatch in the first video attempt.

## 2. Transmitter artifact

The demo payload is `datasets/physical/demo/payload.txt` (317 bytes, compressed
to 294 bytes, one packet). It was rendered as 255 FULL16 frames:

```bash
python3 -m otl render --input datasets/physical/demo/payload.txt \
  --name payload.txt --out datasets/physical/demo/frames
python3 -m otl play datasets/physical/demo/frames \
  --out datasets/physical/demo/player.html --no-embed --autostart --fps 10
python3 -m otl play datasets/physical/demo/frames \
  --out datasets/physical/demo/player_hold.html \
  --no-embed --hold --autostart --frame 0
```

| Artifact | Value |
| --- | --- |
| Frames | 255 (`p00_f000.png` … `p00_f254.png`) |
| Frame set SHA-256 | `207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348` |
| Player HTML SHA-256 | `c1d2e9c59e8ffbb045809fffca507cd62c3c20704bec710c994fe51ac50e7748` |
| Hold-player HTML SHA-256 | `31b5365ba9672d37861dc85618a0b42be31ad7d9e6a1ee01d71e2dc51a9e0b0c` |
| Payload SHA-256 | `829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d` |
| Packet capacity | 255 frames × 11 bytes; 11 × RS(255,223) blocks = 2,453 bytes |

The player uses `object-fit: contain`, so the 1080×1350 canvas is scaled
uniformly with black bars; no resampling beyond the browser's display path is
requested (`image-rendering: pixelated`).

Playback rate is selected with the `?fps=` query on `player.html`. Setting the
URL through Safari's AppleScript `URL of front document` applied the query;
re-using an already-open tab with `open -a Safari` did not.

## 3. Capture setup that produced a link

| Item | Value |
| --- | --- |
| Camera | `iPhone14,2` rear camera through Continuity Camera, AVFoundation index 1 ("Arsh Camera") |
| Camera format | 1920×1440 at 30 fps, H.264 MP4 (video) or PNG burst (still) |
| Display | Apple M5 built-in Liquid Retina, 2560×1664, 60 Hz |
| Browser window | Safari bounds `{0, 0, 1280, 832}` on the display, frontmost |
| Player | `player_hold.html` for the still; `player.html?fps=10` for the packet |
| Lighting | indoor; illuminance not measured |
| Distance / angle | not measured; operator hand-positioned the phone facing the display |
| Exposure / focus / ISO | auto |
| Display brightness | not measured (macOS default) |

A smaller, centered Safari window reduced the fiducial size in the camera image
and caused intermittent detection failure. The full 1280×832 window at the
top-left of the display was stable: 6/6 CRC-valid frames in a re-check before
the packet recording.

Auto-exposure, auto-focus, rolling shutter, moiré and hand motion are all
present in the physical path. They are the reason the physical numbers below
differ from the clean simulation, and they are not modelled by E01–E10.

## 4. Physical still measurement

**Session:** `datasets/physical/m9-iphone14-2-20261108T103717Z`
**Capture:** 15-frame PNG burst at 1920×1440, held on frame 0.
**E11 run:** `experiments/E11_physical/runs/20261108T110718Z-bf6b16`

| Metric | Value |
| --- | ---: |
| Camera files | 15 |
| Unique images (SHA-256) | 1 |
| Byte-identical duplicates | 14 |
| Frame CRC | 1/1 unique image (all 15 files identical) |
| Cell accuracy | 1.000 |
| Bit accuracy | 1.000 |
| BER | 0.000 |
| Decode latency | 12.31 ms/sample |
| Displayed frames delivered | 1/255 |
| Packet / payload | not reconstructed (1 frame is far below RS capacity) |

All 15 files share SHA-256
`4c0f084006835cefdd3edb4ca1ddeea83457353be00c0d64d17a36552d47d506`. They are
one observation, not 15 independent trials; E11 aggregates the unique image and
records the 14 duplicates separately. The burst shows that the optical link can
resolve every cell of a displayed frame; it cannot show packet behaviour.

## 5. Physical full-packet measurement

**Session:** `datasets/physical/m9-iphone14-2-packet-20261108T104529Z`
**Capture:** one 29 s H.264 video at 1920×1440/30 fps, 869 frames, while the
255-frame packet looped at 10 display fps (cycle 25.50 s).
**E11 run:** `experiments/E11_physical/runs/20261108T110719Z-e6ad25`

```bash
python3 -m otl capture video 1 \
  --out datasets/physical/m9-iphone14-2-packet-20261108T104529Z/captures/originals/packet_10fps.mp4 \
  --duration 29 --fps 30 --size 1920x1440
```

### 5.1 Preservation and indexing

| Item | Value |
| --- | --- |
| Original video | 493,558,284 bytes |
| Video SHA-256 | `a9dceae8f863195b94bba33916447ee4605bad0cd196e703c824dec520f5873a` |
| Captures in session | 870 (1 video + 869 extracted PNG frames) |
| Frame extraction | lossless PNG, `pos_msec` retained |
| Session lock `captures_sha256` | `a267ad75d59bd6e5beef4144d230d763c76af2f588d776bc6dc411eea3b39065` |
| Session lock `manifest_sha256` | `aeb825ce4842d47c09e7394401fead1d64c17c1effead95b9b1128c682695f54` |
| Evidence | `PHYSICAL / CAMERA CAPTURE` |

The original MP4 is kept byte-for-byte. E11 skips the video record for spatial
decoding and decodes the extracted frames; the video record stays in the
session and in the checksums.

### 5.2 Frame and cell results

| Metric | Value |
| --- | ---: |
| Camera samples decoded | 869 |
| Frame CRC OK | 816 (93.9%) |
| `E_DETECT` | 34 |
| CRC failures after detection | 19 |
| Unique displayed frames | 255/255 (100%) |
| Frame loss | 0 |
| Cell accuracy (mean of 255 unique frames) | 1.000 |
| Bit accuracy | 1.000 |
| BER | 0.000 |
| Erased frames | 0 |
| RS corrected symbols | 0 |
| Packets received / expected | 1/1 |
| Packet loss | 0 |

Each 10 fps display frame was sampled about three times by the 30 fps camera.
The 869 camera samples are attempts; the 255 unique headers are data. 34 samples
failed fiducial detection (usually a partial or blurred frame) and 19 decoded a
frame whose CRC did not match. Neither loss reached the packet layer because at
least one clean sample existed for every frame index.

### 5.3 Payload reconstruction

| Item | Value |
| --- | ---: |
| Header payload length | 317 bytes |
| Wire bytes | 294 (compressed) |
| Compression ratio | 1.0782× |
| Reassembled payload | 317 bytes |
| Payload SHA-256 | `829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d` |
| SHA-256 match | **yes** |
| Packet decode | 2.06 ms |
| Reassembly | 0.054 ms |
| Reconstruction (packet + reassembly) | 2.12 ms |

`reassemble()` returns the bytes that were on the wire, which are compressed.
E11 decompresses before hashing; comparing the compressed bytes with the
original file produced a false mismatch in the first video attempt (D23).

### 5.4 Rate and resource measurements

| Metric | Value |
| --- | ---: |
| Camera capture duration | 28.9708 s |
| Observed display rate | 9.999 fps |
| Packet duration (255 frames) | 25.5026 s |
| Gross channel rate | 1,199.88 bps |
| Gross payload rate | 879.91 bps |
| RS(255,223) goodput | 769.49 bps |
| SHA-verified application rate | 99.44 bps |
| Decode latency | 7.42 ms/sample (p50 7.57, max 11.99) |
| Decode throughput | 134.8 samples/s |
| E11 wall time | 33.86 s |
| CPU | 171.4% (multi-core) |
| Max RSS | 120,464 KB |

The application rate is low because this demo is one 317-byte packet carried by
255 frames. The protocol rates are the meaningful comparison: 88 payload
bits/frame × 9.999 fps = 879.91 bps, and 2,453 bytes/packet ÷ 25.5026 s = 769.49
bps after RS. Both match E01 arithmetic at the same display rate exactly. A
larger file would amortise the 255-frame preamble and raise application
throughput; that was not measured here.

## 6. Comparison with E01–E10

All rows are from the packet E11 run. `simulated` and `observed` are explicitly
labelled; the delta is `observed − simulated`.

| Metric | Simulated | Physical observed | Delta | Basis |
| --- | ---: | ---: | ---: | --- |
| Clean-cell accuracy | 1.000 | 1.000 | 0 | E02 clean channel vs E11 physical frames |
| File-transfer success | 0.750 | 1.000 | +0.250 | E09 64 simulated trials vs E11 one packet; sample sizes differ |
| Decode latency | 6.60 ms/frame | 7.42 ms/frame | +0.82 ms | E10 software decode vs E11 image decode, same decoder |
| Raw payload rate at 60 fps | 5,280 bps | 879.91 bps | −4,400.09 bps | E01 arithmetic vs E11 at 10 fps; the ratio is mostly display rate |
| Raw payload rate at observed 10 fps | 879.91 bps | 879.91 bps | 0 | E01 arithmetic at 9.999 fps vs E11 delivered frames |
| RS goodput at observed 10 fps | 769.49 bps | 769.49 bps | 0 | E01 arithmetic at 9.999 fps vs E11 packet capacity |

The normalized rates match exactly because the protocol arithmetic is unchanged.
The physical link adds decode latency (image load and detector work) and a 6.1%
camera-sample failure rate, but neither prevents full packet delivery.

## 7. Simulated vs physical differences

The following are the specific reasons a physical result cannot be inferred
from E01–E10. E11 records them as session metadata when a real session exists.

| Factor | Simulation (E01–E10) | Physical reality observed in M9 |
| --- | --- | --- |
| Optics | perspective warp + Gaussian blur | lens MTF, focus, diffraction, flare |
| Sensor | additive Gaussian noise | shot noise, fixed-pattern noise, demosaicing, Bayer artefacts, H.264 compression |
| Exposure | fixed brightness/gamma | auto-exposure, rolling shutter, highlight clipping, black-level offset |
| Geometry | known homography from synthetic fiducials | hand shake, tilt, partial frames, specular reflections |
| Display | ideal black/white PNG | gamma, True Tone, refresh timing, moiré |
| Temporal | frame drops with a probability | 30 fps camera sampling a 10 fps display, codec GOP, dropped/duplicated frames |
| Motion | none or synthetic blur | hand motion, autofocus hunting |
| Colour | grayscale | colour filter array, white balance |
| Environment | constant ambient | indoor lighting, reflections, shadows |
| Reconstruction | full 255-frame packet available | missing frames become RS erasures; a single frame cannot make a packet |

The **observed** physical failure mode was not cell ambiguity but frame
availability: 34 samples had too few fiducials and 19 had a CRC error, while
every cell of every successfully decoded frame was correct. That is a useful
result: D22 removed the only cell-level error seen in the first attempt, and
the residual failures are detection/geometry/timing, not pattern confusion.

## 8. What is measured, and what is not

**Measured (physical camera files, software decode):**

- frame CRC rate, unique-frame delivery, frame loss;
- cell accuracy, bit accuracy, BER over 255 unique frames;
- packet decode, erasure count, RS corrections, packet loss;
- payload reconstruction and SHA-256;
- gross channel rate, gross payload rate, RS goodput, application rate;
- decode/packet/reassembly latency, decode throughput, CPU and RSS;
- device model, display model, camera format, session hashes.

**Not measured:**

- distance, angle, ambient illuminance and display brightness (recorded as null);
- battery drain and thermal throttling;
- sustained multi-packet transfers and application throughput above one packet;
- behaviour at 4K, other phones, other lighting or motion conditions;
- flicker safety.

These remain open. The delivered demonstration does not depend on them.

## 9. History: failed probe, fixture and blocked run

These are retained so the successful result is not confused with earlier
attempts. None of them is the physical measurement above.

### 9.1 Failed line-of-sight probe

`ffmpeg -f avfoundation -list_devices true -i ""` reported camera 0 (MacBook
Air Camera) facing the user and camera 1 (iPhone14,2) facing the room/ceiling.
A white-vs-black display probe changed camera 0 by 4.8 grey levels and camera 1
by 109 levels, but camera 1 was *darker* for a white screen — auto-exposure
responding to the room, not a resolved display. No frame produced four
decodable fiducials.

Raw frames, the displayed stimulus and `analysis.json` are preserved in
`datasets/physical/attempts/20261108T101729Z-line-of-sight/`. This directory is
**not** an E11 session and not evidence of a link.

### 9.2 Software fixture

Before the phone was aimed at the screen, the player was captured with
`screencapture` at 2560×1664 and ingested as a `fixture` session
(`datasets/fixtures/display-capture-20261108T083833Z`). Frame CRC 1/1, cell and
bit accuracy 1.000, decode 13.91 ms, packet decode failed because only 1 of 255
frames existed. E11 run `20261108T102618Z-71f4e8`, label
`SOFTWARE FIXTURE (NOT PHYSICAL)`. This bypasses the lens, sensor, focus,
exposure and rolling shutter.

### 9.3 Blocked run

E11 with no session recorded one missing-prerequisite trial: run
`20261108T102619Z-b8b38b`, status `blocked`, evidence
`BLOCKED / NO PHYSICAL CAPTURE`, no accuracy or throughput.

## 10. Problems found and decisions

1. **Fiducial quadrants** used canonical canvas coordinates, so a screen
   occupying part of a camera frame could not be located. Fixed to image-relative
   quadrants; covered by tests.
2. **`session.lock.json` recorded `BLOCKED` for a finalized fixture** because
   the evidence label was set after the lock was built. Fixed; the lock records
   the final label.
3. **E11 accepted draft sessions.** It now requires `status == "final"` and a
   `session.lock.json`.
4. **The comparison table called the observed column "physical" even for
   fixtures.** It now uses `observed` plus `evidence_source`.
5. **D22 — solid-cell sensor noise became a false triangle.** The first
   physical still decoded at cell accuracy 0.70 because ~20 grey levels of noise
   in a solid dark cell exceeded the old local-span rule. The local-span
   fraction test fixed it; the duplicated still frames then decoded at 1.000.
6. **D23 — repeated camera samples inflated throughput and a compressed payload
   produced a false SHA mismatch.** E11 now counts unique frames, measures the
   display period from first appearances, and decompresses before hashing.
7. **Safari `?fps=` query was dropped** when `open -a Safari` reused an existing
   tab. Setting `URL of front document` through AppleScript applied it; 5 and
   10 fps were both verified by unique-header rate.
8. **Smaller Safari windows reduced fiducial size** and caused detection
   failure. The full 1280×832 window at `{0, 0}` was stable.

The protocol itself was not changed.

## 11. Reproduce

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB

# 1. Rebuild the demo player and frames (already stored).
python3 -m otl render --input datasets/physical/demo/payload.txt \
  --name payload.txt --out datasets/physical/demo/frames
python3 -m otl play datasets/physical/demo/frames \
  --out datasets/physical/demo/player.html --no-embed --autostart --fps 10

# 2. Re-run E11 on the preserved physical sessions.
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/m9-iphone14-2-20261108T103717Z
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/m9-iphone14-2-packet-20261108T104529Z

# 3. Verify the session locks without decoding.
python3 -m otl session validate \
  datasets/physical/m9-iphone14-2-packet-20261108T104529Z

# 4. Inspect history (not physical evidence).
python3 -m json.tool \
  datasets/physical/attempts/20261108T101729Z-line-of-sight/analysis.json
python3 -m experiments.run_all --only E11_physical \
  --session datasets/fixtures/display-capture-20261108T083833Z

# 5. Capture a new session (requires the phone facing the display).
python3 -m otl capture list
python3 -m otl capture video 1 --out /tmp/new.mp4 \
  --duration 29 --fps 30 --size 1920x1440
# session new → attach → ingest --kind video → validate → finalize
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/<session_id>
```

The exact session workflow is in [`PHYSICAL_CAPTURE.md`](PHYSICAL_CAPTURE.md).
