# M11 — Packet-utilisation optimisation

**Date:** 2026-11-08
**Host:** Apple M5 macOS, Python 3.14.7, OpenCV 4.13.0, ffmpeg (AVFoundation)
**Frozen baseline:** M9/M10 protocol, frame format, renderer, player and decoder.
**Status:** **Five of six arms measured physically.** The frozen 11.99% wire
packet fill is unused capacity, not protocol loss. Filling packet 0 with
incompressible data raises measured application throughput from **99.44 bps to
759.45 bps (7.64×)**; the capacity-aware RS arm reaches **792.39 bps (7.97×)**.
The dictionary arm recovers a **145,745-byte** payload from one packet with
**255/255 unique frames and zero erasures**. The always-on control (A4) was not
captured physically and remains software-only.

> **Evidence summary**
>
> - **PHYSICAL / CAMERA CAPTURE:** five locked `m11-*` sessions — A0, A1, A2,
>   A3 and A5. All recover their manifest SHA-256 exactly.
> - **FAILED ATTEMPT (retained):** one A1 session where the phone camera was
>   aimed away from the display (6/255 unique frames). It is preserved and
>   reported as a failed capture, not deleted.
> - **SOFTWARE-ONLY:** A4 (`always_on` control) and all six software
>   round-trips at a stated 10 fps.
> - **MEASURED:** application throughput, packet fill, unique-frame delivery,
>   erasures, RS corrections, exact reconstruction.
> - **UNMEASURED:** A4 physical throughput; 60 fps; distance, angle, ambient
>   illuminance and absolute luminance (nits).

## 1. Why the frozen transfer fills 11.99% of a packet

A packet is always 255 spatial frames × 11 bytes = **2,453 RS data bytes**.
The frozen M9 payload is 317 application bytes, which OTL1 turns into **294
wire bytes**. The first packet reserves a 32-byte file header, so 2,421 bytes
are available; only 294 are used. The remaining **2,159 bytes are zero
padding** that is still RS-encoded and displayed.

```
wire packet fill = 294 / 2,453                = 11.99%
application fill = 317 / 2,453                = 12.92%
packet-0 application utilisation = 317 / 2,421 = 13.09%
```

11.99% is therefore a **payload-size** property. The packet is a fixed
container, and the frozen payload is much smaller than the container.

## 2. Optimisations implemented

All additions are opt-in; `otl.protocol.packet` keeps its frozen M9 behaviour.

| Optimisation | Where | Effect |
| --- | --- | --- |
| Adaptive raw/OTL1 selection | `otl/compress/adaptive.py` | Never expands incompressible data; 2,421 bytes stay 2,421 instead of 2,450 |
| Compact 15-byte file header | `otl/protocol/m11.py` | Saves 17 bytes versus the 32-byte M9 header; keeps CRC-32, lengths and packet count |
| Multi-payload bundle (`OTB1`) | `otl/protocol/m11.py` | Four logical payloads share one 255-frame packet; per-entry CRC-32, optional SHA-256 |
| Shared dictionary on repeated data | existing `OTL1` | 145,745 bytes → 2,420 wire bytes in one packet |
| Capacity-aware RS `nsym` | `otl/protocol/m11.py` | `nsym=24` gives 2,541 data bytes/packet (+88 vs `nsym=32`) |

The bundle container layout is:

```
magic "OTB1" | version u8 | flags u8 | total u32
entry: name_len u8 | data_len u32 | crc32 u32 | [sha256 32 B] | name | data
```

## 3. Arms

| Arm | Application payload | Policy | Header | RS | Frames | Packets |
| --- | --- | --- | --- | --- | --- | --- |
| `A0_reference` | frozen 317 B demo payload | always-on OTL1 | 32 B M9 | 255,223 | 255 | 1 |
| `A1_fill_adaptive` | 2,421 B seeded random | adaptive → raw | 32 B M9 | 255,223 | 255 | 1 |
| `A2_bundle` | four 570 B entries (`OTB1`, 2,280 B net) | adaptive → raw | 15 B compact | 255,223 | 255 | 1 |
| `A3_dictionary` | 145,745 B repeated instruction records | OTL1 | 32 B M9 | 255,223 | 255 | 1 |
| `A4_always_on` | same 2,421 B as A1 | always-on OTL1 | 32 B M9 | 255,223 | 510 | 2 |
| `A5_rs24` | 2,526 B seeded random | adaptive → raw | 15 B compact | 255,231 | 255 | 1 |

