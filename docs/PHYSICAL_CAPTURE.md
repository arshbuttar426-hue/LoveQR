# Physical capture: interfaces, sessions and commands

This document defines the **transmitter** and **receiver** interfaces used by
M9, the session layout that makes a capture auditable, and the exact commands
needed to turn a phone photograph or video into an E11 result, plus the M10 E12
efficiency analysis.

The short version:

```
render PNG frames  ->  HTML player (TX)  ->  phone/computer screen
                                              |
                                              v
                         phone camera / video / photo (RX)
                                              |
                              preserved raw files + session.json
                                              |
                              otl decode / E11_physical (software)
```

A capture is **physical** only when `capture_source` is `camera` or
`manual-import` **and** the session is finalized. A rendered PNG, an OS screen
capture or a re-encoded fixture is **not** physical evidence.

## 1. Transmitter interface (TX)

| Item | Value |
| --- | --- |
| Frame source | `otl render` writes `p<NN>_f<NNN>.png` |
| Player | `otl play FRAMES --out player.html` |
| Player manifest | `player_manifest.json` next to the HTML |
| Display | Any browser, full screen, no browser chrome |
| Hold mode | `--hold --frame N` or `?frame=N` |
| Playback | wall-clock scheduler; `--fps`, `--autostart`, `--no-loop` |
| Embedding | embedded data URIs by default; `--no-embed` for a portable folder |

The player is deliberately dumb: it displays pre-rendered PNGs and records
their SHA-256. It never renders cells at run time, so the displayed bytes are
exactly the bytes the decoder was tested against.

`player_manifest.json` contains:

- `schema: "otl-player/1"`, `otl_version`, `created_utc`;
- `fps`, `loop`, `hold`, `embed`, `start_delay_s`, `show_hud`, `autostart`;
- one record per frame: `index`, `file`, `sha256`, `bytes`, `packet_id`,
  `frame_index`;
- `frames_sha256` (a digest over the ordered frame hashes) and
  `player_html_sha256`.

### Still-capture mode

For a single photograph, hold one frame:

```bash
python3 -m otl render --text "hello" --out demo/frames --limit 1
python3 -m otl play demo/frames --out demo/player_hold.html \
    --no-embed --hold --autostart --frame 0
```

Open `player_hold.html` in a browser, make it full screen, and photograph the
screen. The operator must record which frame is on screen; the `frame` field in
the session is that independent mapping.

### Full-packet mode

A complete OTL packet is 255 frames. Render the payload, then play it:

```bash
python3 -m otl render --input payload.txt --out demo/frames
python3 -m otl play demo/frames --out demo/player.html \
    --no-embed --autostart --fps 10
```

At 10 fps a packet takes 25.5 s, which is slow enough for a phone video at
30 fps to sample every frame. At 60 fps the packet takes 4.25 s and needs a
higher camera frame rate or a rolling-shutter-aware capture.

## 2. Receiver interface (RX)

Two paths are supported. Both preserve the original bytes.

### A. Local camera (`otl capture`)

`otl capture` drives an AVFoundation device through `ffmpeg`. The exact command
is written into the capture log.

```bash
python3 -m otl capture list
python3 -m otl capture probe 1
python3 -m otl capture still 1 --out datasets/physical/raw --frames 10 --fps 30
python3 -m otl capture video 1 --out datasets/physical/raw/clip.mp4 \
    --duration 30 --fps 30
```

`capture still` keeps **every** raw frame and marks the last non-black frame as
`selected`; it does not delete the dark settling frames. `capture video` keeps
the video file and a sidecar `*.capture_log.json` with the command and SHA-256.

### B. Manual import from a phone

Copy the original photo/video off the phone (AirDrop, USB, Photos export) and
ingest it without re-encoding:

```bash
python3 -m otl session ingest SESSION photo.HEIC --frame 0:0
python3 -m otl session ingest SESSION clip.mov --kind video --stride 1
```

`ingest_image` copies the original into `captures/originals/`, hashes it, and
only derives a PNG when Pillow/OpenCV cannot read the format (for example
HEIC). The original is never modified; both hashes are recorded.
`ingest_video` copies the video, then extracts lossless PNG frames with a
`pos_msec` timestamp for each frame.

## 3. Session layout

A session is the unit of physical evidence:

