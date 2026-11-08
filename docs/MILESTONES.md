# Milestones

Incremental history of the project. Each milestone lists what was researched,
implemented, tested, the actual result, the problems found, and what came next.
Later milestones do not rewrite earlier results.

## M0 — Environment and literature

**Researched.** Screen–camera communication (COBRA, Strata, LightSync, HiLight,
InFrame++, ChromaCode), rolling-shutter receivers (Danakis, Luxapose, VRCodes),
standards (IEEE 802.15.7, ITU-T G.9991), coding (Reed–Solomon, Barker, LZ),
flicker perception.

**Implemented.** Directory tree, `pyproject.toml`, MIT `LICENSE`, package
skeleton (`otl/__init__.py`, `errors.py`, `types.py`, `logging.py`,
`config.py`).

**Tested.** Import and configuration validation; geometry arithmetic.

**Result.** Python 3.14.7 on Apple M5 macOS; pinned numpy 2.4.4,
opencv-python 4.13.0.92, Pillow 12.2.0, pytest 9.0.3, zstandard 0.25.0.

**Problems.** No physical hardware was available. Decision: all optical results
are simulated and labelled `OBSERVED (SIMULATED)`; `VERIFIED` is reserved for a
physical capture.

**Next.** Implement the protocol.

## M1 — Cell alphabet, CRC and compression

**Implemented.** `otl/codec/patterns.py` (16 four-triangle patterns, Hamming
distance, `PARITY8`/`BALANCED6` control alphabets), `otl/ecc/crc.py`
(CRC-16/CCITT-FALSE, CRC-32), `otl/compress/dictionary.py` (`OTL1` with
LIT/REP/CPY/INV/SEQ).

**Tested.** CRC check value `123456789` → `0x29B1`; exact `OTL1` roundtrip on
empty, repetitive, sequential, random, inverted, text and mixed payloads.

**Result.** All unit tests passed. `OTL1` is deterministic and validates every
operand.

**Problems.** `INV` and `SEQ` needed explicit operand bounds to avoid
out-of-range copies; fixed with validation and tests.

**Next.** Reed–Solomon and the frame/packet layers.

## M2 — Reed–Solomon and packet layer

**Implemented.** Clean-room GF(256) RS(255,223), `nsym = 32`, systematic
encoding, errors + erasures. `otl/protocol/frame.py` (120-bit frame),
`otl/protocol/packet.py` (32-byte file header, 11 blocks, byte interleaving,
reassembly), `otl/protocol/blink.py` (Barker-13 + three searched IDs).

**Tested.** Errors-only, erasures-only (1…32), mixed `2e + r ≤ 32`; over-
capacity raises `E_ECC`. Frame packing/unpacking and CRC. Packet capacity and
interleaving. Blink autocorrelation and cross-correlation.

**Result.** RS capacity boundary is exactly `nsym = 32`. Packet 0 capacity 2421
bytes, later packets 2453, maximum 39,216 bytes.

**Problems.** The syndrome convention and Forney magnitude indexing had to be
fixed so erasure-only and mixed cases agree. The 4-bit packet id was found to
cap the transfer at 16 packets; documented rather than silently extended.

**Next.** Transmitter, channel and decoder.

## M3 — Renderer, synthetic channel and decoder

**Implemented.** `otl/tx/renderer.py` (cached tiles, fiducials, solid outer
border, supersampling), `otl/rx/channel.py` (perspective, blur, noise,
vignette, brightness, gamma, ambient, JPEG), `otl/rx/detect.py` (fiducial
detection, homography, sampling, reference levels), `otl/rx/rolling.py`
(rolling-shutter row integration), `otl/rx/sync.py`,
`otl/decoder/spatial.py`, `otl/decoder/temporal.py`.

**Tested.** Renderer determinism and golden hash; fiducial detection; all-black
and all-white payloads; rolling-shutter word recovery.

**Result.** Renderer golden SHA-256
`fb306fd6b2a3c281c5c344378abec246e1f823421837c36637c2b84672272413`.

