# Experiments E01–E13

Every experiment is implemented in `experiments/` and run by
`python3 -m experiments.run_all`. Each invocation writes a new immutable
directory under `experiments/<id>/runs/<UTC timestamp>-<nonce>/` containing
`raw/trials.jsonl`, `processed/summary.json`, `processed/summary.csv`,
`REPORT.md`, `manifest.json` and `artifacts/`. `LATEST` points at the newest
run.

**Evidence level.** E01–E10 use no physical camera; every optical result there
is `OBSERVED (SIMULATED channel)`, protocol arithmetic is `THEORETICAL`, and
software timings are `OBSERVED (SOFTWARE)`. E11 is the physical path: it is
`PHYSICAL / CAMERA CAPTURE` only for a finalized camera session, otherwise
`SOFTWARE FIXTURE (NOT PHYSICAL)` or `BLOCKED / NO PHYSICAL CAPTURE`. As of
2026-11-08 five M10 sessions plus two M9 camera sessions and five successful
M11 sessions exist, so E11, E12 and E13 report measured physical results. E13
is `PHYSICAL / CAMERA CAPTURE` only for a locked `m11-*` session; its six-arm
software round-trip is `OBSERVED (SOFTWARE)`. The environment is recorded in
each `manifest.json`.

The numbers below are from the full runs recorded on the development host. Run
directories are the source of truth; re-running on another host changes the
timings and may shift a boundary by one step.

---

## E01 — Protocol arithmetic and raw capacity

**Hypothesis.** The 30-cell, four-triangle alphabet yields 120 raw bits per
screen frame, 88 payload bits after the 16-bit header and 16-bit CRC, and the
4-bit packet id limits a transfer to 16 packets.

**Classification.** `THEORETICAL (arithmetic) + OBSERVED (software timings)`.

**Controlled.** FULL16 alphabet, 16-bit header, 16-bit CRC, RS(255,223).
**Independent.** Display frame rate, frame-loss rate.
**Dependent.** Raw bit rate, framed payload rate, RS goodput, packet duration.

**Procedure.** Derive frame and packet arithmetic from `ProtocolConfig`;
compute rates for 1–120 fps and 0–10% loss; measure pack/unpack and RS
encode/decode time on 2000 random frames and one packet.

**Result (33 trials, 0.04 s).**

| Quantity | Value |
| --- | ---: |
| Cells per frame | 30 |
| Bits per cell | 4 |
| Raw bits per frame | 120 |
| Header bits | 16 |
| Payload bits | 88 |
| Payload bytes per frame | 11 |
| CRC bits | 16 |
| Frames per packet | 255 |
| Packet payload (packet 0 / later) | 2421 / 2453 bytes |
| Maximum payload | 39,216 bytes (16 packets) |
| RS code rate | 223/255 = 0.8745 |
| Raw rate at 60 fps | 7,200 bps |
| Framed payload at 60 fps | 5,280 bps |
| RS goodput at 60 fps | 4,617.4 bps |
| One packet at 60 fps | 4.25 s |
| Pack / unpack (software) | 1.42 / 3.99 µs per frame |

**Failures.** None.

**Conclusion.** The arithmetic is exact and matches the protocol definition. At
60 display frames/s the link carries at most 4,617 bps of RS-protected payload;
the 4-bit packet id caps a file at 39,216 bytes before compression. The software
timings are negligible relative to screen time.

**Reproduce.** `python3 -m experiments.run_all --only E01_capacity`

---

## E02 — Separability of the 16 four-triangle cell patterns

**Hypothesis.** Four independent black/white triangles give 16 visually distinct
patterns, but the alphabet has minimum Hamming distance 1 and therefore needs
CRC/RS protection.

**Classification.** `OBSERVED (SIMULATED channel)`.

**Controlled.** 30-cell layout, FULL16 alphabet, 15 fixed target positions, 15
random distractor cells.
**Independent.** Cell pattern 0–15, channel severity
(clean/mild/harsh/extreme/brutal).
**Dependent.** Target-cell accuracy, cell bit error rate, confidence, bit
margin, decode time.

**Procedure.** Build a frame with 15 target cells set to one pattern and 15
random distractors; render, apply the channel, decode, and compare decoded cell
values with ground truth. Repeat four times per pattern and severity (two in
quick mode).

**Result (80 trials, 9.27 s).** Mean target-cell accuracy:

| Channel | Mean accuracy |
| --- | ---: |
| clean | 1.000 |
| mild | 1.000 |
| harsh | 1.000 |
| extreme | 1.000 |
| brutal | 0.3135 |

Alphabet: 16 patterns, minimum pairwise Hamming distance **1**, maximum **4**.
The brutal channel (blur σ=3.5, noise σ=20, ambient 60, brightness 0.5,
γ=1.6, vignette 0.6, perspective 0.08, JPEG 35) is deliberately beyond a
plausible handheld capture.

**Failures.** No run failure. The brutal channel is the observed failure mode;
it is a stress case, not a claim about a real camera.

**Conclusion.** The 16-way decision is perfect in clean through extreme
simulated channels and degrades only when several degradations are combined.
Because the alphabet has distance 1, a single misclassified triangle changes the
nibble; protection comes from the frame CRC-16 and the RS packet layer, not from
the cell alphabet.

**Reproduce.** `python3 -m experiments.run_all --only E02_patterns`

---

## E03 — Single-frame decode robustness sweep

**Hypothesis.** One 120-bit frame can be recovered under moderate blur, noise,
JPEG, ambient light, brightness, perspective and vignetting, with a
parameter-dependent failure boundary.

**Classification.** `OBSERVED (SIMULATED channel)`.

**Controlled.** Random frame contents, layout, decoder settings, 12 frames per
level.
**Independent.** One channel parameter at a time: blur σ, noise σ, JPEG quality,
ambient offset, brightness, perspective, vignette, gamma.
**Dependent.** CRC success rate, cell accuracy, cell bit error rate, confidence,
decode time.

