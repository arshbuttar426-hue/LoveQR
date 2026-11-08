# Physical-capture plan

This is the plan for turning the current **simulated** observations into
**VERIFIED** physical measurements. M9 executed the transmitter, receiver and
session parts of P0/P1, then completed a first physical link: an iPhone14,2
camera decoded a still burst and a full 255-frame packet with a SHA-verified
payload. Those sessions are `PHYSICAL / CAMERA CAPTURE` but not `VERIFIED`,
because distance, angle, illuminance and display brightness were not measured.
M10 repeated the packet three times at the frozen M9 setup, measured display
brightness as a `DisplayServices` controller fraction, and quantified the
efficiency decomposition with E12; distance, angle, ambient illuminance and
absolute luminance remain unmeasured. E01–E10 optical results remain
`OBSERVED (SIMULATED)` or `THEORETICAL`. The M9 report is
`docs/M9_PHYSICAL_VALIDATION.md`, the M10 report is
`docs/M10_CHANNEL_EFFICIENCY.md`, and the exact commands are in
`docs/PHYSICAL_CAPTURE.md`.

The plan is written so another agent or operator can execute it without
guessing. A physical result is only `VERIFIED` when the run directory contains
all of the items in §7.

## 1. Questions the physical phase must answer

| ID | Question | Current status |
| --- | --- | --- |
| P1 | Does the 30-cell FULL16 frame decode from a real phone at 20–40 cm? | **Yes** — iPhone14,2 still and full packet decoded; distance not measured |
| P2 | What is the distance/angle boundary at 1080p and 4K? | Simulated boundary only (E04); physical boundary not measured |
| P3 | How do auto-exposure, auto-focus and demosaicing change BER vs the synthetic channel? | One physical link: cell/bit BER 0.000; frame availability 93.9% |
| P4 | What is the real end-to-end latency and decode FPS on a phone? | Software benchmark only (E10); host decode 7.42 ms/sample, not on-phone |
| P5 | Can a 26-chip blink word be captured at 60/120/240 Hz display refresh? | Rejected in simulation (E08); needs confirmation |
| P6 | Does a high-refresh display (≥ 1000 Hz equivalent) make the temporal layer practical? | Untested |
| P7 | How much battery and thermal load does continuous decoding cause? | Untested physically |
| P8 | Is the temporal layer flicker-safe for a human observer? | Open risk; no human-subject study |

## 2. Minimum equipment

### Transmitter (screen)

- One OLED phone (e.g. iPhone or Pixel class) with a known resolution and
  refresh rate; record the exact model, panel type and OS build.
- One LCD monitor or tablet as a contrast case (different gamma and black
  level).
- Optional: a high-refresh display or a DLP projector for the temporal phase.
  A 26-chip word at 26 × 1 ms = 26 ms needs a display that can change the whole
  screen every ~1 ms; ordinary 60–240 Hz panels cannot. The temporal phase must
  therefore use either (a) a lab display/projector capable of ≥ 1 kHz whole-frame
  updates, or (b) a rolling-shutter mode where the word is spread across
  multiple captures and reassembled. Option (b) is a protocol change and must be
  specified before it is measured.

### Receiver (camera)

- One phone with a **manual** camera API: iOS `AVCaptureDevice` with locked
  exposure/ISO/focus/white balance, or Android Camera2 with
  `CONTROL_MODE_OFF`.
- One phone using the default camera app as a "naive" comparison.
- Record: model, sensor, lens, resolution, frame rate, exposure time, ISO,
  focus mode, white balance, stabilisation, HDR/ night mode state.

### Environment

- Measuring tape (distance), protractor or gimbal (angle), tripod for the
  camera.
- Lux meter for ambient illuminance; colour-temperature meter if available.
- Controlled lighting: dark room, office fluorescent, daylight window, and one
  flickering source (e.g. PWM dimmed LED) as a stress case.
- A neutral grey card and a black card for white/black reference checks.

## 3. Phase plan