**Problems.**
- The first rolling-shutter implementation used a tensordot that sampled the
  wrong axis; replaced with `np.einsum("rs,srw->rw", weights, stack)` and a
  shape assertion in `tests/test_temporal.py`.
- The classifier failed on all-black/all-white payloads with a fixed threshold;
  fixed by `reference_levels()` combining fiducials and data-area percentiles.
- A border touching the fiducials merged components; fixed with a separated
  ring and a white gap.
- Exposure longer than one symbol period integrated several chips; the timing
  report now includes `exposure_us`, `exposure_over_period`,
  `exposure_within_symbol` and `temporal_budget_ok`.

**Next.** End-to-end pipeline and CLI.

## M4 — Pipeline and CLI

**Implemented.** `otl/pipeline.py` (compress → packetise → render → channel →
decode → RS → reassemble → decompress), `otl/metrics.py` (timer, throughput,
BER, aggregation, CPU/RSS), `otl/cli.py` + `otl/__main__.py` (`manifest`,
`info`, `render`, `decode`, `transfer-sim`, `selftest`).

**Tested.** Clean, degraded, all-zero/all-0xFF, text, random, multi-packet,
frame drop within RS capacity; over-capacity fails with `E_RECONSTRUCT`.

**Result.** End-to-end simulated transfers succeed; failures are structured and
never silently accepted.

**Problems.** macOS reports `ru_maxrss` in bytes, not KiB; normalised to KiB so
the field has one meaning across hosts.

**Next.** Experiment harness and E01–E10.

## M5 — Experiment harness

**Implemented.** `experiments/harness.py`, `common.py`, `registry.py`,
`run_all.py`. Append-only run directories with `manifest.json`,
`raw/trials.jsonl`, `processed/summary.json`, `processed/summary.csv`,
`REPORT.md`, `artifacts/`. `LATEST` pointer and a derived `results/` index.

**Tested.** Quick runs of E01–E10; crash path leaves raw trials and a
traceback.

**Result.** Each run is reproducible and auditable. Re-running never overwrites
an earlier run.

**Problems.** Duplicate loss counts in E05 were collapsed with
`tuple(sorted(set(range(0, 41, 2)) | {31, 32, 33, 34}))`. E09/E10 file names
exceeded the 13-byte header limit; shortened to `t<size>.bin` and `determ.bin`.

**Next.** Extend sweeps until failure boundaries were actually reached.

## M6 — Experiment hardening

**Implemented.** Extended E03 sweeps (blur to 16, brightness to 0.08,
perspective to 0.25, vignette to 0.9), E04 scales down to 0.02 and perspective
to 0.25, E08 exposure constraint, E09 data-driven conclusion, E06 capacity-33
mixed cases.

**Tested.** Full pytest suite; quick runs of every experiment.

**Result (quick runs, simulated).**

- E02: clean/mild/harsh/extreme target accuracy 1.0; brutal 0.331.
- E03 boundaries: blur_sigma 16, brightness 0.08, perspective 0.18,
  vignette 0.9; no failure inside the tested range for noise, JPEG, ambient or
  gamma.
- E04: resolution 0.06 scale (8.58 px/cell) succeeds, 0.04 (5.72 px/cell)
  fails; perspective 0.12 succeeds, 0.16 fails.
- E05: success through 32 lost frames, first failure at 33; random and burst
  identical.
- E06: 18 successes / 4 failures in quick mode; capacity boundary at 32.
- E07 mean ratios: zeros ~47.6×, repeat ~35.8×, alternating ~36.7×,
  text/inverted ~9.8×, random ~0.98×.
- E08: 39/39 correct when the temporal budget is satisfied; 3 failures at
  2500 µs exposure (2.5 symbols).
- E09: 8/8 success in quick mode.
- E10: 40/40 CRC OK; render/decode/pipeline deterministic; decode mean ~6.07 ms;
  max RSS ~120,464 KiB (normalised).