**Procedure.** Generate random valid frames, render to the canonical canvas,
apply one parameter over a fixed sweep with seeded noise, decode, and compare
header/data/CRC and cell values with ground truth. Aggregate per level.

**Result (69 trials, 8.62 s).** For brightness and JPEG quality a *lower* value
is harder; every other parameter gets harder as it increases. The boundary is
the failing level closest to the successful region.

| Parameter | Last full success | First failure | Success at first failure | Min success |
| --- | ---: | ---: | ---: | ---: |
| blur σ | 16 (no failure) | — | — | 1.000 |
| noise σ | 90 (no failure) | — | — | 1.000 |
| brightness | 0.15 | 0.08 | 0.000 | 0.000 |
| perspective | 0.12 | 0.18 | 0.000 | 0.000 |
| vignette | 0.9 (no failure) | — | — | 1.000 |
| JPEG quality | 5 (no failure) | — | — | 1.000 |
| ambient | 200 (no failure) | — | — | 1.000 |
| gamma | 2.8 (no failure) | — | — | 1.000 |

**Failures.** No run failure. The table records the first failing level; the
per-trial data retains the failures themselves. The D22 local-span threshold
moved the blur, noise and vignette boundaries past the top of the tested range;
the brightness and perspective boundaries are unchanged.

**Conclusion.** A boundary was measured for brightness (0.08) and perspective
(0.18). No failure was reached for blur σ 16, noise σ 90, vignette 0.9, JPEG
quality 5, ambient offset 200 or gamma 2.8 inside the tested range; the
per-frame photometric calibration makes global brightness/gamma/ambient largely
irrelevant until contrast is destroyed. Blur mixes triangle interiors, noise
perturbs the per-cell threshold, JPEG adds block artefacts, perspective
stresses fiducial detection, and vignetting reduces corner contrast. These are
simulated observations, not physical camera results.

**Reproduce.** `python3 -m experiments.run_all --only E03_frame_robustness`

---

## E04 — Resolution (distance proxy) and perspective (angle proxy)

**Hypothesis.** Spatial decoding tolerates moderate resolution loss and
perspective, with a measurable boundary set by cell size and the fiducial
detector.

**Classification.** `OBSERVED (SIMULATED channel)`.

**Controlled.** Clean optical channel, canonical layout, random frames, decoder
settings, 12 frames per point.
**Independent.** Downscale factor (resolution proxy), perspective amount (angle
proxy).
**Dependent.** CRC success rate, cell accuracy, cell bit error rate, detection
failures, decode time.

**Procedure.** Render random frames at 1080×1350; apply a downscale/upscale or
perspective warp; decode; record success and effective cell size.

**Result (21 trials, 2.20 s).** For resolution a *lower* scale is harder; for
perspective a *higher* amount is harder.

Resolution:

| Scale | Effective px/cell | Success rate |
| ---: | ---: | ---: |
| 1.00 | 143.0 | 1.000 |
| 0.25 | 35.75 | 1.000 |
| 0.10 | 14.30 | 1.000 |
| 0.06 | 8.58 | 1.000 |
| 0.04 | 5.72 | 0.917 |
| 0.03 | 4.29 | 0.250 |
| 0.02 | 2.86 | 0.083 |

Perspective:

| Amount | Success rate |
| ---: | ---: |
| 0.00–0.12 | 1.000 |
| 0.16 | 0.000 |
| 0.20 | 0.000 |
| 0.25 | 0.000 |

**Boundaries.** Last fully successful downscale **0.06 (8.58 px/cell)**; first
failure **0.04 (5.72 px/cell)**. Perspective last full success **0.12**; first
failure **0.16**.

**Failures.** The 0.04 and 0.03 resolution points and 0.16–0.25 perspective
points fail; raw trials retain the cell errors.

**Conclusion.** Resolution loss makes triangle sampling windows overlap pattern
boundaries; perspective is limited by the fiducial detector's fixed area/aspect
gates and quadrant assumption, which are tuned for a cropped screen. The
perspective sweep is an angle proxy, not a measurement of a real phone at a real
angle. A physical boundary requires the plan in `HARDWARE_PLAN.md`.

**Reproduce.** `python3 -m experiments.run_all --only E04_geometry`

---

## E05 — Frame loss and Reed–Solomon erasure capacity

**Hypothesis.** Byte interleaving plus RS(255,223) tolerates up to 32 lost
frames per packet, independent of whether the loss is random or bursty.

**Classification.** `OBSERVED (software ECC) + THEORETICAL (capacity)`.

**Controlled.** One packet of 255 frames, fixed 2200-byte payload, `nsym = 32`,
frame indices.
**Independent.** Number of lost frames (0–40), loss pattern (random/burst),
seed (3 seeds in full mode).
**Dependent.** Packet decode success, corrected positions, block failures,
decode time.

**Procedure.** Encode one packet; remove 0–40 frames at random or as one
contiguous burst; decode with the erasure-aware RS path; record success or the
structured error.

**Result (138 trials, 1.50 s).**

| Lost frames | Random | Burst |
| ---: | ---: | ---: |
| 0–32 | 3/3 success at every count | 3/3 success at every count |
| 33 | 0/3 | 0/3 |
| 34 | 0/3 | 0/3 |
| 36, 38, 40 | 0/3 | 0/3 |

The largest decoded loss count is **32**; the smallest failing count is **33**,
for both patterns.

**Failures.** All runs above 32 lost frames fail with `E_RECONSTRUCT`; the raw
trials retain the error and the failing block information.

**Conclusion.** The observed boundary matches `2·errors + erasures ≤ nsym` with
`nsym = 32`. Interleaving turns each lost frame into exactly one erasure in
every RS block, so random and burst loss behave identically at equal counts.
This is a software ECC result, not an optical measurement.

**Reproduce.** `python3 -m experiments.run_all --only E05_erasures`