Payloads are deterministic (`experiments/m11_payloads.py`) and are regenerated
byte-for-byte by `scripts/m11_prepare.py`.

## 4. Software validation

All six arms were encoded, rendered, decoded through the real packet/RS/
container code and compared by SHA-256. All six round-trip exactly. At a stated
10 fps:

| Arm | Application B | Wire B | Packets | Application bps | Wire fill | Fill incl. header |
| --- | --- | --- | --- | --- | --- | --- |
| A0 | 317 | 294 | 1 | 99.45 | 11.99% | 13.29% |
| A1 | 2,421 | 2,421 | 1 | 759.53 | 98.70% | 100.00% |
| A2 | 2,280 | 2,361 | 1 | 715.29 | 96.25% | 96.86% |
| A3 | 145,745 | 2,420 | 1 | 45,723.92* | 98.65% | 99.96% |
| A4 | 2,421 | 2,450 | 2 | 379.76 | 49.94% | 50.59% |
| A5 | 2,526 | 2,526 | 1 | 792.47 | 99.41% | 100.00% |

\* A3 counts pre-compression application bytes. Its wire payload rate is
758.91 bps; the difference is dictionary gain, not extra channel capacity.

Software-only comparisons:

- adaptive vs always-on on the same 2,421-byte payload: **2.00×** (one packet
  vs two);
- bundle vs four separate 255-frame packets: **4.00×** wall-clock amortisation;
- `nsym=24` vs `nsym=32`: **1.04337×** (105 extra payload bytes in the same
  255 frames: 88 from parity, 17 from the header).

## 5. Physical capture

### 5.1 Setup

| Item | Value |
| --- | --- |
| Camera | iPhone14,2 rear camera through Continuity Camera, AVFoundation device 1 (`Arsh Camera`) |
| Capture | H.264 MP4, 1920×1440, requested 30 fps, `ffmpeg -f avfoundation` |
| Display | Apple M5 built-in Liquid Retina, 2560×1664, 60 Hz |
| Brightness | `DisplayServices` fraction **0.354058** (not nits) |
| Player | frozen M9 `player.html?fps=10`, Safari window `{250,120,700,700}` points |
| Framing | hand-held iPhone; distance, angle and lux **UNMEASURED** |
| Centre Stage | checked and **disabled** (control mode user, enabled false) |

The smaller Safari window was required for this phone position: the camera's
field of view covered only part of the 2560×1664 display. At
`{250,120,700,700}` the complete frame, including all four fiducials, was
inside the camera image. This is a capture-geometry change, not a protocol
change; it is recorded in every session.

A short pre-capture probe was used when possible. The phone is hand-held and
was moved between captures, so one A1 capture and one probe lost the display
entirely. The failed A1 session is retained and reported separately.

### 5.2 Sessions

| Arm | Session | Captures | Video SHA-256 (prefix) | Lock manifest SHA-256 (prefix) |
| --- | --- | --- | --- | --- |
| A0 | `m11-a0-reference-20261108T122331Z` | 1,014 | `ab50685e…` | `5c5284af…` |
| A1 (failed) | `m11-a1-fill-adaptive-20261108T122602Z` | 1,021 | `92ef3ca5…` | `280f15e8…` |
| A1 | `m11-a1-fill-adaptive-20261108T122956Z` | 931 | `5cd091ba…` | `d54e5f4e…` |
| A2 | `m11-a2-bundle-20261108T123222Z` | 931 | `3470850e…` | `663da9ad…` |
| A3 | `m11-a3-dictionary-20261108T123444Z` | 1,513 | `33ad5a13…` | `d8b3e65b…` |
| A5 | `m11-a5-rs24-20261108T123758Z` | 931 | `4a80f967…` | `99a100c7…` |

Full hashes are in each `session.lock.json` and in the E13 run artifacts.

### 5.3 Measured results

| Arm | Observed fps | Unique frames | Erased | Corrected | App bps | Wire bps | Wire fill | Fill incl. header | SHA exact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 | 9.999 | 247/255 | 8 | 8 | 99.44 | 92.23 | 11.99% | 13.29% | yes |
| A1 | 9.999 | 249/255 | 6 | 66 | **759.45** | 759.45 | 98.70% | **100.00%** | yes |
| A2 | 9.999 | 248/255 | 7 | 77 | **715.22** | 740.63 | 96.25% | 96.86% | yes (4/4 entries) |
| A3 | 9.996 | 255/255 | 0 | 0 | **45,705.64*** | 758.91 | 98.65% | 99.96% | yes |
| A5 | 9.999 | 245/255 | 10 | 110 | **792.39** | 792.39 | 99.41% | **100.00%** | yes |
| A4 | — | — | — | — | not measured | — | — | — | software only |