```
datasets/physical/<session_id>/
  session.json                 # schema, device, display, geometry, capture, transmitter, captures
  session.lock.json            # written by `otl session finalize`
  README.md
  display/                     # exact PNGs that were shown, copied byte-for-byte
    player_manifest.json
    p00_f000.png ...
  captures/
    originals/                 # camera originals, never edited
    derived/                   # lossless PNG conversions, only when needed
    frames/<video>/            # extracted video frames
    index.json                 # machine-readable capture index
    index.jsonl                # append-only log
```

`session.json` blocks:

| Block | Required fields for a physical session |
| --- | --- |
| `device` | `model`, `os`, `camera` |
| `display` | `model`, `kind`, `width_px`, `height_px`, `refresh_hz`, `brightness` |
| `geometry` | `distance_mm`, `angle_deg`, `ambient_lux`, `lighting`, `hand_held` |
| `capture` | `mode`, `resolution`, `fps`, `exposure`, `iso`, `focus`, `zoom`, `stabilization`, `format` |
| `transmitter` | player manifest path/hash, frame hash, payload name/SHA-256 |
| `captures` | at least one record with `path`, `sha256`, `frame` (for stills) |

A capture record for a still should include:

```json
{
  "path": "captures/originals/IMG_0001.HEIC",
  "sha256": "…",
  "kind": "still",
  "frame": {"packet_id": 0, "frame_index": 0},
  "display_file": "display/p00_f000.png",
  "width": 4032,
  "height": 3024,
  "source": "camera"
}
```

For video frames, `frame` is `null` and `pos_msec` is recorded. The OTL header
inside each decoded frame supplies the frame identity; accuracy against a known
display frame is only claimed when the operator recorded `frame`.

## 4. Exact workflow

### 4.1 Create the session

```bash
python3 -m otl session new m9-iphone-20261108 \
  --root datasets/physical \
  --source camera \
  --device-model "iPhone 13 Pro" \
  --device-os "iOS 18" \
  --camera "rear wide, 4K video" \
  --display-model "MacBook Air M5 Liquid Retina" \
  --display-kind computer \
  --display-width 2560 --display-height 1664 --refresh-hz 60 \
  --brightness "100%, True Tone off, Night Shift off" \
  --distance-mm 250 --angle-deg 5 --ambient-lux 40 \
  --lighting "indoor, no direct sun" \
  --mode video --resolution 3840x2160 --capture-fps 30 \
  --exposure "auto" --iso "auto" --focus "locked" \
  --zoom "1x" --stabilization "off" --format "HEVC"
```

`--source camera` means the files came from a camera. `--source
manual-import` is also physical (phone export). `--source fixture` is **not**
physical and is only for testing the ingestion path.

### 4.2 Attach the exact displayed frames

```bash
python3 -m otl session attach datasets/physical/m9-iphone-20261108 \
  --frames demo/frames \
  --player-manifest demo/player_manifest.json \
  --payload-name payload.txt \
  --payload-sha256 "$(shasum -a 256 payload.txt | cut -d' ' -f1)"
```

The command refuses to overwrite a frame and verifies every copied frame
against the player manifest.

### 4.3 Ingest the camera files

```bash
# Still: the operator recorded that frame 0 was on screen.
python3 -m otl session ingest datasets/physical/m9-iphone-20261108 \
  IMG_0001.HEIC --frame 0:0 --notes "hand-held, 25 cm"

# Video: extract every frame with timestamps.
python3 -m otl session ingest datasets/physical/m9-iphone-20261108 \
  IMG_0002.MOV --kind video --stride 1
```

### 4.4 Validate and lock

```bash
python3 -m otl session validate datasets/physical/m9-iphone-20261108
python3 -m otl session finalize datasets/physical/m9-iphone-20261108
```

`finalize` refuses an incomplete session and writes `session.lock.json` with
the manifest hash, capture hash, capture count and evidence label. A locked
session rejects further captures or transmitter changes.

### 4.5 Run E11

```bash
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/m9-iphone-20261108
```

The report header, `processed/summary.json` and `manifest.json` must say
`PHYSICAL / CAMERA CAPTURE`. If the session is a draft, a fixture or missing,
E11 refuses to label it physical.

### 4.6 Run E12 (efficiency and reliability)

E12 reads every locked `m9-*`/`m10-*` session under `datasets/physical` by
default. Select sessions explicitly with `--sessions` (comma-separated):