**Problems.** Direction-aware boundaries were wrong for JPEG quality, brightness
and resolution (lower is harder); fixed with explicit direction flags. E08
initially reported a "word fits" success at 2.5-symbol exposure; fixed by adding
the exposure constraint.

**Next.** Full runs, documentation, reproducibility tooling.

## M7 — Documentation and reproducibility

**Implemented.** `README.md`, `docs/RESEARCH.md`, `docs/ARCHITECTURE.md`,
`docs/PROTOCOL.md`, `docs/MEASUREMENT_POLICY.md`, `docs/EXPERIMENTS.md`,
`docs/REPRODUCE.md`, `docs/HARDWARE_PLAN.md`, `docs/LICENCES.md`,
`docs/STATUS.md`, `docs/DECISIONS.md`, `docs/MILESTONES.md`, `Makefile`,
`bootstrap.sh`, `scripts/checksums.py`, `CHECKSUMS.sha256`,
`requirements.lock`.

**Tested.** `python3 -m pytest`; `python3 -m otl selftest`; checksum
generation and verification; a clean virtual environment installed from
`requirements.lock`.

**Result.** The project can be reproduced from the folder alone.

**Problems.**
- `docs/REPRODUCE.md` first listed E07 at 0.17 s; the recorded full run is
  0.19 s. Corrected from the run data rather than left as an estimate.
- `scripts/checksums.py` did not cover `datasets/*.md`; added so the dataset
  policy file is covered by the manifest.

**Next.** Full runs and clean-venv verification (M8), then the physical phase
per `docs/HARDWARE_PLAN.md`.

## M8 — Full runs and rerun verification

**Implemented.** Deterministic E09 payloads (seeded `numpy` generator instead of
`os.urandom`), `RunContext.metadata` serialised into `manifest.json` and
`summary.json`, an explicit success/failure split with the failing stage of
every failed trial, per-payload SHA-256 verification, separate throughput,
latency and reconstruction-time aggregates, `scripts/verify_rerun.py`, and
`tests/test_experiments.py`.

**Tested.** Full runs of E01–E10; two complete full runs of E09; the rerun
comparison; `python3 -m pytest` (139 tests).

**Result (all SIMULATED / SOFTWARE).**

- E09: 48/64 transfers succeeded (75.0%). Clean, mild and harsh each 16/16;
  brutal 0/16, failing at frame CRC and then RS erasure capacity
  (`E_RECONSTRUCT` / `E_ECC`, 255 erasures against `nsym = 32`).
- E09 SHA-256: 64/64 payloads matched the pre-run manifest and 64/64 were
  re-derived identically; 0 mismatches.
- E09 rerun: `20261108T075737Z-98fd9f` and `20261108T080655Z-52295e` have the
  same `payload_manifest_sha256` and `outcome_sha256`; `verify_rerun.py`
  reports `IDENTICAL` with 64 trials in each run.
- E07: 30 trials, 0.19 s, random ratio 0.984 (range 0.972–0.992), zeros 58.5×,
  all roundtrips exact.
- E10: 3 trials, 4.56 s, 40/40 CRC OK, decode mean 5.80 ms, CPU 270%, peak RSS
  119,552 KiB.
- E01–E08 full-run numbers are in `docs/EXPERIMENTS.md` and
  `results/SUMMARY.md`.

**Problems.**
- `os.urandom` in E09 made the random payloads irreproducible; replaced and
  recorded in D17. The affected run is retained as historical data.
- E07 generated one 4096-byte random block and repeated it to 16384 bytes,
  inflating the ratio; fixed by generating each size independently (D17).
- `resource_sample` measured process-lifetime CPU/RSS, which attributed earlier
  experiments to E09/E10; replaced with `ResourceMeter` interval measurement.
- The harness manifest had no generator/seed block; added
  `experiment_metadata` so a run's inputs are auditable (D18).