### P0 — Render and freeze the test material (software, no capture)

1. Generate a deterministic set of frames for payloads: all-zero, all-0xFF,
   text, random, inverted, and a 10 KB file spanning multiple packets.
2. Store PNGs under `datasets/frames/<corpus>/` with a `manifest.json` that
   records the command, config and SHA-256 of every file.
3. Verify that `python3 -m otl decode` recovers each PNG exactly. This is the
   software baseline against which physical captures are compared.

**Exit criterion:** every frozen PNG decodes with CRC OK and the expected bytes.

### P1 — Static single-frame capture

1. Display one frame full-screen at maximum brightness, auto-brightness off,
   true-tone/night-shift off.
2. Mount the camera on a tripod at 30 cm, perpendicular to the screen.
3. Lock exposure/ISO/focus/white balance. Capture 30 stills (DNG/PNG) and 10 s
   of 1080p30 video.
4. Repeat for 5 frames (different cell patterns).
5. Decode each capture with the same `otl decode` path; record CRC OK, BER,
   per-triangle margins, decode time.

**Exit criterion:** ≥ 95% of stills decode with CRC OK at 30 cm, and the
failure mode of the rest is recorded (fiducial, sampling, threshold, CRC).

### P2 — Distance and angle sweep

1. Distances: 10, 20, 30, 40, 60, 80, 100, 150 cm.
2. Horizontal angles: 0°, 10°, 20°, 30°, 40°, 50°.
3. Vertical angles: 0°, 10°, 20°, 30°.
4. At each point: 10 stills + 5 s video, same locked settings.
5. Record effective cell size in pixels (from the detected homography), success
   rate, BER, and the first failing distance/angle in each direction.

**Exit criterion:** a measured boundary with at least 10 trials per point, and a
comparison with the simulated E04 boundary.

### P3 — Photometric and environmental sweep

1. Screen brightness: 100%, 75%, 50%, 25%, 10%.
2. Ambient: dark (< 5 lux), office (~300 lux), window (~1000 lux), direct
   lamp (> 5000 lux at the screen).
3. Colour temperature: 2700 K, 4000 K, 6500 K (if controllable).
4. Optional: screen protector (matte/glossy), polarised sunglasses in front of
   the lens.
5. Record success rate, BER, reference levels, and whether auto-exposure moved
   during the capture.

**Exit criterion:** a table of success rate per condition, with the failing
conditions named.

### P4 — Temporal / rolling-shutter capture

1. Use the highest-refresh display available. Record the actual refresh rate
   from the display specification and, if possible, from a photodiode trace.
2. Display the 26-chip word repeatedly.
3. Capture at 30, 60, 120, 240 fps with several exposure times (1/1000,
   1/500, 1/120, 1/60 s) and several ISO values.
4. Measure visible symbols per capture, sync detection, ID correctness, and
   whether the word fits. Compare with the E08 arithmetic.
5. If the display cannot reach the required rate, record that as a **rejected**
   physical hypothesis rather than a software failure.

**Exit criterion:** either a verified word capture with the timing values that
made it possible, or a recorded rejection with the measured refresh/readout
numbers.

### P5 — Dynamic multi-frame transfer

1. Play a full packet (255 frames) at the display refresh rate.
2. Capture video at 30/60 fps; decode frames, count CRC OK, lost frames, RS
   corrections, and reassemble the file.
3. Repeat with deliberate occlusion (hand pass), motion (hand shake), and a
   moving camera.
4. Measure gross/net throughput, goodput, frame loss, BER, latency from display
   start to file verified, CPU, memory, battery drop and device temperature.

**Exit criterion:** at least one end-to-end file recovered physically, with all
raw video retained and the exact decode command recorded.

### P6 — Flicker and human factors (only with approval)

1. Do **not** run a human-subject study without ethics approval.
2. At minimum, use a photodiode + oscilloscope to measure the modulation depth
   and frequency, and compare with published flicker-perception thresholds.
3. Record the waveform, not a subjective impression.