---

## E06 — Reed–Solomon byte-error and mixed error/erasure capacity

**Hypothesis.** The clean-room RS(255,223) decoder corrects up to 16 unknown
byte errors per block, or a mix satisfying `2·errors + erasures ≤ 32`, and
rejects anything beyond that.

**Classification.** `OBSERVED (software ECC) + THEORETICAL (capacity)`.

**Controlled.** One encoded packet, block interleaving, `nsym = 32`, frame
indices.
**Independent.** Byte errors per block, number of erased frames, seed.
**Dependent.** Decode success, corrected positions, block failures, capacity
used, decode time.

**Procedure.** Encode one packet and keep a clean copy; inject a fixed number of
single-bit byte errors per RS block at random frame positions; optionally erase
whole frames (one erasure per block); decode and compare the observed boundary
with `2·errors + erasures ≤ 32`.

**Result (72 trials, 1.02 s).**

| Errors/block | Erasures | Capacity used | Result |
| ---: | ---: | ---: | --- |
| 0–16 | 0 | 0–32 | all succeed (16 errors: 6/6) |
| 17 | 0 | 34 | all fail |
| 10 | 12 | 32 | 3/3 succeed |
| 11 | 11 | 33 | all fail |
| 8 | 16 | 32 | 3/3 succeed |
| 10 | 16 | 36 | all fail |
| 9 | 16 | 34 | all fail |
| 8 | 20 | 36 | all fail |
| 2 | 28 | 32 | 3/3 succeed |
| 0 | 32 | 32 | 3/3 succeed |

**Summary.** 54 successes, 18 failures; maximum capacity used with success
**32**; minimum capacity used with failure **33**.

**Failures.** Every over-capacity case fails with `E_ECC`/`E_RECONSTRUCT`; no
case returns silently corrupt data.

**Conclusion.** The measured boundary follows `2·errors + erasures ≤ nsym`.
This is an injected-error test of the RS layer, not an optical measurement:
frame CRC would normally convert most optical byte errors into erasures.

**Reproduce.** `python3 -m experiments.run_all --only E06_errors`

---

## E07 — Shared instruction dictionary (`OTL1`) compression

**Hypothesis.** A small deterministic LIT/REPEAT/COPY/INVERT/SEQUENCE codec
reduces screen time for structured payloads while remaining byte-exact and cheap
enough for the transmitter.

**Classification.** `OBSERVED (software)`.

**Controlled.** `OTL1` encoder settings, corpus contents, payload sizes.
**Independent.** Corpus type, payload size (512 / 4096 / 16384 bytes).
**Dependent.** Compression ratio, encode/decode time, opcode counts, packets
needed.

**Procedure.** Build a deterministic corpus (zeros, repeated ABCD, alternating,
text, CSV, source code, JSON, sparse binary, random, inverted text) at each
size; compress, decompress, verify byte-exact roundtrip; record ratio, timings,
opcode mix and packets needed. `random` and `sparse_binary` are generated fresh
for each size so block repetition cannot inflate their ratio.

**Result (30 trials, 0.19 s).** Mean `OTL1` ratio (original / compressed):

| Corpus | Mean ratio |
| --- | ---: |
| zeros | 58.51 |
| alternating `00 FF` | 44.57 |
| repeat `ABCD` | 43.73 |
| source code | 25.69 |
| inverted text | 19.09 |
| text | 19.09 |
| JSON | 17.15 |
| sparse binary | 9.37 |
| CSV | 1.33 |
| random | 0.984 (range 0.972–0.992) |

All 30 roundtrips are byte-exact. Random data expands slightly (ratio < 1)
because of the container header; it never silently loses bytes.

**Failures.** None. A ratio below 1 is reported as expansion, not hidden.

**Conclusion.** `OTL1` compresses repetitive, textual and structured payloads
strongly (up to 58.5× on zeros), leaves incompressible random data at roughly
unit ratio, and always round-trips exactly. Because the compressed payload
determines the number of packets, compression directly reduces screen time.
`OTL1` does not claim to beat zlib/zstd on general data; its purpose is a small,
deterministic, inspectable instruction stream.

**Reproduce.** `python3 -m experiments.run_all --only E07_compression`

---

## E08 — Temporal blink IDs under a rolling-shutter capture

**Hypothesis.** Rolling shutter exposes multiple display symbols per capture only
when the readout time spans multiple symbol periods; a 26-chip word needs
readout ≥ 26 symbol periods and exposure ≤ 1 symbol period.

**Classification.** `OBSERVED (SIMULATED rolling shutter) + THEORETICAL (timing)`.

**Controlled.** Camera height 1350 rows, uniform display frames, sync+ID
codebook, phase 0.
**Independent.** Display frame rate (60–2000 Hz), exposure time (50–2500 µs),
row time (5–40 µs), sensor noise (0–30), blink ID (0–2).
**Dependent.** Temporal lock, correct ID, visible symbols, symbols per capture,
decode time.

**Procedure.** Render the 26-chip sync+ID word as uniform full-frame symbols;
integrate each camera row's exposure against the display timeline; optionally
add noise; segment and decode the visible symbols; compare with the analytical
readout/symbol-period ratio.

**Result (60 trials, 1.95 s).**

| Display rate | Trials | Word fits | Correct ID |
| ---: | ---: | ---: | ---: |
| 60 Hz | 3 | 0 | 0 |
| 120 Hz | 3 | 0 | 0 |
| 240 Hz | 3 | 0 | 0 |
| 500 Hz | 3 | 0 | 0 |
| 1000 Hz | 45 | 39 | 36 |
| 2000 Hz | 3 | 3 | 3 |

- 39/39 correct when the **temporal budget** is satisfied (word fits *and*
  exposure ≤ 1 symbol period).
- 36/42 correct when the word merely fits; the 3 extra failures had exposure
  2500 µs = 2.5 symbol periods, which integrates several chips per row.