**Verification.** A fresh virtualenv created from `requirements.lock` (Python
3.14.7) installs the package with `pip install -e . --no-deps`; inside it
`python3 -m otl selftest` returns `ok: true` and `python3 -m pytest` reports 139
passed. `scripts/checksums.py --write` covers 83 source files and
`--verify` passes. The package metadata now uses the PEP 639 form
(`license = "MIT"`, `license-files = ["LICENSE"]`) with
`setuptools>=77`, which removes the deprecated licence-table warning from the
build.

**Next.** The physical phase in `docs/HARDWARE_PLAN.md`.

## M9 — Physical optical validation

**Implemented.** Deterministic HTML transmitter player
(`otl/tx/player.py`), camera capture and byte-preserving ingestion
(`otl/rx/capture.py`), physical session schema/validation/locking
(`otl/rx/session.py`), E11 physical experiment
(`experiments/e11_physical.py`), CLI `play`/`capture`/`session`, harness
`--session` and per-run evidence/device overrides, and tests for the player,
preservation, locks, blocked and fixture evidence gates.

**Tested.** `python3 -m pytest` (161 tests). Two finalized iPhone camera
sessions are measured:

- Still: `m9-iphone14-2-20261108T103717Z` (E11 run
  `20261108T110718Z-bf6b16`), 15-frame 1920×1440 burst of held frame 0; one
  unique image (14 byte-identical duplicates), CRC 1/1, cell/bit accuracy
  1.000, decode 12.31 ms.
- Full packet: `m9-iphone14-2-packet-20261108T104529Z` (E11 run
  `20261108T110719Z-e6ad25`), 29 s video at 30 fps while the 255-frame packet
  looped at 10 fps. 869 camera samples, 816 CRC-valid (93.9%), 255/255 unique
  frames, cell/bit accuracy 1.000, 0 erasures, 0 RS corrections, payload 317
  bytes with matching SHA-256. Gross payload 879.91 bps, RS goodput 769.49 bps,
  application 99.44 bps at the observed 9.999 fps; decode 7.42 ms/sample.

Historical runs retained: fixture `20261108T102618Z-71f4e8` (software fixture,
not physical) and blocked `20261108T102619Z-b8b38b`.

**Result.**

- A real iPhone14,2 rear camera, viewing the macOS display through Continuity
  Camera at 1920×1440, decodes the displayed FULL16 frames. Every cell of every
  CRC-valid frame was correct.
- The full 255-frame packet survived the link: 255/255 unique frames, no
  packet loss, no RS corrections, and the reassembled payload matched the
  transmitted SHA-256 after decompression.
- Residual failures are frame availability (34 fiducial-detection failures, 19
  frame CRC errors across 869 samples), not cell classification.
- Normalized at the observed display rate, measured gross payload (879.91 bps)
  and RS goodput (769.49 bps) equal E01 arithmetic exactly.
- The earlier failed probe is preserved in
  `datasets/physical/attempts/20261108T101729Z-line-of-sight/`; the fixture is
  labelled `SOFTWARE FIXTURE (NOT PHYSICAL)`.

**Problems.**

- Fiducial quadrant assignment used canonical canvas coordinates, so a screen
  occupying part of a camera frame could not be located. Fixed to image-relative
  quadrants (D19).
- `session.lock.json` recorded `BLOCKED` for a finalized fixture because the
  evidence label was set after the lock was written. Fixed.
- E11 accepted draft sessions. It now requires a finalized session and a lock
  (D20), and refuses to label a fixture as physical (D21).
- Solid-cell sensor noise became a false triangle at cell accuracy 0.70. D22
  added a local-span fraction test; the same still then decoded at 1.000.
- Repeated camera samples inflated throughput and a compressed payload produced
  a false SHA mismatch. D23 counts unique frames and decompresses before
  hashing.
- Safari dropped the `?fps=` query when reusing a tab; setting `URL of front
  document` applied it. A smaller Safari window reduced fiducial size and
  failed; the full 1280×832 window was stable.