## 4. Controls and confounders

| Confounder | Control |
| --- | --- |
| Auto-exposure | Lock exposure/ISO; record values; verify they did not change. |
| Auto-focus | Lock focus; record dioptre; repeat with autofocus as a separate condition. |
| Auto white balance | Lock; record gains; repeat with auto as a separate condition. |
| Display brightness | Set manually; disable auto-brightness and true-tone/night-shift. |
| Display scaling | Full-screen, no letterboxing; record actual on-screen size. |
| Camera resolution | Record native vs selected; avoid digital zoom. |
| Rolling shutter | Record readout direction and row time if the API exposes it; otherwise infer from a known flicker source. |
| Compression | Capture RAW/DNG where possible; otherwise record JPEG quality and compare. |
| Hand shake | Tripod for P1–P4; hand-held only in the deliberate motion condition. |
| Ambient flicker | Record mains frequency (50/60 Hz) and lamp type; include one PWM source as a stress case. |
| Thermal throttling | Record device temperature and battery level before/after; stop if throttled. |

## 5. Metrics to record for every physical trial

- device models, OS builds, app/API and settings;
- distance (cm), horizontal angle (°), vertical angle (°);
- screen brightness setting, measured screen luminance if available;
- ambient illuminance (lux), colour temperature, lamp type;
- camera resolution, frame rate, exposure time, ISO, focus, white balance;
- number of frames captured, frames decoded, CRC OK, CRC fail;
- BER (bit and byte), packet loss, sync failures;
- gross bps, net bps, goodput bps, decode FPS, latency (ms);
- CPU %, peak RSS, battery drop (%), device temperature;
- raw file names and SHA-256 hashes;
- the exact decode command.

## 6. Raw-data policy

- Raw captures are never edited, cropped or re-encoded in place. Derived images
  go in a separate `derived/` directory.
- Each capture file gets a SHA-256 in `raw/SHA256SUMS`.
- A failed capture is retained. Deleting a capture requires a written reason in
  the run's `REPORT.md`.
- Video is stored as the camera produced it; if storage forces a transcode, the
  original is kept and the transcode is labelled.
- Personal content on the screen must be removed before capture.

## 7. Definition of VERIFIED

A physical result may be labelled `VERIFIED` only when its run directory
contains:

1. `manifest.json` with device, date, operator, settings, distance, angle,
   ambient light, brightness, and `"simulation_only": false`;
2. `raw/` original files with `SHA256SUMS`;
3. `processed/` derived metrics and a `summary.csv`;
4. `REPORT.md` with hypothesis, procedure, raw measurements, processed results,
   failures, conclusion and reproduction command;
5. a decode command that another person can run against the retained raw files
   and reproduce the reported numbers.

Anything less is `OBSERVED`, `THEORETICAL`, `HYPOTHESIS` or `REJECTED`.

## 8. Risks and stop conditions

- **Flicker / photosensitivity.** Stop immediately if any observer reports
  discomfort. Do not run a temporal display in a room with photosensitive
  people. Seek ethics approval before any human-subject measurement.
- **Display damage.** Avoid static high-brightness patterns for long periods on
  OLED; rotate patterns and use a screen saver between runs.
- **Thermal throttling.** Stop a run if the device reports throttling; a
  throttled result is not comparable with an unthrottled one.
- **Privacy.** Do not capture notifications, messages or faces. Use a dedicated
  test device or a clean profile.
- **Data loss.** Copy raw captures to a second location before processing.

## 9. Estimated effort

| Phase | Effort | Depends on |
| --- | --- | --- |
| P0 render/freeze | 0.5 day | none (software only) |
| P1 static capture | 1 day | P0, equipment |
| P2 distance/angle | 2 days | P1 |
| P3 photometric | 1 day | P1 |
| P4 temporal | 2–3 days | high-refresh display |
| P5 dynamic transfer | 3 days | P1–P3 |
| P6 flicker | external approval | P4 |

These are planning estimates, not measurements.
