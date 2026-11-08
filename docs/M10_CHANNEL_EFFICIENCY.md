# M10 — Physical channel efficiency and reliability

**Date:** 2026-11-08
**Host:** Apple M5 macOS, Python 3.14.7, OpenCV 4.13.0, ffmpeg (AVFoundation)
**Baseline protocol:** the successful M9 configuration, frozen and unchanged.
**Status:** **Physical baseline repeated.** Three independent camera sessions
recovered the complete SHA-verified payload at identical normalised rates.
E12 quantifies the per-frame payload utilisation and the loss decomposition.
Two brightness sessions were captured at measured brightness values; both lost
frame coverage to hand-held framing drift and are reported as failed captures,
not as a brightness effect.

> **Evidence summary**
>
> - **PHYSICAL / CAMERA CAPTURE:** five new M10 sessions — three baseline
>   repeats (`m10-baseline-01/02/03`) and two brightness attempts
>   (`m10-brightness-065/090`). All are finalized and locked.
> - **Frozen reference:** the M9 physical packet
>   `m9-iphone14-2-packet-20261108T104529Z` is re-analysed read-only.
> - **MEASURED:** rates, per-frame utilisation, loss decomposition,
>   repeatability, CRC/delivery reliability, decode latency.
> - **PROJECTION — not measured:** every 60 fps figure. No 60 fps physical
>   capture exists.
> - **UNMEASURED:** distance, camera angle and ambient illuminance. Brightness
>   is measured as a `DisplayServices` fraction (0–1), not in nits.

## 1. Frozen configuration

M10 did not change the frame format, packet layout, RS(255,223), compressor,
renderer, player or decoder geometry. The frozen reference is the M9 packet
session:

| Item | Value |
| --- | --- |
| Reference session | `m9-iphone14-2-packet-20261108T104529Z` |
| Frozen configuration SHA-256 | `7e1db99b9118a6b1530a5c0742900ae285cdab3b1ff6667a4c825765e71263b3` |
| Frame set SHA-256 | `207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348` |
| Payload | `payload.txt`, 317 bytes |
| Payload SHA-256 | `829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d` |
| Display player | `player.html?fps=10`, Safari window about `{0,28,1280,832}` |
| Frame | 30 cells × 4 bits = 120 bits; 88 payload bits (11 bytes) |
| Packet | 255 frames; 2,453 RS data bytes; RS(255,223), `nsym=32` |
| Frame-header overhead | 32 bits (16 header + 16 CRC) = 26.67% of the frame |

E12 checks the frame-set and payload hashes in every session. Deviations:
**none** across the seven analysed sessions.

## 2. Exact definitions and denominators

Let `fps` be the **observed display frame rate** (not the camera rate and not
the 60 Hz panel refresh), `N = 255` the displayed frames in one packet, and
`P` the SHA-verified application payload.

| Quantity | Formula | Denominator |
| --- | --- | --- |
| Packet duration | `N / fps` | observed display period |
| Gross channel | `120 × fps` | one displayed frame |
| Gross payload | `88 × fps` | one displayed frame |
| RS goodput | `2,453 × 8 / (N / fps)` | packet duration |
| Wire payload | `wire_bytes × 8 / (N / fps)` | packet duration |
| Application | `P × 8 / (N / fps)` | packet duration |
| Application bytes/frame | `P / N` | displayed frame |
| Application per-frame utilisation | `(P / N) / 11` | 11 payload bytes/frame |
| Wire per-frame utilisation | `(wire_bytes / N) / 11` | 11 payload bytes/frame |
| Packet fill (wire) | `wire_bytes / 2,453` | 2,453 RS data bytes |
| Packet fill (application) | `P / 2,453`; `P / 2,421` | RS data bytes / packet-0 capacity |
| Compression gain | `(P − wire_bytes) × 8 / (N / fps)` | packet duration |

The loss identity used by E12 is exact to floating-point rounding:

```
channel − application
    = (channel − gross_payload)        framing: header + CRC
    + (gross_payload − rs_goodput)     RS(255,223) parity
    + (rs_goodput − wire_payload)      unused packet capacity
    − (application − wire_payload)     compression gain
```

`residual_bps` in the E12 summary is zero (checked by a regression test).

## 3. Measured sessions

All rates below use the observed display rate (`9.999` fps except the 0.65
brightness attempt, where the observed rate was `9.075` fps). "CRC" is the
fraction of unique camera samples that decoded with a valid frame CRC.

| Session | Unique camera images | CRC rate | Unique frames | Payload | Decode ms | RS erasures / corrections |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| M9 packet (reference) | 869 | 0.939 | 255/255 (1.000) | **match** | 7.52 | 0 / 0 |
| `m10-baseline-01-…112241Z` | 888 | 0.618 | 255/255 (1.000) | **match** | 7.26 | 0 / 0 |
| `m10-baseline-02-…112441Z` | 900 | 0.688 | 255/255 (1.000) | **match** | 7.71 | 0 / 0 |
| `m10-baseline-03-…112602Z` | 899 | 0.889 | 246/255 (0.965) | **match** | 7.55 | 9 / 18 |
| `m10-brightness-065-…112854Z` | 1,081 | 0.458 | 175/255 (0.686) | **fail** | 5.58 | — |
| `m10-brightness-090-…113031Z` | 886 | 0.472 | 146/255 (0.573) | **fail** | 5.13 | — |
| M9 still burst | 1 | 1.000 | 1/255 | n/a | 8.16 | 0 / 0 |

The M9 still burst is a held-frame capture, not a packet transfer; it is
included only as a reference and is excluded from baseline statistics.

Every successful session produced the **same normalised rates**:

| Rate | Value |
| --- | ---: |
| Observed display rate | 9.999 fps |
| Packet duration | 25.5026 s |
| Gross channel | **1,199.88 bps** |
| Gross payload | **879.91 bps** |
| RS(255,223) goodput | **769.49 bps** |
| Application | **99.44 bps** |

Session evidence (video SHA-256 is in each session's capture log; the lock
hashes cover the manifest and every capture record):

| Session | Capture count | `captures_sha256` | `manifest_sha256` |
| --- | ---: | --- | --- |
| `m10-baseline-01-20261108T112241Z` | 889 | `09592dda0ecd3d0b1c0463fa3a89f697dd068399e667ec1198e1731574ba2494` | `e5bb266050c54e8f9c703604fc56342cdca0dc8d6a4d1a7459f787f98c43066a` |
| `m10-baseline-02-20261108T112441Z` | 901 | `0425f3b9a6d11d5941b41b0c23994846f7882a08aad6e0b5c3985ed5014ef76d` | `4dee2957adc4ce1462dbf3260108c1d5361b1569b2dce7c9a8f2eb4bcb6a29d2` |
| `m10-baseline-03-20261108T112602Z` | 900 | `dc251806f6b6df11d094613e046eac192fc62a609be0c435cbad637db2238162` | `9f79f48ab718ed085f02da229f559a1ccc9446ffdc07bd44f07e3389995638db` |
| `m10-brightness-065-20261108T112854Z` | 1,082 | `b02dc7d2534920c3bd7ac2ce32fbf1acc835b8789db7e6f3bfd81ef691627926` | `ebb11a354808b7fa5770b466c58b747bcd16f9a55f19222db429408f0a2c9d6c` |
| `m10-brightness-090-20261108T113031Z` | 887 | `2ea5ff71cfcd8949780ca3a5f7d75d01cbe6da591272bb47b7fe3de9a0ad8193` | `7094a5edf0a7545ea37a88d8251b0740488305b5b3b73c6487665e2e6f966f83` |

Raw videos (preserved byte-for-byte under `captures/originals/`):