- 0 successes when the word does not fit.

**Failures.** At 1000 Hz with 2500 µs exposure, all three IDs fail to lock; the
raw trials record `exposure_over_period = 2.5`.

**Conclusion.** A 26-chip word is recovered only when the rolling readout spans
at least 26 display symbol periods; the lowest tested display rate with a
fitting word was 1000 Hz. At 60 Hz a 27 ms readout sees ~1.62 symbols, so a full
blink word cannot fit in one capture. Separately, a fitting readout with a
2.5-symbol exposure destroys the word; exposure must be no longer than one
symbol period as well. This is the central temporal constraint of the proposed
architecture, and it is a physical/arithmetic result, not a software limitation.
The hypothesis that a 60 Hz display can carry a 26-chip word is **REJECTED**.

**Reproduce.** `python3 -m experiments.run_all --only E08_rolling`

---

## E09 — End-to-end simulated transfer

**Hypothesis.** The full pipeline (compression, packetisation, RS, rendering,
simulated channel, spatial decode, reassembly) recovers files under clean/mild/
harsh channels and moderate frame loss, with a measurable failure limit on a
deliberately brutal stress channel.

**Classification.** `OBSERVED (SIMULATED channel) + THEORETICAL (projected screen
time)`. Evidence source: **SIMULATED / SOFTWARE**. The optics are
`otl/rx/channel.py`; wall-clock numbers are Python execution time. This is not a
physical optical transmission benchmark.

**Controlled.** Protocol, layout, renderer, decoder, RS settings, seeds.
**Independent.** Payload kind/size, channel severity, frame-drop probability.
**Dependent.** Transfer success, compression ratio, frames decoded/dropped, BER,
simulated throughput, projected screen throughput, decode latency,
reconstruction time, CPU/memory.

**Procedure.**
1. Generate text and seeded-random payloads at four sizes and hash each one.
2. Record the payload generator, every seed and every payload SHA-256 in the run
   manifest (`experiment_metadata`).
3. Run the complete `simulate_transfer` pipeline with clean/mild/harsh/brutal
   channels and 0%/3% frame loss.
4. Record success, per-packet RS statistics, errors, throughput, latency,
   reconstruction time and resource use for **every** trial, including failures.
5. Re-derive each payload hash and fingerprint the payload set
   (`payload_manifest_sha256`) and the outcome set (`outcome_sha256`).
6. Re-run the experiment and compare the two runs with
   `scripts/verify_rerun.py`.

**Matrix.** 2 payload kinds × 4 sizes (100, 1000, 2400, 6000 bytes) × 4 channels
(clean, mild, harsh, brutal) × 2 drop probabilities (0%, 3%) = **64 trials**.
All 64 trial records, including the 16 failures, are retained in
`raw/trials.jsonl`.

### Result — successful trials

**48/64 (75.0%) succeeded.** By channel:

| Channel | Successes / trials |
| --- | ---: |
| clean | 16/16 |
| mild | 16/16 |
| harsh | 16/16 |
| brutal | 0/16 |

By payload kind: text 24/32, random 24/32. By size: 12/16 at every size — all
four brutal trials fail at each size, and every size succeeds on clean, mild and
harsh at both drop rates. All successful trials reconstructed byte-exactly
(BER = 0; no silent corruption).

Frame counts: text payloads compress to one packet (255 frames) at all four
sizes (compressed to 111/147/167/227 bytes); random 100/1000/2400 bytes need one
packet and random 6000 bytes needs three packets (765 frames, projected 12.75 s
at 60 display fps).

### Result — failed trials

**16/64 (25.0%) failed.** Every failure is the brutal channel; the failing
stages, counted per trial, are `frame_crc` 16, `packet` 16 and `reassembly` 16.

| Kind | Sizes (bytes) | Drop | Failed trials | Stages |
| --- | --- | ---: | ---: | --- |
| text | 100, 1000, 2400, 6000 | 0% | 4 | frame_crc → packet → reassembly |
| text | 100, 1000, 2400, 6000 | 3% | 4 | frame_crc → packet → reassembly |
| random | 100, 1000, 2400, 6000 | 0% | 4 | frame_crc → packet → reassembly |
| random | 100, 1000, 2400, 6000 | 3% | 4 | frame_crc → packet → reassembly |

Mechanism: the brutal channel corrupts the decoded cells, so frames fail
CRC-16 (`frame_crc`); with almost every frame erased, the packet layer raises
`E_RECONSTRUCT` caused by `E_ECC` ("too many erasures", 255 erasures against
`nsym = 32`), and reassembly cannot start. The failure is reported, never
silently accepted. A single `frame_crc` failure would still be correctable as an
erasure; the brutal channel erases essentially all frames, which is far beyond
the 32-erasure budget.

### Payload generation and SHA-256 verification

| Item | Value |
| --- | --- |
| text generator | UTF-8 template repeated then truncated; template SHA-256 `09ebc393…9119`; no seed |
| random generator | `numpy.random.default_rng` (PCG64), `integers(0, 256, size=payload_bytes, dtype=uint8).tobytes()` |
| random seed rule | `7000 + payload_bytes` → 7100, 8000, 9400, 13000 for 100/1000/2400/6000 bytes |
| trials hashed | 64 |
| verified against pre-run manifest | 64/64 |
| re-derived from the recorded generator specification | 64/64 |
| mismatches | 0 |
| `payload_manifest_sha256` | `9cf02deb1f14f95ed3521b5754216e45526f910a61b3e47704817287dd2e6e39` |
| `outcome_sha256` | `c4d98b2becddaaeeaccba18b6748afd69ed79e3926c704a39572a4f31983c075` |

### Throughput (successful trials only)

Failures carry no verified payload, so throughput aggregates use the 48
successful trials. "Simulated" is Python wall time; "projected" is
`frames / 60 display fps`, which is arithmetic, not a camera measurement.