**Next.** Measure distance/angle/illuminance boundaries, sustained multi-packet
throughput and battery/thermal behaviour on more devices. The session workflow
in `docs/PHYSICAL_CAPTURE.md` and E11 need no code change.

## M10 — Physical channel efficiency and reliability

**Researched.** Where the measured physical throughput goes: framing, RS
parity, packet fill, compression, capture, decode, detection and RS correction.
Which physical factors can actually be measured on this host.

**Implemented.** E12 (`experiments/e12_channel_efficiency.py`) with exact rate
formulas, per-frame payload utilisation, an exact loss identity, baseline
repeatability statistics, factor coverage, brightness-series reporting,
bottleneck attribution and a measured-versus-projection split.
`scripts/display_brightness.py` reads/sets the macOS built-in display
brightness through `DisplayServices` as a 0–1 controller fraction (explicitly
not nits). `experiments/run_all.py` gained `--sessions` for E12.
`tests/test_e12_channel_efficiency.py` covers the arithmetic, gap identity,
projection label, brightness parser, factor coverage and evidence gates.

**Captured.** Five new locked camera sessions at the frozen M9 configuration:
three independent baselines
(`m10-baseline-01/02/03-20261108T112241Z/112441Z/112602Z`) and two brightness
attempts (`m10-brightness-065/090-20261108T112854Z/113031Z`).

**Tested.** `python3 -m pytest` → 169 passed; `python3 -m compileall -q otl
experiments scripts tests` → clean.

**Result.**

- Three baseline repeats recovered the exact 317-byte payload at identical
  normalised rates: 1,199.88 bps gross channel, 879.91 bps gross payload,
  769.49 bps RS goodput and 99.44 bps application at 9.999 fps.
- Application payload utilisation is **1.243 bytes of 11 per displayed frame
  (11.30%)**; wire packet fill is 11.99%, application packet fill 12.92%.
- The channel-to-application gap is 1,100.44 bps: framing 319.97 bps, RS parity
  110.42 bps, unused packet capacity 677.27 bps, minus 7.21 bps compression
  gain. The RS-to-application gap is 670.05 bps.
- Primary bottleneck: unused packet capacity (677.27 bps, 56.4% of channel).
  Framing is second, RS parity third. Camera capture has 3.00× headroom and
  decode 4.46× at the observed rates; RS correction and packet loss are not
  limiting.
- Repeatability: 3/3 payload success, throughput CV 0.0. Unique-frame delivery
  was 255/255, 255/255 and 246/255; the last used 9 erasures and 18 corrected
  symbols. Camera-sample CRC rate varied 0.618–0.889, confirming that sample
  CRC rate is not frame coverage.
- Brightness was varied at measured 0.650/0.900 controller fractions, but both
  sessions lost the top fiducials to hand-held framing drift after about 14 s
  (455/457 detection failures) and failed the packet. No brightness effect is
  claimed. Distance, angle and ambient illuminance remain UNMEASURED.
- 60 fps figures are **projections only**.

**Problems.**

- The brightness series is confounded. Both captures drifted out of frame in
  the second half; the failure is a receiver framing failure, not a brightness
  result. A fixed mount is required for factor isolation.
- One baseline lost 9 frames and needed 18 RS symbols even though its sample
  CRC rate was the highest (0.889). Counting CRC-valid samples alone would have
  hidden that.
- `Path.is_file()` reports false for the shared-cache `DisplayServices`
  framework symlink; the instrumentation loads it with `ctypes.CDLL` directly.
- The RS-to-application and channel-to-application gaps were initially
  conflated in the report text. E12 and its tests now enforce the exact
  identity; framing and RS parity sit above RS goodput.

**Next.** Repeat with a fixed camera mount and calibrated distance, angle and
lux instrumentation; then test larger payloads/multi-packet transfers and a
60 fps playback configuration. E12 analyses new locked sessions without code
changes.

## M11 — Packet-utilisation optimisation

**Goal.** Explain the 11.99% wire-packet fill measured by E12, then raise
application throughput without changing the frozen M9 frame format, renderer,
player, decoder geometry or RS(255,223) block size.

