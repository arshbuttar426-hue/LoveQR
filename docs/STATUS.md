# Project status

**As of:** 2026-11-08
**Stage:** software, simulation and a first physical screen→camera link complete.
**Tests:** 183 passing (`python3 -m pytest`).
**Experiments:** E01–E13 implemented; full runs recorded under
`experiments/*/runs/`. The latest run of each is indexed in
[`../results/SUMMARY.md`](../results/SUMMARY.md).

> **A physical optical measurement exists.** Two M9 camera sessions were
> captured with an iPhone14,2 through Continuity Camera, viewing the macOS
> display: a still burst and a full 255-frame packet video. E11 reports
> `PHYSICAL / CAMERA CAPTURE` for both. The packet decoded 255/255 unique frames
> at cell/bit accuracy 1.000, with 0 RS corrections, and recovered the 317-byte
> payload with a matching SHA-256. Decode is still software. E01–E10 remain
> `OBSERVED (SIMULATED)` for optics. `VERIFIED` is reserved for a capture with a
> named device, date, raw file and reproduction command; see
> [`MEASUREMENT_POLICY.md`](MEASUREMENT_POLICY.md) and
> [`M9_PHYSICAL_VALIDATION.md`](M9_PHYSICAL_VALIDATION.md).
>
> **M10 repeated the physical baseline.** Three independent camera sessions
> recovered the same 317-byte payload at identical normalised rates
> (1,199.88 bps channel, 879.91 bps gross payload, 769.49 bps RS goodput,
> 99.44 bps application). E12 measures **11.30%** application payload
> utilisation per frame and attributes the dominant loss (677.27 bps, 56.4% of
> the channel) to **unused packet capacity**. Camera capture and decode have
> measured headroom; RS correction and packet loss are not limiting. Display
> brightness was varied only as a measured `DisplayServices` fraction, and both
> brightness sessions failed from hand-held framing drift, so no brightness
> effect is claimed. Distance, angle and ambient illuminance remain
> **UNMEASURED**. See
> [`M10_CHANNEL_EFFICIENCY.md`](M10_CHANNEL_EFFICIENCY.md).
>
> **M11 optimised packet utilisation.** The 11.99% wire packet fill is unused
> capacity: the fixed packet is 2,453 bytes and the frozen payload is 294 wire
> bytes. Five of six deterministic arms were captured physically. Filling
> packet 0 with 2,421 incompressible bytes raises measured application
> throughput from **99.44 bps to 759.45 bps (7.64×)**; `nsym=24` reaches
> **792.39 bps (7.97×)** with 14 erasures of margin; four logical payloads share
> one packet at **715.22 bps**; and the shared dictionary recovers
> **145,745 bytes** from one packet with **255/255 unique frames and zero
> erasures**. The always-on control (A4) was not captured physically, so its
> 2× adaptive gain remains software-only. One failed A1 attempt (phone aimed
> away from the display) is retained. See
> [`M11_PACKET_UTILISATION.md`](M11_PACKET_UTILISATION.md).

## 1. What is complete