| Metric | Mean | p50 | Max |
| --- | ---: | ---: | ---: |
| Simulated net throughput | 3,953.5 bps | 2,167.7 bps | 27,117.3 bps |
| Projected net throughput at 60 fps | 3,529.4 bps | 2,823.5 bps | 11,294.1 bps |
| Simulated decode rate | 67.2 fps | 32.4 fps | 145.1 fps |
| Projected screen time | 5.31 s | 4.25 s | 12.75 s |

### Latency (all 64 trials, measured software time)

| Metric | Mean | p50 | p95 | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Spatial decode per decoded frame | 8.57 ms | 7.85 ms | 13.56 ms | 5.77 ms | 14.41 ms |
| Total pipeline per trial | 8,982 ms | 7,999 ms | 25,260 ms | 1,757 ms | 34,514 ms |

Latency is measured decode time, not screen time. "Total pipeline per trial"
covers rendering, channel application, spatial decoding and ECC for all frames
of that trial.

### Reconstruction time (all 64 trials, measured software time)

| Stage | Mean | p95 | Max |
| --- | ---: | ---: | ---: |
| Reassembly + decompression | 0.030 ms | 0.169 ms | 0.173 ms |
| Reed–Solomon ECC decode | 3.36 ms | 10.29 ms | 22.14 ms |
| `OTL1` compression (encoder) | 0.91 ms | 4.80 ms | 4.94 ms |

### Resources

CPU 181% of one core (p95 273%, max 274.5%); peak RSS 183,552 KiB (~179.3 MiB)
for the whole run. These are host-specific measurements on the recorded machine.

### Rerun verification

Two complete full runs were recorded:

| Run | Wall time | Trials | Success rate |
| --- | ---: | ---: | ---: |
| `20261108T080655Z-52295e` | 556.7 s | 64 | 75.0% |
| `20261108T105617Z-13284e` | 575.6 s | 64 | 75.0% |

`python3 scripts/verify_rerun.py --experiment E09_end_to_end` reports
`"verdict": "IDENTICAL"`: 64 trials in each run, the same
`payload_manifest_sha256`, the same `outcome_sha256`, identical per-trial
payload hashes, success flags, frame counters and error stages, and no problems.
Wall-clock, CPU, RSS and latency differ slightly between runs and are excluded
from that comparison by design.

**Failures.** The 16 brutal-channel trials fail at `frame_crc`; see the failed
trials table above. The harness recorded no run-level exceptions
(`failures: []` in the manifest). The earlier `os.urandom` E09 run and a
quick-mode run are retained as historical data; they are superseded by the two
deterministic full runs above and are not used for any number in this section.

**Conclusion.** 48 of 64 simulated transfers succeeded (75.0%); 16 failed. Every
trial on clean, mild and harsh channels succeeded at both 0% and 3% independent
frame loss and at every tested payload size, including a 6000-byte random
payload that spans three packets. The deliberately brutal channel failed on all
16 trials, consistently at frame CRC, then RS erasure capacity, then
reassembly; the observed boundary therefore lies between the harsh and brutal
channel settings, not inside the clean/mild/harsh range. All 64 payloads were
reproduced from the recorded generator specification and all 64 SHA-256 values
matched, and an independent second run produced the same payload and outcome
fingerprints. Throughput, latency and reconstruction time are reported
separately because they answer different questions: link goodput, per-frame
decode cost, and packet-reassembly cost. Every number in this section is
**SIMULATED / SOFTWARE**; none of it is a physical optical transmission
benchmark, and it must not be cited as a phone, camera or screen measurement.

**Reproduce.**

```bash
python3 -m experiments.run_all --only E09_end_to_end
python3 scripts/verify_rerun.py --experiment E09_end_to_end
```

---

## E10 — Determinism, prerecorded-image decoding and resource benchmark

**Hypothesis.** Every stage is deterministic for fixed inputs and seeds, the
decoder works on prerecorded images without a camera, and latency/memory are
measurable and stable.

**Classification.** `OBSERVED (software)`.

**Controlled.** Fixed frames, layout/config, seed, host.
**Independent.** Repeat index, input source (memory vs PNG).
**Dependent.** Hash equality, CRC success, cell accuracy, latency, CPU, RSS.

**Procedure.** Render 40 random frames twice and compare hashes; save them as
PNG, decode from disk twice, and compare cell sequences; run the end-to-end
pipeline twice with the same seed; benchmark render/decode latency and record
CPU/RSS for the experiment interval.

**Result (3 trials, 5.48 s).**

| Check | Result |
| --- | --- |
| Frames decoded from PNG | 40/40 |
| CRC OK | 40/40 |
| Cell accuracy | 1.000 |
| Render hashes equal across repeats | yes |
| Decode cell sequences repeatable | yes |
| Pipeline identical with fixed seed | yes |
| Corpus hash | `a2bdb40d…b4c` |
| Render latency (mean) | 0.20 ms/frame |
| Decode latency (mean / p50 / p95) | 6.60 / 6.54 / 7.02 ms |
| CPU (interval) | 249% of one core |
| Peak RSS (interval) | 184,608 KiB (~180 MiB) |

**Failures.** None.

**Conclusion.** Rendering is byte-identical across repeated calls, decoding the
same prerecorded PNGs twice produces identical cell sequences, and the
end-to-end pipeline reproduces the same drop pattern and output with a fixed
seed. The decoder has no camera dependency, so it can be run on a physical
capture without code changes. Latency and memory figures are observed software
measurements on this host and will vary with hardware; CPU above 100% reflects
multithreaded OpenCV.

**Reproduce.** `python3 -m experiments.run_all --only E10_determinism`

---

## E11 — Physical optical validation (screen → camera)

**Hypothesis.** The existing FULL16 frame, renderer and decoder can recover
frames from real smartphone-camera images of a screen. Physical cell accuracy
and CRC success will be lower than the simulated clean channel because of
optics, exposure, rolling shutter, moiré, compression and hand motion.