**What was done.**

- Added `otl/protocol/m11.py` (additive; `otl.protocol.packet` defaults remain
  M9): compact 15-byte file header, capacity-aware `nsym`, `OTB1` multi-payload
  bundle, and v2 packet encode/decode/reassemble helpers.
- Added `otl/compress/adaptive.py`: choose raw when `OTL1` would expand a
  payload, otherwise compress.
- Added `experiments/m11_payloads.py` with six deterministic arms
  (`A0_reference`, `A1_fill_adaptive`, `A2_bundle`, `A3_dictionary`,
  `A4_always_on`, `A5_rs24`), `scripts/m11_prepare.py` to render frames and the
  frozen-M9 player, `scripts/m11_capture_arm.py` to capture/finalize one arm,
  and `experiments/e13_packet_utilisation.py` to validate software arms and
  analyse locked `m11-*` sessions.
- Captured five physical arms with the iPhone14,2 Continuity Camera and the
  frozen `player.html?fps=10`. All five match their manifest SHA-256.

**Results (E13 run `20261108T125654Z-e5001c`).**

- Root cause: the packet is a fixed 2,453-byte container; the frozen payload is
  294 wire bytes. 2,159 data bytes are zero padding that is still RS-encoded
  and displayed.
- Filling packet 0 with adaptive raw data: **99.44 → 759.45 bps (7.637×)**,
  249/255 unique frames, 6 erasures.
- Capacity-aware `nsym=24`: **792.39 bps (7.968×)**, 245/255 frames, 10
  erasures against 24 correctable = 14 margin, and 1.04337× over A1 at the
  same 255 frames.
- `OTB1` bundle: **715.22 bps**, 4/4 entries independently SHA-verified,
  248/255 frames.
- Shared dictionary: **145,745 bytes in one packet**, 255/255 frames, zero
  erasures, zero corrections; wire payload 758.91 bps.
- A4 (always-on control) was not captured physically; its 2× penalty is
  software-only.

**Problems.**

- The hand-held phone moved between captures. One A1 attempt lost the display
  (6/255 unique frames) and is retained as a failed capture; a short
  pre-capture probe was added for later arms. Centre Stage was checked and is
  disabled; the drift is physical, not auto-framing.
- A4 needs a 510-frame two-packet capture (~57 s of held aim). It was deferred
  by the user, so multi-packet physical delivery remains unmeasured.
- Distance, angle, ambient lux, absolute nits and 60 fps remain UNMEASURED.

**Next.** Capture A4, re-run E13 without a session filter, regenerate
`CHECKSUMS.sha256`, and commit. Then start LoveQR; see
[`M11_HANDOFF_AND_LOVEQR.md`](M11_HANDOFF_AND_LOVEQR.md).

## Current status

The project is complete as a **software, simulation and first physical-link**
deliverable. The M9 transmitter/receiver/session/analysis path is complete, and
an iPhone camera has decoded a full packet with a SHA-verified payload. M10
froze that configuration, repeated the baseline three times and quantified the
efficiency bottleneck: 11.30% application payload utilisation per frame and
unused packet capacity as the dominant loss. M11 removed that bottleneck:
filling the packet and adapting compression raises measured application
throughput to 759–792 bps (7.6–8.0×), packs four payloads into one packet, and
recovers 145,745 bytes from one packet with a shared dictionary. Five of six
arms are physically measured; A4 (multi-packet control) is software-only. The
physical result is one device pair, one indoor setting and one short packet;
distance, angle, illuminance, absolute luminance, battery, thermal behaviour
and 60 fps are not measured. See
`docs/STATUS.md` for the claim-by-claim state,
`docs/M9_PHYSICAL_VALIDATION.md` for the M9 report,
`docs/M10_CHANNEL_EFFICIENCY.md` for the M10 report,
`docs/M11_PACKET_UTILISATION.md` for the M11 report and
`docs/PHYSICAL_CAPTURE.md` for commands.