| Session | Video bytes | SHA-256 |
| --- | ---: | --- |
| baseline-01 | 358,184,442 | `a86c611f2e3d264e5a28c3dc9164a07d2f9900d522a0ade859f637309889451b` |
| baseline-02 | 372,339,961 | `d040664b11d95276365932349c4da27441f07606fb1a49b741f23c55bc1f444c` |
| baseline-03 | 363,563,987 | `2ee66c2b88cf266b363bae4c4a4841b6cc90168f420cfab93925a7d1114f726f` |
| brightness-065 | 558,354,862 | `36338560d96f4eab46eed4ee65a4a09ac85d37657cac17dfbe909a413c7e884b` |
| brightness-090 | 473,244,725 | `7b6ada55e5ae1a9e2aff34b7b0d0bb2dd021fcf8645b50384151151153a40e3b` |

## 4. Per-frame application payload utilisation

The 317-byte payload is spread over 255 displayed frames:

| Quantity | Value |
| --- | ---: |
| Application bytes per displayed frame | `317 / 255` = **1.2431 B** |
| Frame payload capacity | **11 B** (88 bits) |
| Application payload utilisation per frame | **11.30%** |
| Wire (compressed) bytes per frame | `294 / 255` = **1.1529 B** |
| Wire utilisation per frame | **10.48%** |
| Application share of the 2,453-byte packet | **12.92%** |
| Application share of packet-0 capacity (2,421 B) | **13.09%** |
| Wire packet fill | **11.99%** |
| Application share of RS goodput | **12.92%** |

So more than **88% of every displayed frame's payload capacity is unused** at
this payload size. The transfer is protocol-bound, not decoder-bound: the
receiver is idle most of the time, but the packet is too short to fill the
255-frame container.

## 5. The 769.49 → 99.44 bps gap

Measured decomposition for the 317-byte payload at 9.999 fps:

| Stage | Loss (bps) | Share of channel |
| --- | ---: | ---: |
| Gross channel | 1,199.88 | 100.00% |
| − Framing (header + CRC) | 319.97 | 26.67% |
| − RS(255,223) parity | 110.42 | 9.20% |
| − Unused packet capacity | 677.27 | 56.44% |
| + Compression gain | 7.21 | 0.60% |
| = Application | **99.44** | **8.29%** |

The total channel-to-application gap is **1,100.44 bps**. Of that, the narrower
**RS-goodput-to-application gap is 670.05 bps**, which is exactly the unused
packet capacity (677.27 bps) minus the compression gain (7.21 bps). Framing
and RS parity sit *above* RS goodput and must not be counted twice.

The dominant loss is unused packet capacity: **677.27 bps, 56.4% of the gross
channel**. Framing is second at 319.97 bps (26.7%); RS parity is third at
110.42 bps (9.2%). The application carries 8.3% of the raw channel and 12.9%
of RS goodput.

## 6. Repeatability

Three independent baseline sessions were captured without changing the frozen
setup (same payload, frame set, renderer, decoder and 10 fps playback).

| Metric | Result |
| --- | --- |
| Sessions | 3 |
| Complete SHA-verified payload | **3/3** |
| Normalised rate CV | **0.0** (all four rates identical in every session) |
| Unique-frame delivery | 0.965–1.000 (mean 0.988) |
| Camera-sample CRC rate | 0.618–0.889 (mean 0.732) |
| Decode latency | 7.26–7.71 ms/sample (mean 7.51 ms, CV 0.025) |
| RS corrections | only baseline-03: 9 erasures, 18 corrected symbols |
| Packet loss | 0 in all sessions |

**What repeated:** the delivered payload and every normalised protocol rate.
The payload SHA-256 matched in all three sessions, and the rate CV is exactly
zero because the display period was the same and the payload size was the same.