**Classification.** `PHYSICAL / CAMERA CAPTURE` only when a finalized session
contains real camera files; otherwise `SOFTWARE FIXTURE (NOT PHYSICAL)` for a
fixture session or `BLOCKED / NO PHYSICAL CAPTURE` when no session exists.
Decoding is always software.

**Controlled.** Protocol, layout, renderer, decoder, displayed frame sequence,
capture settings.
**Independent.** Device, display, distance, angle, ambient light,
exposure/focus.
**Dependent.** Frame CRC success, cell/bit accuracy, payload reconstruction,
decode latency, capture/decode rate, throughput.

**Interfaces and procedure.** `otl render` → `otl play` (HTML full-screen
player with a SHA-256 manifest) → phone/computer screen → `otl capture`
(ffmpeg/AVFoundation) or manual phone export → `otl session ingest` (originals
preserved byte-for-byte) → `otl session validate/finalize` → E11 decode with
the standard `decode_image`, `decode_packet` and `reassemble`.

**Result on this host (2026-11-08).**

- **Physical still** (`m9-iphone14-2-20261108T103717Z`, E11 run
  `20261108T110718Z-bf6b16`): 15-frame 1920×1440 PNG burst of held frame 0 from
  an iPhone14,2 via Continuity Camera. All 15 files are byte-identical (one
  unique image); CRC 1/1, cell accuracy 1.000, bit accuracy 1.000, decode
  12.31 ms/sample. Only 1 of 255 packet frames exists, so no packet/payload.
- **Physical full packet** (`m9-iphone14-2-packet-20261108T104529Z`, E11 run
  `20261108T110719Z-e6ad25`): 29 s H.264 video, 1920×1440/30 fps, 869 camera
  frames, while the 255-frame packet looped at 10 display fps. 816 samples
  passed the frame CRC (93.9%), 34 `E_DETECT`, 19 CRC failures. Unique delivered
  frames **255/255** (0 loss), cell/bit accuracy **1.000**, **0** erasures,
  **0** RS corrections, packet loss 0. Payload **317 bytes** recovered from 294
  compressed bytes (1.0782×) with a matching SHA-256. Observed display rate
  9.999 fps; packet duration 25.5026 s; gross channel 1,199.88 bps, gross
  payload 879.91 bps, RS goodput 769.49 bps, application 99.44 bps. Decode
  7.42 ms/sample, packet decode 2.06 ms, reassembly 0.054 ms, 134.8 samples/s,
  CPU 171.4%, max RSS 120,464 KB.
- **Historical failed probe** (`datasets/physical/attempts/20261108T101729Z-line-of-sight/`):
  cameras did not have a resolved view of the display; raw frames, stimulus and
  `analysis.json` retained. Not an E11 session.
- **Historical fixture run** (`20261108T102618Z-71f4e8`): macOS `screencapture`
  of the player, 2560×1664; CRC 1/1, cell accuracy 1.000, decode 13.91 ms;
  packet failed with only 1/255 frames. Label `SOFTWARE FIXTURE (NOT PHYSICAL)`.
- **Historical blocked run** (`20261108T102619Z-b8b38b`): no session; status
  `blocked`, 1 trial, accuracy and throughput not reported.

**M10 follow-up.** Five further camera sessions were captured at the frozen
configuration; three baseline repeats again delivered 255/255, 255/255 and
246/255 unique frames with the same 317-byte payload SHA-256. E12 analyses all
locked M9/M10 sessions read-only and reports the efficiency decomposition; see
`docs/M10_CHANNEL_EFFICIENCY.md`.

**Comparison.** At 9.999 fps, E01 arithmetic predicts 879.91 bps gross payload
and 769.49 bps RS goodput; the physical packet measured exactly those values
(delta 0). Clean-cell accuracy is 1.000 in both E02 and E11. E09 file-transfer
success 0.750 (64 simulated trials) vs E11 1.000 (one physical packet); the
sample sizes differ, so this is not a like-for-like rate. Decode latency
6.60 ms (E10, software images) vs 7.42 ms (E11, camera frames). The 60 fps raw
rate comparison is 5,280 bps vs 879.91 bps, mostly because the physical display
ran at 10 fps.

**Failures.** Intermittent fiducial detection (34/869) and 19 frame CRC errors;
no frame-index loss reached the packet layer. D22 fixed solid-cell sensor noise
being split into a false triangle. D23 fixed repeated-camera-sample throughput
inflation and compressed-vs-original SHA comparison. Safari dropped the `?fps=`
query when reusing a tab; setting `URL of front document` fixed playback-rate
control. A smaller Safari window reduced fiducial size and failed; the full
1280×832 window was stable.

**Conclusion.** The existing FULL16 frame, renderer and decoder work over a real
phone-camera screen link. All 255 unique frames decoded with perfect cell
accuracy and zero RS corrections, and the payload matched byte-for-byte. The
remaining physical failures are frame availability, not cell confusion. One
device pair and one short packet are measured; distance/angle/illuminance
boundaries and sustained throughput are not.

**Reproduce.**

```bash
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/m9-iphone14-2-20261108T103717Z
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/m9-iphone14-2-packet-20261108T104529Z
```

---

## E12 — Physical channel efficiency and reliability

**Hypothesis.** The gap between RS(255,223) goodput and application throughput
is dominated by unused packet capacity (payload utilisation), not by display
refresh, camera capture, detection, decoding or RS correction. Independent
baseline sessions should repeat the normalised protocol rates while
camera-sample reliability may vary.

**Classification.** `PHYSICAL / CAMERA CAPTURE` only when at least one
finalized session passes the physical-evidence gates; otherwise
`BLOCKED / NO PHYSICAL CAPTURE`. Decode and analysis are software.