\* pre-compression application bytes; wire payload 758.91 bps.

Measured gains over the frozen reference (99.441 bps):

- A1 fill + adaptive: **7.637×**
- A2 bundle: **7.192×** (and four payloads delivered in one packet)
- A5 capacity-aware RS: **7.968×**, and **1.04337×** over A1 at the same
  255 frames
- A3 dictionary: **459.6×** in application bytes (compression, not wire rate)

The A5/software ratio and the physical ratio agree to five significant
figures (1.04337 both), which confirms the capacity arithmetic.

### 5.4 Reliability

- Every successful arm matched its manifest SHA-256; the bundle arm verified
  all four entry hashes independently.
- Worst measured erasure count was **10** (A5) against `nsym=24`, leaving
  **14 erasures of margin** in every RS block. A3 delivered 255/255 frames with
  zero erasures and zero corrections.
- The frozen A0 capture repeated the M10 result exactly: 8 erasures, 8
  corrections, 99.44 bps at 9.999 fps.
- A1/A2/A5 needed more corrected symbols than erased frames (66/77/110
  corrections for 6/7/10 erasures), which is expected when some retained
  samples contain byte errors. All remained inside `2e + r ≤ 32` (`≤ 24` for
  A5).

## 6. Loss accounting

E13 closes the identity to a floating-point residual:

```
channel − application
    = framing (header + CRC)
    + RS parity
    + file header
    + unused packet padding
    + encoding overhead (negative when compression wins)
```

- A0 residual: 0.0 bps; dominant loss `unused_packet_padding`.
- A1 residual: ~2.3e-13 bps; dominant loss becomes `framing_header_and_crc`
  because the packet is full.
- A2 residual: 0.0 bps.
- A3 residual: ~2.5e-12 bps.
- A5 residual: ~2.3e-13 bps.

The optimisation therefore moves the bottleneck: once the packet is full, the
irreducible costs are the 26.67% frame overhead and RS parity.

## 7. What is not measured

- **A4 physical throughput.** The always-on control has no camera session. Its
  2.00× adaptive-vs-always-on ratio is software-encoded, not measured over the
  camera.
- **Multi-packet physical delivery.** A4 would have been the first 510-frame
  two-packet capture; it was not captured.
- **60 fps.** Every 60 fps figure is `PROJECTION — not measured`.
- **Distance, angle, ambient illuminance, nits.** The phone is hand-held; no
  calibrated positioner or lux meter was used.
- **Repeatability across multiple sessions per arm.** One successful physical
  session per arm (A1 has one successful and one failed attempt).

## 8. Reproduce

```bash
# 1. build every arm and its frozen-M9 player
python3 scripts/m11_prepare.py --arm A1_fill_adaptive \
    --out datasets/physical/m11-staging/A1_fill_adaptive --fps 10

# 2. create, attach, capture, ingest, validate and lock one session
python3 scripts/m11_capture_arm.py --arm A1_fill_adaptive \
    --duration 31 --window-id <Safari window id>

# 3. re-analyse all locked m11-* sessions
python3 -m experiments.run_all --only E13_packet_utilisation

# 4. software tests
python3 -m pytest tests/test_m11_packet_utilisation.py
```

The canonical run is
`experiments/E13_packet_utilisation/runs/20261108T125654Z-e5001c/`.

## 9. Claim status

| ID | Claim | Status |
| --- | --- | --- |
| C26 | The 11.99% wire fill is unused packet capacity, not protocol loss | `OBSERVED (PHYSICAL)` + `THEORETICAL` |
| C27 | Filling packet 0 with incompressible data raises measured application throughput 7.64× | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` |
| C28 | Four logical payloads can share one 255-frame packet with per-entry verification | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` |
| C29 | The shared dictionary recovers 145,745 bytes from one packet | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` |
| C30 | `nsym=24` adds 105 payload bytes and 4.34% throughput at the same frame count, with measured erasure margin | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` |
| C31 | Adaptive raw/OTL1 is 2× the always-on path for incompressible data | `OBSERVED (SOFTWARE)` only — A4 has no physical session |
| C32 | The optimised link works at 60 fps | `UNMEASURED` |
| C33 | The optimised link works at other distances/angles/lux | `UNMEASURED` |