| Area | State | Evidence |
| --- | --- | --- |
| Protocol (frame, packet, blink) | Implemented and unit-tested | `otl/protocol/`, `tests/test_frame.py`, `test_packet.py`, `test_blink.py` |
| Reed–Solomon + CRC | Clean-room implementation, tested to capacity | `otl/ecc/`, E05, E06 |
| `OTL1` compression | Deterministic, exact roundtrip | `otl/compress/`, E07 |
| Renderer | Deterministic, golden hash | `otl/tx/renderer.py`, E10 |
| Simulated channel | Perspective, blur, noise, vignette, brightness, gamma, ambient, JPEG | `otl/rx/channel.py`, E02–E04 |
| Detector/decoder | Fiducials, homography, sampling, classification; no camera dependency | `otl/rx/detect.py`, `otl/decoder/`, E10 |
| Rolling-shutter model | Row exposure integration + timing budget | `otl/rx/rolling.py`, E08 |
| End-to-end pipeline | Compress → packetise → render → channel → decode → RS → reassemble | `otl/pipeline.py`, E09 |
| TX player (M9) | Deterministic full-screen HTML player, hold/playback, frame manifest | `otl/tx/player.py`, `tests/test_player.py` |
| RX capture/session (M9) | ffmpeg/AVFoundation capture, byte-preserving import, HEIC derivation, session lock | `otl/rx/capture.py`, `otl/rx/session.py`, `tests/test_capture_session.py` |
| Physical experiment (M9) | E11 decode of preserved captures, accuracy/throughput/latency, evidence gates | `experiments/e11_physical.py`, `tests/test_e11_physical.py` |
| Physical efficiency/reliability (M10) | E12 exact rate/utilisation accounting, loss decomposition, repeatability, factor coverage | `experiments/e12_channel_efficiency.py`, `tests/test_e12_channel_efficiency.py` |
| M11 packet-utilisation codec | Compact 15-byte header, capacity-aware packets, `OTB1` bundle, adaptive compression | `otl/protocol/m11.py`, `otl/compress/adaptive.py`, `tests/test_m11_packet_utilisation.py` |
| M11 capture/prepare tooling | Deterministic arm builder, frozen-M9 player render, one-command physical capture | `experiments/m11_payloads.py`, `scripts/m11_prepare.py`, `scripts/m11_capture_arm.py` |
| Packet-utilisation experiment (M11) | E13 software validation, physical `m11-*` analysis, exact loss identity, capacity table | `experiments/e13_packet_utilisation.py`, `tests/test_m11_packet_utilisation.py` |
| Brightness instrumentation (M10) | macOS `DisplayServices` fraction read/set, JSON output | `scripts/display_brightness.py` |
| CLI | `manifest`, `info`, `render`, `decode`, `transfer-sim`, `selftest`, `play`, `capture`, `session` | `otl/cli.py`, `tests/test_cli.py` |
| Experiment harness | Append-only runs, raw JSONL, reports, index | `experiments/harness.py` |
| Documentation | Research, architecture, protocol, experiments, reproduction, hardware plan, licences, decisions, milestones | `docs/` |
| Reproducibility | Pinned lockfile, bootstrap script, Makefile, checksums, rerun verification | `requirements.lock`, `bootstrap.sh`, `scripts/checksums.py`, `scripts/verify_rerun.py` |

## 2. Claim-by-claim status