```bash
python3 -m experiments.run_all --only E12_channel_efficiency
python3 -m experiments.run_all --only E12_channel_efficiency \
  --sessions datasets/physical/m10-baseline-01-20261108T112241Z,datasets/physical/m10-baseline-02-20261108T112441Z
```

E12 never edits a session, lock file or earlier run. It reports measured values
and arithmetic `PROJECTION — not measured` rows separately. The same evidence
gates apply; a fixture is skipped, never promoted.

### 4.7 Measure display brightness (macOS)

`scripts/display_brightness.py` reads or sets the built-in display brightness
through `DisplayServices`. The value is a **controller fraction (0–1), not
nits**:

```bash
python3 scripts/display_brightness.py --get
python3 scripts/display_brightness.py --set 0.65
```

Record the start and end readback in `session.json`'s `display.brightness`
field as `start=…; end=…`. Do not convert the fraction to luminance or compare
it across displays.

### 4.8 Capture an M11 arm (packet-utilisation)

M11 has a one-command capture wrapper. It prepares nothing itself; first render
the arm from `experiments/m11_payloads.py`, then run the wrapper with a Safari
window id that the phone can see.

```bash
# 1. render frames + frozen-M9 player for one arm
python3 scripts/m11_prepare.py --arm A1_fill_adaptive \
  --out datasets/physical/m11-staging/A1_fill_adaptive --fps 10

# 2. ask Safari for the existing window id
osascript -e 'tell application "Safari" to get id of every window'

# 3. create, attach, capture, ingest, validate and lock
python3 scripts/m11_capture_arm.py --arm A1_fill_adaptive \
  --duration 31 --window-id <id>
```

`m11_capture_arm.py` sets the window to `{250, 120, 700, 700}` points and loads
`player.html?fps=10`. That smaller window was required for the phone position
used in the M11 captures; the full `{0,0,1280,832}` window put the frame outside
the camera's field of view. It records at 1920×1440 with the requested 30 fps,
ingests every frame at stride 1, then validates and finalizes. The session id is
`m11-<arm-slug>-<UTC>`.

**Duration.** 255-frame arms need about 31 s; A4 (`always_on`, 510 frames, two
packets) needs about 57 s.

**Before a capture**, take a 1–2 s probe or check a still. The phone is
hand-held and moves between captures; a probe that decodes at least five
CRC-valid frames is the practical go/no-go gate. Centre Stage was checked with
AVFoundation and is disabled (`centerStageControlMode = user`, `isCenterStageEnabled = false`);
framing drift is physical.

**Failed captures are retained.** If the arm does not match its payload, keep
the locked session and report it. E13 lists it as a failed row with a reason
and excludes it from measured throughput. Do not delete a session to make a
success rate look better.

### 4.9 Run E13 (packet utilisation)

```bash
# all locked m11-* sessions under datasets/physical
python3 -m experiments.run_all --only E13_packet_utilisation

# one session for a quick check
python3 -m experiments.run_all --only E13_packet_utilisation \
  --sessions datasets/physical/m11-a1-fill-adaptive-20261108T122956Z
```

E13 reads the arm manifest from `session.transmitter.m11`, verifies the payload
SHA-256, computes packet fill and the exact loss identity, and refuses to
promote a software arm that has no locked physical session.

## 5. Evidence gates

| Condition | E11 label |
| --- | --- |
| No session | `BLOCKED / NO PHYSICAL CAPTURE` |
| Invalid session | `BLOCKED / NO PHYSICAL CAPTURE` |
| Draft / not finalized | `BLOCKED / NO PHYSICAL CAPTURE` |
| `capture_source = fixture` | `SOFTWARE FIXTURE (NOT PHYSICAL)` |
| `capture_source = camera` or `manual-import`, finalized | `PHYSICAL / CAMERA CAPTURE` |

Decoding is always software. The physical claim refers only to the image bytes;
accuracy, latency and throughput are software measurements over those bytes.
E12 applies the same gates and additionally skips any session whose
`capture_source` is not `camera` or `manual-import`.

## 6. Current machine: measured result

Probed on 2026-11-08 (Apple M5 macOS, ffmpeg AVFoundation):

| Device | Name | Result |
| ---: | --- | --- |
| 0 | MacBook Air Camera | Works; points at the user/room, not the display |
| 1 | Arsh Camera (iPhone14,2) | **Used for the physical link**; rear camera facing the display through Continuity Camera |
| 2 | MacBook Air Desk View Camera | Device opens inconsistently; not usable |
| 3 | Arsh Desk View Camera | Fails to open |
| 4 | Capture screen 0 | Software screen capture, not a camera |