**What varied:** camera-sample reliability and frame coverage. Baseline-01
passed only 61.8% of samples yet delivered all 255 frames because the 30 fps
camera oversampled the 10 fps display. Baseline-03 passed 88.9% of samples but
delivered only 246 frames; the 9 missing frames became 9 erasures and were
repaired by 18 RS symbols. This is the important reliability lesson: **sample
CRC rate is not frame coverage**. A high sample CRC rate can still miss a
frame, and only unique-frame delivery predicts packet success.

`frame_delivery_all_exact = false` is recorded for the baseline set because one
session needed RS help. The label `repeatable = true` therefore refers to the
delivered payload and the normalised rates, not to perfect optical frame
coverage. Both facts are reported; neither hides the other.

## 7. Factor variation and what could not be varied

| Factor | Actual values | Status | Effect |
| --- | --- | --- | --- |
| Display brightness | `0.650`, `0.900` (`DisplayServices` fraction) | **MEASURED (instrument readback)** | Not interpretable: both sessions lost fiducials to framing drift |
| Distance | — | **UNMEASURED** | No calibrated distance measurement |
| Camera angle | — | **UNMEASURED** | No angle fixture or measurement |
| Ambient illuminance | — | **UNMEASURED** | No lux meter or calibrated sensor |
| Lighting description | “indoor” in all sessions | OPERATOR-RECORDED | Nominally constant; illuminance not measured |

`scripts/display_brightness.py` reads and sets the built-in display brightness
through macOS `DisplayServices`. It reports a **fraction of the controller
range (0–1), not nits**, and the value is not comparable across displays. The
brightness sessions recorded `start=…; end=…` readbacks in `session.json`.

### Why the brightness sessions failed

Both brightness attempts captured clean frames for roughly the first 14 s, then
the hand-held camera drifted downward. The top fiducials left the image; the
decoder reports `E_DETECT` for 455/1,081 and 457/886 samples, and unique-frame
delivery fell to 0.686 and 0.573. Inspection of preserved frames (for example
`frame_000450.png` and `frame_000600.png` in the 0.90 session) shows the top
row clipped while the laptop keyboard enters the bottom of the frame. This is
a **receiver framing failure**, not evidence that brightness helped or hurt.

Consequence: the brightness factor was varied with real values, but a causal
brightness comparison is **not available** from these two sessions. The result
is still a useful measured reliability boundary: losing more than 32 frames
exceeds the RS erasure budget, so a packet that is otherwise perfectly
decodable fails outright. A future tripod-mounted capture is required to
separate brightness from framing.

## 8. Bottleneck attribution

Using the measured loss decomposition and measured headroom:

| Stage | Verdict | Measured evidence |
| --- | --- | --- |
| Unused packet capacity | **Primary bottleneck** | 677.27 bps lost; 11.99% wire packet fill; 1.24 B/frame of 11 B |
| Framing (header + CRC) | Secondary | 319.97 bps; 32 of 120 bits per frame |
| RS(255,223) parity | Third | 110.42 bps; code rate 223/255 = 0.8745 |
| Camera capture | Not limiting | 30 fps camera vs 9.999 fps display = 3.00× headroom |
| Decode | Not limiting | 133.9 decoded samples/s vs 30 fps camera = 4.46× headroom |
| RS correction | Not limiting | 0 corrections in the reference; 18 in one baseline |
| Packet loss | Not limiting | 1/1 packet in every successful session |
| Detection / CRC | Limiting only when frames are missed | Reference 816/869 CRC-valid but 255/255 delivered; brightness drift lost 80–109 frames |

The 60 Hz panel was driven at a configured 10 fps. That is a **6.00×
configuration penalty**, not a display hardware limit and not a measured 60 fps
result. The primary efficiency limit at this payload size is nevertheless the
unused packet capacity, not the display rate: even at 60 fps the same 317-byte
payload would carry only 13.1% of the packet-0 capacity.

## 9. Measured versus projection

**Measured (finalized physical sessions only):**