| ID | Claim | Status | Where |
| --- | --- | --- | --- |
| C01 | 30 cells × 4 bits = 120 raw bits/frame | `THEORETICAL` | E01, `docs/PROTOCOL.md` |
| C02 | 11 payload bytes/frame after header + CRC | `THEORETICAL` | E01 |
| C03 | 4,617 bps RS goodput at 60 fps | `THEORETICAL` | E01 |
| C04 | 16 packets / 39,216 bytes maximum | `THEORETICAL` | E01 |
| C05 | 16 four-triangle patterns are separable | `OBSERVED (SIMULATED)` | E02 |
| C06 | Single-frame failure boundaries: brightness 0.08, perspective 0.18; no failure to blur σ 16, noise σ 90 or vignette 0.9 | `OBSERVED (SIMULATED)` | E03 |
| C07 | Resolution boundary 0.06 scale; perspective boundary 0.12 | `OBSERVED (SIMULATED)` | E04 |
| C08 | 32 lost frames recoverable; 33 not | `OBSERVED (SOFTWARE)` | E05 |
| C09 | RS corrects `2e + r ≤ 32`; rejects beyond | `OBSERVED (SOFTWARE)` | E06 |
| C10 | `OTL1` is exact and compresses structured data | `OBSERVED (SOFTWARE)` | E07 |
| C11 | 26-chip word needs readout ≥ 26 symbols and exposure ≤ 1 symbol | `OBSERVED (SIMULATED)` + `THEORETICAL` | E08 |
| C12 | 60 Hz display cannot carry a 26-chip word in one capture | `REJECTED` | E08 |
| C13 | Full pipeline: 48/64 simulated transfers; clean/mild/harsh 16/16 each, brutal 0/16; a second full run reproduces the same payload and outcome fingerprints | `OBSERVED (SIMULATED)` | E09 |
| C14 | Render/decode/pipeline are deterministic; decoder is camera-independent | `OBSERVED (SOFTWARE)` | E10 |
| C15 | Simulated results predict a real phone link | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` for one link; broader prediction open | E11 packet, normalized comparisons |
| C16 | The temporal layer is flicker-safe for humans | `HYPOTHESIS` | none |
| C17 | The link works at a specific physical distance/angle | `HYPOTHESIS` | none |
| C18 | The M9 TX/RX/session path preserves originals and feeds the existing decoder on real raster data | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` | E11 still and packet runs |
| C19 | A smartphone camera can decode the displayed FULL16 frames in this environment | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` | E11 still run `20261108T110718Z-bf6b16`; packet run `20261108T110719Z-e6ad25` |
| C20 | A full 255-frame packet survives the screen→camera→decode path and reassembles a SHA-verified payload | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` | E11 packet run; `datasets/physical/m9-iphone14-2-packet-20261108T104529Z` |
| C21 | The physical baseline repeats: three independent sessions recover the exact payload at identical normalised rates | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` | E12 run `20261108T114711Z-2064a2`; `m10-baseline-01/02/03` |
| C22 | Application payload utilisation is 11.30% per frame, and unused packet capacity is the dominant loss (677.27 bps, 56.4% of the channel) | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` + `THEORETICAL` (arithmetic) | E12, M10 report §4–§5 |
| C23 | Camera capture, decode, RS correction and packet loss are not limiting at the 317-byte payload | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` | E12 measured headroom and zero corrections in the reference |
| C24 | Display brightness affects physical reliability | `UNMEASURED` | Brightness values were set and read back, but both sessions lost framing; no causal effect measured |
| C25 | The link works at 60 fps | `UNMEASURED` | 60 fps rows are projections; no 60 fps physical capture |
| C26 | The 11.99% wire fill is unused packet capacity, not protocol loss | `OBSERVED (PHYSICAL)` + `THEORETICAL` | E13 root-cause arithmetic; `docs/M11_PACKET_UTILISATION.md` |
| C27 | Filling packet 0 with incompressible data raises measured application throughput 7.64× | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` | E13 run `20261108T125654Z-e5001c`; `m11-a1-fill-adaptive-20261108T122956Z` |
| C28 | Four logical payloads share one 255-frame packet with per-entry verification | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` | E13; `m11-a2-bundle-20261108T123222Z` |
| C29 | The shared dictionary recovers 145,745 bytes from one packet | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` | E13; `m11-a3-dictionary-20261108T123444Z` |
| C30 | `nsym=24` adds 105 payload bytes and 4.34% throughput at the same frame count, with measured erasure margin | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` | E13; `m11-a5-rs24-20261108T123758Z` |
| C31 | Adaptive raw/OTL1 is 2× the always-on path for incompressible data | `OBSERVED (SOFTWARE)` only | E13 software arm A4; no physical A4 session |
| C32 | The optimised link works at 60 fps | `UNMEASURED` | no 60 fps M11 capture |
| C33 | The optimised link works at other distances/angles/lux | `UNMEASURED` | hand-held phone; no calibrated positioner or lux meter |

## 3. Measured vs theoretical

- **Measured (software/simulation):** decode success rates, cell accuracy, BER,
  RS correction counts, compression ratios, render/decode latency, CPU, RSS,
  determinism hashes. These are real measurements *of this implementation*.
- **Measured (M9 physical camera):** an iPhone14,2 viewed the macOS display
  through Continuity Camera. Still burst: 15 camera files, one unique image
  (14 byte-identical duplicates), CRC 1/1, cell and bit accuracy 1.000, 12.31 ms
  decode. Full packet: 869 camera samples,
  816 CRC-valid (93.9%), 255/255 unique frames, cell/bit accuracy 1.000, 0
  erasures, 0 RS corrections, payload 317 bytes with matching SHA-256,
  1,199.88 bps gross channel, 879.91 bps gross payload, 769.49 bps RS goodput,
  99.44 bps application, 7.42 ms/sample decode. See
  [`M9_PHYSICAL_VALIDATION.md`](M9_PHYSICAL_VALIDATION.md).
- **Measured (M9 fixture, historical):** one HTML-player screen captured by
  `screencapture` at 2560×1664: CRC 1/1, cell/bit accuracy 1.000, decode
  13.91 ms. This is a **software fixture**, not a camera link.
- **Measured (M9 probe, historical):** camera availability and global brightness
  response to a white/black display; raw frames preserved under
  `datasets/physical/attempts/`.
- **Theoretical:** bit rates at a given display refresh, packet capacity,
  maximum transfer size, RS capacity, the rolling-shutter timing inequality.
- **Measured (M10 physical camera):** three independent baseline repeats at the
  frozen M9 setup. Each recovered the SHA-verified 317-byte payload at
  1,199.88 bps gross channel, 879.91 bps gross payload, 769.49 bps RS goodput
  and 99.44 bps application. Unique-frame delivery was 255/255, 255/255 and
  246/255; the last needed 9 erasures and 18 RS corrections. Camera-sample CRC
  rate varied from 0.618 to 0.889. Application payload utilisation was 11.30%
  per frame; the dominant loss was unused packet capacity (677.27 bps, 56.4% of
  the channel). Two brightness attempts at measured `DisplayServices`
  fractions 0.650 and 0.900 lost the fiducials to hand-held framing drift and
  failed to deliver the packet; they are reliability failures, not a brightness
  effect. See [`M10_CHANNEL_EFFICIENCY.md`](M10_CHANNEL_EFFICIENCY.md).
- **Measured (M11 physical camera):** five locked `m11-*` arms on the same
  device pair. Filling packet 0 and choosing raw for incompressible data gave
  759.45 bps (7.637× the 99.44 bps reference); `nsym=24` gave 792.39 bps
  (7.968×) with 10 erasures against 24, leaving 14 of margin; an `OTB1` bundle
  delivered four SHA-verified payloads at 715.22 bps; and the shared dictionary
  recovered 145,745 bytes from one packet with 255/255 frames and zero
  erasures. All five match their manifest SHA-256. One failed A1 attempt is
  retained. A4 (always-on, two packets) was not captured physically. See
  [`M11_PACKET_UTILISATION.md`](M11_PACKET_UTILISATION.md).
- **Not measured:** distance, angle, ambient light, absolute display luminance
  (nits), battery, thermal behaviour, sustained multi-packet throughput, A4
  physical throughput, and behaviour on other devices.

## 4. Known limitations

1. The physical link is one device pair, one indoor setting and one display.
   Distance, angle and illuminance were not measured, so no physical boundary
   is claimed. Display brightness was set and read back only as a 0–1
   controller fraction; absolute luminance in nits was not measured.
2. The channel model is not a calibrated camera: no demosaicing, no
   rolling-shutter integration during a spatial frame, no hand-shake motion
   blur, no auto-exposure transient, no measured display gamma.
3. FULL16 has minimum Hamming distance 1; protection is CRC + RS, not the
   alphabet.
4. The 4-bit packet id caps a transfer at 16 packets.
5. A 26-chip blink word does not fit a 60 Hz display capture; the temporal
   layer needs a high-refresh display or a multi-capture protocol.
6. `OTL1` is not a general-purpose compressor.
7. CPU/RSS/latency are host-specific and not portable predictions.
8. E09's simulated matrix is not a physical success rate. Its brutal channel is
   deliberately beyond a plausible handheld capture, so the boundary it reports
   is a software stress boundary, not a measured phone/camera limit.
9. The physical packet is one 317-byte payload in the M9/M10 baseline (99.44
   bps). M11 raised measured application throughput to 759–792 bps and
   delivered 145,745 bytes through the dictionary, but A4's two-packet
   physical delivery was not captured, so sustained multi-packet throughput is
   still unmeasured.
10. 34 of 869 camera samples failed fiducial detection and 19 had a frame CRC
    error in the M9 reference. Every successfully decoded cell was correct; the
    residual failure is frame availability, not pattern confusion.
11. The receiver has no framing-loss tolerance beyond RS: the M10 brightness
    sessions lost the top fiducials after about 14 s of hand-held drift, missed
    80–109 of 255 frames, and failed the packet even though the early frames
    decoded cleanly. A tripod or mount is required for factor-isolated physical
    experiments.
12. Sample CRC rate is not a success metric by itself. One baseline delivered
    255/255 frames at 61.8% sample CRC; another delivered 246/255 at 88.9%.
    Unique-frame delivery and RS erasure count predict packet success.

## 5. Open problems

- Physical boundary for distance/angle at 1080p and 4K.
- Auto-exposure/auto-focus/demosaicing effect on BER across devices.
- Sustained multi-packet throughput and real phone decode FPS.
- A4 physical always-on control and two-packet delivery.
- 60 fps playback and capture at that rate.
- Flicker safety at the symbol rates required by the temporal layer.
- Whether a multi-capture rolling-shutter word is worth specifying.
- Whether the 39 KiB ceiling should be extended with a second header format.

## 6. Next action

M9 executed the transmitter, receiver, session and E11 parts of
`docs/HARDWARE_PLAN.md` phases P0/P1, then closed the physical loop with a
still burst and a full packet. M10 froze that configuration, repeated the
baseline three times and quantified the efficiency bottleneck with E12. M11
removed that bottleneck: five arms are physically measured and the packet now
fills to 98.7–100% with exact SHA-256 reconstruction. The remaining M11 work is
the A4 physical control, a final E13 rerun, checksum regeneration and the first
commit. After that, product work moves to a separate `LoveQR` repository; the
ordered plan, capture command and architecture are in
[`M11_HANDOFF_AND_LOVEQR.md`](M11_HANDOFF_AND_LOVEQR.md). The session workflow
is in `docs/PHYSICAL_CAPTURE.md` §4; E12/E13 analyse new finalized sessions
without a code change.