**Controlled.** Protocol, frame format, packet layout, RS(255,223),
compression, renderer, decoder geometry, payload, frame set, display playback
rate.
**Independent.** Device, display, distance, angle, ambient light, display
brightness, capture settings.
**Dependent.** Gross channel / gross payload / RS goodput / application rates,
application payload utilisation per frame, CRC and unique-frame delivery, RS
corrections and packet loss, decode latency, baseline repeatability, bottleneck
attribution.

**Procedure.** Read only locked physical sessions (no session or run is
modified). Decode every preserved camera sample with the standard decoder,
count unique `(packet_id, frame_index)` frames, reconstruct the payload, and
compare its SHA-256 with the transmitted hash. Compute every rate with the
observed display period as the denominator. Compute the per-frame utilisation
and the exact loss decomposition. Aggregate independent baseline sessions;
separate throughput repeatability from optical sample reliability. Report
measured values and arithmetic projections under different labels.

**Result (E12 run `20261108T114711Z-2064a2`, 7 sessions).** Four sessions
delivered the complete SHA-verified payload: the M9 reference and three
independent M10 baselines. All four measured the same normalised rates at
9.999 fps: **1,199.88 bps** gross channel, **879.91 bps** gross payload,
**769.49 bps** RS(255,223) goodput and **99.44 bps** application. The
application carries **1.243 bytes per displayed frame out of 11 (11.30%)**;
wire packet fill is **11.99%** and application packet fill **12.92%**. The
channel-to-application gap of **1,100.44 bps** decomposes into framing
319.97 bps, RS parity 110.42 bps and unused packet capacity 677.27 bps, with
compression recovering 7.21 bps. The narrower RS-to-application gap is
**670.05 bps** (unused capacity minus compression gain). Primary bottleneck:
**unused packet capacity (56.4% of the channel)**; framing second (26.7%); RS
parity third (9.2%). Camera capture (3.00× headroom), decode (4.46× headroom),
RS correction (zero in the reference) and packet loss (1/1) are not limiting.

Baseline repeatability: payload success **3/3**, normalised-rate CV **0.0**.
Unique-frame delivery was 255/255, 255/255 and 246/255; the last produced 9
erasures and 18 corrected symbols. Camera-sample CRC rate varied from 0.618 to
0.889, so sample CRC rate is not a frame-coverage metric. Decode mean was
7.26–7.71 ms/sample. `frame_delivery_all_exact` is `false` and is reported
separately from throughput repeatability.

Factor coverage: display brightness was set and read back at **0.650** and
**0.900** `DisplayServices` fractions (not nits). Both sessions lost the top
fiducials to hand-held framing drift after about 14 s (455 and 457 `E_DETECT`
failures; delivery 0.686 and 0.573), so they failed the packet and **no
brightness effect is claimed**. Distance, camera angle and ambient illuminance
are **UNMEASURED**.

**Projection — not measured.** At 60 fps (arithmetic only): the same 317-byte
payload would carry 596.71 bps application; a full packet-0 payload (2,421 B)
4,557.18 bps; the maximum 16-packet transfer (39,216 B) 4,613.65 bps. No 60 fps
physical capture exists.

**Comparison.** The measured rates equal E01 arithmetic at the observed display
rate exactly. The 60 fps headline arithmetic (5,280 bps gross payload,
4,617 bps RS goodput) remains theoretical. E12 shows that at the 317-byte
payload size the dominant physical/applications gap is packet fill, not
decoder speed or RS correction.

## E13 — Packet utilisation optimisation

**Hypothesis.** The frozen 11.99% wire packet fill is unused capacity, not
protocol loss, and filling packet 0 with real data (or packing several payloads
into one packet) raises application throughput without breaking the frozen
frame format, RS layer or decoder.

**Method.** `experiments/e13_packet_utilisation.py` builds six deterministic
arms from `experiments/m11_payloads.py`, round-trips each through the real
packet/RS/container code, and analyses every locked `m11-*` physical session.
Payloads are generated byte-for-byte by `scripts/m11_prepare.py`; each physical
session commits the arm manifest under `session.transmitter.m11` before
finalization. Evidence gates reject any session whose payload SHA-256 does not
match, and a failed capture is retained and reported separately rather than
deleted.

**Root cause.** A packet is 255 frames × 11 bytes = 2,453 RS data bytes. The
frozen M9 payload is 317 application bytes → 294 wire bytes after `OTL1`, so
2,159 of 2,453 data bytes are zero padding. 11.99% is a payload-size property
of a fixed container; the padding is still RS-encoded and displayed.

**Software arms (stated 10 fps).**

| Arm | Change | Application B | Wire B | Packets | App bps |
| --- | --- | ---: | ---: | ---: | ---: |
| A0 | frozen reference | 317 | 294 | 1 | 99.45 |
| A1 | fill packet 0 + adaptive raw | 2,421 | 2,421 | 1 | 759.53 |
| A2 | four-payload `OTB1` bundle, 15-byte header | 2,280 | 2,361 | 1 | 715.29 |
| A3 | shared dictionary, 145,745 B payload | 145,745 | 2,420 | 1 | 45,723.92* |
| A4 | same payload as A1, always-on `OTL1` | 2,421 | 2,450 | 2 | 379.76 |
| A5 | `nsym=24`, 15-byte header, adaptive raw | 2,526 | 2,526 | 1 | 792.47 |

\* pre-compression application bytes; wire payload rate 758.91 bps. The
dictionary is compression gain, not extra channel capacity.

**Physical result (run `20261108T125654Z-e5001c`, 5 successful sessions).**

| Arm | Session | Unique frames | Erased | Corrected | App bps | Wire fill |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A0 | `m11-a0-reference-20261108T122331Z` | 247/255 | 8 | 8 | 99.44 | 11.99% |
| A1 | `m11-a1-fill-adaptive-20261108T122956Z` | 249/255 | 6 | 66 | 759.45 | 98.70% |
| A2 | `m11-a2-bundle-20261108T123222Z` | 248/255 | 7 | 77 | 715.22 | 96.25% |
| A3 | `m11-a3-dictionary-20261108T123444Z` | 255/255 | 0 | 0 | 45,705.64* | 98.65% |
| A5 | `m11-a5-rs24-20261108T123758Z` | 245/255 | 10 | 110 | 792.39 | 99.41% |