The working geometry was Safari at bounds `{0, 0, 1280, 832}` on the
2560×1664 display, frontmost, with the iPhone rear camera hand-positioned
facing it. A smaller centered window reduced the fiducial size and failed
intermittently.

Seven finalized sessions were measured: two M9 sessions and five M10 sessions.

| Session | Capture | Result |
| --- | --- | --- |
| `m9-iphone14-2-20261108T103717Z` | 15-frame 1920×1440 PNG burst, held frame 0 | 1 unique image (14 duplicates); CRC 1/1; cell/bit accuracy 1.000; decode 12.31 ms |
| `m9-iphone14-2-packet-20261108T104529Z` | 29 s 1920×1440/30 fps video, 10 fps display | 869 samples; 816 CRC-valid; 255/255 unique frames; 0 RS corrections; 317-byte payload SHA-256 matched |
| `m10-baseline-01-20261108T112241Z` | 30 s video, frozen M9 setup | 888 samples; 549 CRC-valid; 255/255 unique frames; payload matched |
| `m10-baseline-02-20261108T112441Z` | 30 s video, frozen M9 setup | 900 samples; 619 CRC-valid; 255/255 unique frames; payload matched |
| `m10-baseline-03-20261108T112602Z` | 30 s video, frozen M9 setup | 899 samples; 799 CRC-valid; 246/255 unique frames; 9 erasures / 18 RS corrections; payload matched |
| `m10-brightness-065-20261108T112854Z` | 30 s video, brightness 0.650 | 1,081 samples; 495 CRC-valid; 175/255 unique frames; packet failed |
| `m10-brightness-090-20261108T113031Z` | 30 s video, brightness 0.900 | 886 samples; 418 CRC-valid; 146/255 unique frames; packet failed |

The brightness sessions were set and read back at the stated `DisplayServices`
fractions, but the hand-held camera drifted downward after about 14 s and
clipped the top fiducials. They are preserved as failed captures; E12 marks the
brightness comparison **NOT INTERPRETABLE** rather than claiming an effect.

M11 added six more locked sessions. The successful five were captured with
Safari at `{250, 120, 700, 700}` points and the iPhone held so the whole frame,
including all four fiducials, stayed inside the camera image:

| Session | Arm | Result |
| --- | --- | --- |
| `m11-a0-reference-20261108T122331Z` | A0 reference | 247/255 unique frames; 8 erasures / 8 corrections; 99.44 bps; payload matched |
| `m11-a1-fill-adaptive-20261108T122602Z` | A1 (failed) | 6/255 unique frames; payload failed; retained as a failed capture |
| `m11-a1-fill-adaptive-20261108T122956Z` | A1 fill + adaptive | 249/255 unique frames; 6 erasures / 66 corrections; 759.45 bps; payload matched |
| `m11-a2-bundle-20261108T123222Z` | A2 `OTB1` bundle | 248/255 unique frames; 7 erasures / 77 corrections; 4/4 entries matched |
| `m11-a3-dictionary-20261108T123444Z` | A3 shared dictionary | 255/255 unique frames; 0 erasures; 145,745-byte payload matched |
| `m11-a5-rs24-20261108T123758Z` | A5 `nsym=24` | 245/255 unique frames; 10 erasures / 110 corrections; 792.39 bps; payload matched |

A4 (`always_on`, 510 frames) was not captured and remains software-only.

```bash
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/m9-iphone14-2-20261108T103717Z
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/m9-iphone14-2-packet-20261108T104529Z
```

An earlier line-of-sight probe failed because the cameras were not aimed at the
display; its raw frames are preserved under
`datasets/physical/attempts/20261108T101729Z-line-of-sight/` and are not an E11
session. Distance, angle and ambient illuminance were not measured for any
session, so they record those fields as null. Display brightness was measured
only as a controller fraction for the two M10 attempts; absolute luminance in
nits was not measured.

To repeat a physical run, place the phone so its camera sees the display, then
run §4.1–§4.6 with device `1` (or import the phone's photo/video). A fixed
mount is required for factor-isolated experiments: the M10 brightness attempts
show that hand-held drift can exceed the 32-erasure RS budget and fail an
otherwise decodable packet.