| Quantity | Value |
| --- | ---: |
| Display rate | 9.999 fps |
| Gross channel | 1,199.88 bps |
| Gross payload | 879.91 bps |
| RS goodput | 769.49 bps |
| Application | 99.44 bps |
| Per-frame application utilisation | 11.30% |

**PROJECTION — not measured** (arithmetic only; no 60 fps physical capture):

| Scenario | Application | RS goodput | Gross channel |
| --- | ---: | ---: | ---: |
| Same 317-byte payload at 60 fps | 596.71 bps | 4,617.41 bps | 7,200 bps |
| Full packet-0 payload (2,421 B) at 60 fps | 4,557.18 bps | 4,617.41 bps | 7,200 bps |
| Maximum 16-packet transfer (39,216 B) at 60 fps | 4,613.65 bps | 4,617.41 bps | 7,200 bps |
| Same 317-byte payload at the observed 9.999 fps | 99.44 bps | 769.49 bps | 1,199.88 bps |

The last row is the arithmetic identity of the measured row, not a second
measurement. It is retained to show that the measured rates are the arithmetic
values at the observed display period.

## 10. Threats to validity

1. **One device pair, one host, one indoor setting.** No claim about other
   phones, displays or rooms.
2. **Hand-held camera.** Baseline sessions were stable enough to deliver the
   payload; the brightness sessions were not. Framing is a real failure mode.
3. **No distance/angle/lux measurement.** E12 reports `UNMEASURED`; it does not
   substitute a nominal value.
4. **Brightness is a controller fraction, not luminance.** Nits were not
   measured, and the brightness comparison is confounded by framing drift.
5. **10 fps playback, 30 fps camera.** The 60 fps rows are projections.
6. **One 317-byte payload.** Larger payloads and multi-packet transfers were
   not measured.
7. **Decode is software.** The optical path is physical; the decoder is not.
8. **Raw video is H.264.** The session preserves the encoded camera file and
   lossless PNG extractions; codec artefacts are part of the received signal.

## 11. Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB

# Re-analyse every locked M9/M10 physical session (read-only).
python3 -m experiments.run_all --only E12_channel_efficiency

# Or select sessions explicitly.
python3 -m experiments.run_all --only E12_channel_efficiency \
  --sessions datasets/physical/m10-baseline-01-20261108T112241Z,datasets/physical/m10-baseline-02-20261108T112441Z

# Brightness instrumentation (macOS, controller fraction not nits).
python3 scripts/display_brightness.py --get
python3 scripts/display_brightness.py --set 0.65
```

E12 discovery accepts locked sessions whose directory name starts with `m9-`
or `m10-`. It never edits a session, a lock file or an earlier run directory.
The latest E12 run is
`experiments/E12_channel_efficiency/runs/20261108T114711Z-2064a2`.

## 12. Conclusion

At the frozen M9 configuration the physical link delivers **99.44 bps** of
SHA-verified application data over a **1,199.88 bps** raw channel and
**769.49 bps** of RS(255,223) goodput. The per-frame application payload
utilisation is **11.30%** (1.243 of 11 bytes). The dominant loss is **unused
packet capacity (677.27 bps, 56.4% of the channel)**, followed by framing
(319.97 bps) and RS parity (110.42 bps); compression recovers only 7.21 bps on
this tiny payload. Three independent baseline sessions recovered the exact
payload at identical normalised rates, while camera-sample CRC and frame
coverage varied; one baseline needed 9 erasures and 18 RS corrections. Camera
capture, decode, RS correction and packet loss are not the bottleneck at this
payload size. Display playback at 10 fps instead of 60 Hz is a 6× configuration
penalty, but 60 fps figures remain **projections, not measurements**. Distance,
angle and ambient illuminance remain **UNMEASURED**; display brightness was
varied only as a measured controller fraction, and the two brightness sessions
failed from framing drift, so no brightness effect is claimed.