\* pre-compression application bytes; wire payload 758.91 bps. A4
(`always_on`) has no physical session and is not promoted.

Measured gains over the frozen 99.441 bps: A1 **7.637×**, A2 **7.192×** (four
payloads verified independently), A5 **7.968×** and **1.04337×** over A1 at the
same 255 frames. The A5 software and physical ratios agree to five significant
figures, confirming the capacity arithmetic (105 extra bytes = 88 RS parity +
17 header).

**Reliability.** Every successful arm matched its manifest SHA-256. Worst
erasure count was 10 (A5) against `nsym=24`, leaving 14 erasures of margin;
A3 delivered 255/255 frames with zero erasures and zero corrections. One A1
attempt where the phone was aimed away from the display (6/255 unique frames)
is retained as a failed capture, not deleted.

**Loss accounting.** E13 closes
`channel − application = framing + RS parity + file header + unused padding +
encoding overhead` to a floating-point residual for every arm (0.0 or ~1e−12
bps). Once the packet is full, the dominant loss switches from
`unused_packet_padding` to `framing_header_and_crc`.

**Not measured.** A4 physical throughput and multi-packet physical delivery
(the 510-frame two-packet capture), 60 fps, distance, angle, ambient
illuminance and absolute nits. See
[`M11_PACKET_UTILISATION.md`](M11_PACKET_UTILISATION.md).

## Cross-experiment summary

| Claim | Status | Experiment |
| --- | --- | --- |
| 120 raw bits / 88 payload bits / 11 bytes per frame | THEORETICAL | E01 |
| 4,617 bps RS goodput at 60 fps | THEORETICAL | E01 |
| 39,216-byte maximum transfer | THEORETICAL | E01 |
| 16 cell patterns separable in clean–extreme simulated channels | OBSERVED (SIMULATED) | E02 |
| Single-frame boundaries: brightness 0.08, perspective 0.18; no failure to blur σ 16, noise σ 90, vignette 0.9 | OBSERVED (SIMULATED) | E03 |
| Resolution boundary 0.06 scale (8.58 px/cell); perspective boundary 0.12 | OBSERVED (SIMULATED) | E04 |
| 32 lost frames recoverable, 33 not | OBSERVED (SOFTWARE) | E05 |
| `2e + r ≤ 32` boundary, over-capacity rejected | OBSERVED (SOFTWARE) | E06 |
| `OTL1` exact roundtrip; 58.5× on zeros, 0.98× on random | OBSERVED (SOFTWARE) | E07 |
| 26-chip word needs readout ≥ 26 symbols and exposure ≤ 1 symbol | OBSERVED (SIMULATED) + THEORETICAL | E08 |
| 60 Hz display cannot carry a 26-chip word in one capture | REJECTED | E08 |
| Full pipeline: 48/64 transfers; clean/mild/harsh 16/16 each, brutal 0/16 | OBSERVED (SIMULATED) | E09 |
| A second full run reproduces the same payload and outcome fingerprints | OBSERVED (SOFTWARE) | E09 |
| Deterministic render/decode/pipeline; decoder camera-independent | OBSERVED (SOFTWARE) | E10 |
| Screen → camera path implemented and exercised on real raster data | OBSERVED (PHYSICAL / CAMERA CAPTURE) | E11 |
| iPhone14,2 camera decodes displayed FULL16 frames at cell/bit accuracy 1.000 | OBSERVED (PHYSICAL / CAMERA CAPTURE) | E11 still + packet |
| Full 255-frame packet survives the physical link; 317-byte payload SHA-256 matches | OBSERVED (PHYSICAL / CAMERA CAPTURE) | E11 packet |
| Three independent baseline repeats recover the exact payload at identical normalised rates | OBSERVED (PHYSICAL / CAMERA CAPTURE) | E12 |
| Application payload utilisation is 11.30%/frame; unused packet capacity is the dominant loss (677.27 bps, 56.4% of channel) | OBSERVED (PHYSICAL / CAMERA CAPTURE) + THEORETICAL | E12 |
| Capture, decode, RS correction and packet loss are not limiting at the 317-byte payload | OBSERVED (PHYSICAL / CAMERA CAPTURE) | E12 |
| Display brightness affects physical reliability | UNMEASURED | E12 brightness attempts failed from framing drift |
| The 11.99% wire fill is unused packet capacity, not protocol loss | OBSERVED (PHYSICAL) + THEORETICAL | E13 |
| Filling packet 0 with incompressible data raises measured application throughput 7.64× | OBSERVED (PHYSICAL / CAMERA CAPTURE) | E13 |
| Four logical payloads share one 255-frame packet with per-entry SHA-256 verification | OBSERVED (PHYSICAL / CAMERA CAPTURE) | E13 |
| The shared dictionary recovers 145,745 bytes from one packet | OBSERVED (PHYSICAL / CAMERA CAPTURE) | E13 |
| `nsym=24` adds 105 payload bytes (+4.34%) at the same frame count, leaving 14 measured erasure margin | OBSERVED (PHYSICAL / CAMERA CAPTURE) | E13 |
| Adaptive raw/OTL1 is 2× the always-on path for incompressible data | OBSERVED (SOFTWARE) only | E13 A4 has no physical session |
| The link works at 60 fps | UNMEASURED (PROJECTION only) | E12, E13 |
| Simulated results predict a real phone link at other distances/angles | HYPOTHESIS | none yet |

No experiment in this repository is `VERIFIED` in the physical sense. See
`MEASUREMENT_POLICY.md` and `HARDWARE_PLAN.md`.
