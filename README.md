# OPTICAL_TRANSMISSION_LAB (OTL)

> **Repository note.** This research archive is published on GitHub as
> **LoveQR**. The product architecture, remaining M11 work and LoveQR roadmap
> are in [`docs/M11_HANDOFF_AND_LOVEQR.md`](docs/M11_HANDOFF_AND_LOVEQR.md)
> and [`TODO.md`](TODO.md). The raw camera evidence (about 37 GB) is retained
> outside git; its hashes are recorded in each session's
> `captures/index.jsonl` and `session.lock.json`.

A reproducible research and engineering lab for **screen-to-camera optical data
transmission** using ordinary smartphone cameras: optical camera communication
(OCC), visible-light communication (VLC), rolling-shutter capture, dynamic
spatial codes and a shared instruction dictionary.

The repository contains a complete, typed Python implementation of a proposed
30-cell / 120-bit spatial frame, its transmitter, simulated optical channel,
detector, decoder, Reed–Solomon packet layer, compression container, CLI and a
set of controlled experiments (E01–E13). Every run is append-only and every
number is labelled with its evidence level.

> **Evidence status.** The M9 transmitter player, receiver capture/session
> layer and E11 analysis are implemented and exercised. A real iPhone14,2
> camera has viewed the macOS display and decoded the signal: the still burst
> contained one unique image that decoded at CRC 1/1 and cell/bit accuracy
> 1.000, and a full 255-frame packet decoded
> 255/255 unique frames at accuracy 1.000 with 0 RS corrections and a
> SHA-256-matched 317-byte payload. E11 reports `PHYSICAL / CAMERA CAPTURE` for
> both finalized sessions. M10 repeated the frozen packet three more times:
> all three recovered the exact payload at identical normalised rates
> (1,199.88 bps channel, 769.49 bps RS goodput, 99.44 bps application), while
> camera-sample CRC and frame coverage varied. E12 measures **11.30%**
> application payload utilisation per frame and attributes the dominant loss
> (677.27 bps, 56.4% of the channel) to unused packet capacity, not to capture,
> decode or RS correction. Decode is still software. All optical results from
> E01–E10 are **OBSERVED on a simulated channel** or **THEORETICAL** arithmetic.
>
> **M11 removed the packet-fill bottleneck.** The frozen transfer uses 11.99%
> of the 2,453-byte packet, and the rest is zero padding, not protocol loss.
> Filling packet 0 with 2,421 incompressible bytes raises measured application
> throughput from **99.44 bps to 759.45 bps (7.64×)**; capacity-aware
> `nsym=24` reaches **792.39 bps (7.97×)** with 14 erasures of margin; four
> logical payloads share one packet at **715.22 bps**; and a shared dictionary
> recovers **145,745 bytes** from one packet with **255/255 unique frames and
> zero erasures**. Five of six arms are physically measured; the always-on
> control (A4) is software-only. One failed A1 attempt is retained. `VERIFIED`
> is reserved for a measurement with a named device, date, raw capture and
> reproduction command. See
> [`docs/MEASUREMENT_POLICY.md`](docs/MEASUREMENT_POLICY.md),
> [`docs/M9_PHYSICAL_VALIDATION.md`](docs/M9_PHYSICAL_VALIDATION.md),
> [`docs/M10_CHANNEL_EFFICIENCY.md`](docs/M10_CHANNEL_EFFICIENCY.md) and
> [`docs/M11_PACKET_UTILISATION.md`](docs/M11_PACKET_UTILISATION.md).

---

## What is implemented

| Layer | Module | Responsibility |
| --- | --- | --- |
| Codec | `otl/codec/patterns.py` | 16 four-triangle cell patterns, Hamming distance, control alphabets |
| Frame | `otl/protocol/frame.py` | 16-bit header + 11 data bytes + CRC-16 → 30 cells |
| Packet | `otl/protocol/packet.py` | 32-byte file header, 11× RS(255,223), byte interleaving, reassembly |
| Blink | `otl/protocol/blink.py` | Barker-13 sync + three low-cross-correlation IDs |
| ECC | `otl/ecc/crc.py`, `otl/ecc/rs.py` | CRC-16/CCITT-FALSE, CRC-32, clean-room GF(256) RS with erasures |
| Compression | `otl/compress/dictionary.py` | Deterministic `OTL1` container: LIT/REPEAT/COPY/INVERT/SEQUENCE |
| Adaptive + M11 codec | `otl/compress/adaptive.py`, `otl/protocol/m11.py` | Raw/OTL1 selection, 15-byte compact header, capacity-aware `nsym`, `OTB1` multi-payload bundle |
| TX | `otl/tx/renderer.py`, `player.py` | Deterministic cached tile renderer, fiducials, solid outer border; full-screen HTML player with frame manifest |
| RX | `otl/rx/channel.py`, `detect.py`, `rolling.py`, `sync.py`, `capture.py`, `session.py` | Synthetic channel, fiducial detection, rectification, sampling; camera capture, byte-preserving import, physical session |
| Decoder | `otl/decoder/spatial.py`, `temporal.py` | Image → cells → frame; blink/band decoding |
| Pipeline | `otl/pipeline.py` | End-to-end simulated transfer with structured errors and timings |
| Metrics | `otl/metrics.py` | Timer, throughput, BER, aggregation, CPU/RSS sampling |
| CLI | `otl/cli.py` | `manifest`, `info`, `render`, `decode`, `transfer-sim`, `selftest`, `play`, `capture`, `session` |

## Protocol at a glance

- **Spatial frame:** 6 × 5 cells, 4 bits per cell = **120 raw bits**.
  - 16-bit header: 4-bit packet id + 12-bit frame index.
  - 88-bit payload: **11 bytes per frame**.
  - 16-bit CRC-16/CCITT-FALSE over header + data.
- **Packet:** exactly 255 frames × 11 bytes = 2805 bytes = 11 × RS(255,223).
  - Frame *n* carries byte *n* of every RS block, so a lost frame is one
    erasure in every block.
  - `nsym = 32`: up to 16 unknown byte errors, or 32 erasures, or
    `2·errors + erasures ≤ 32` per block.
- **File header:** 32 bytes (magic `OT`, version, flags, packet id, total
  packets, original/payload lengths, CRC-32, 13-byte UTF-8 name).
- **Capacity:** packet 0 carries 2421 payload bytes, later packets 2453;
  a 4-bit packet id caps a transfer at 16 packets = **39,216 bytes** before
  compression.
- **Temporal layer:** 26-chip word = 13-chip Barker-13 sync + 13-chip ID.
  A rolling-shutter capture sees `height × row_time / symbol_period` display
  symbols; exposure must also be no longer than one symbol period.
- **Compression:** `OTL1` is a small, deterministic, inspectable instruction
  stream. It does not claim to beat zlib/zstd on general data.

### Headline arithmetic (THEORETICAL, 60 display frames/s)

| Quantity | Value |
| --- | ---: |
| Raw bits per frame | 120 |
| Payload bits per frame | 88 |
| Payload bytes per frame | 11 |
| Raw rate | 7,200 bps |
| Framed payload rate | 5,280 bps |
| RS(255,223) goodput | 4,617 bps |
| One packet on screen | 4.25 s |
| Maximum pre-compression transfer | 39,216 bytes |

Software timings and simulated-channel results vary by host and are reported
per run under [`results/`](results/SUMMARY.md).

## Quick start

Python **3.11+** is required; the development host used Python 3.14.

```bash
cd OPTICAL_TRANSMISSION_LAB
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.lock
python3 -m pip install -e . --no-deps
```

Run the fast internal checks and the full test suite:

```bash
python3 -m otl selftest
python3 -m pytest
```

Render a payload to PNG frames and decode one back without a camera:

```bash
python3 -m otl render --text "hello optical world" --name hello.txt --out /tmp/otl_frames --limit 3
python3 -m otl decode /tmp/otl_frames/p00_f000.png --out /tmp/otl_decode.json
```

Run a complete simulated transfer:

```bash
python3 -m otl transfer-sim --text "hello" --channel mild --drop 0.03
python3 -m otl manifest
```

Run experiments (append-only; each invocation creates a new run directory):

```bash
python3 -m experiments.run_all --list
python3 -m experiments.run_all --only E01_capacity --quick
python3 -m experiments.run_all --all
```

`make` targets wrap the same commands; see [`Makefile`](Makefile).

## Physical capture (M9/M10)

The transmitter is a deterministic HTML player; the receiver is a camera
capture or a phone import into a hash-checked session.

```bash
# Build a real displayable player from rendered frames.
python3 -m otl render --text "hello" --out demo/frames --limit 1
python3 -m otl play demo/frames --out demo/player_hold.html \
    --no-embed --hold --autostart --frame 0

# Inspect cameras, then capture (macOS AVFoundation via ffmpeg).
python3 -m otl capture list
python3 -m otl capture still 1 --out datasets/physical/raw --frames 10

# Create, populate, validate, lock and analyze a session.
python3 -m otl session new m9-demo --root datasets/physical \
    --source camera --device-model "iPhone" --display-model "MacBook display" \
    --mode photo --resolution 1920x1440
python3 -m otl session attach datasets/physical/m9-demo \
    --frames demo/frames --player-manifest demo/player_manifest.json
python3 -m otl session ingest datasets/physical/m9-demo \
    datasets/physical/raw/still_*/raw_010.png --frame 0:0
python3 -m otl session validate datasets/physical/m9-demo
python3 -m otl session finalize datasets/physical/m9-demo
python3 -m experiments.run_all --only E11_physical \
    --session datasets/physical/m9-demo
```

A physical label requires a finalized session with `capture_source = camera` or
`manual-import`. Fixtures and screen captures are labelled
`SOFTWARE FIXTURE (NOT PHYSICAL)`. The measured M9 sessions are in
`datasets/physical/`; full instructions and metadata requirements are in
[`docs/PHYSICAL_CAPTURE.md`](docs/PHYSICAL_CAPTURE.md).

M10 adds five further locked sessions under `datasets/physical/` (three
baseline repeats and two brightness attempts) and the E12 analysis:

```bash
python3 -m experiments.run_all --only E12_channel_efficiency
python3 scripts/display_brightness.py --get
```

E12 reads finalized sessions read-only and reports measured values separately
from 60 fps projections. See
[`docs/M10_CHANNEL_EFFICIENCY.md`](docs/M10_CHANNEL_EFFICIENCY.md).

## Repository layout

```text
OPTICAL_TRANSMISSION_LAB/
├── otl/                  # production library (typed, deterministic)
├── tests/                # unit, integration, regression and CLI tests
├── experiments/          # E01–E13 implementations + append-only harness
│   └── E0x_*/runs/       # immutable run directories (raw + processed + report)
├── results/              # latest-run index and summary (derived)
├── datasets/             # physical sessions, failed probes, fixtures, corpora
├── docs/                 # research, protocol, architecture, policy, licences
├── scripts/              # checksum and verification helpers
├── pyproject.toml
├── requirements.lock     # pinned environment
├── Makefile
└── bootstrap.sh
```

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/RESEARCH.md`](docs/RESEARCH.md) | Literature review, primary sources, what is novel here |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layer boundaries, data flow, interfaces, determinism |
| [`docs/PROTOCOL.md`](docs/PROTOCOL.md) | Bit layouts, CRC, RS, packetisation, blink codebook, capacity |
| [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) | E01–E13 hypotheses, methods, results, failures |
| [`docs/REPRODUCE.md`](docs/REPRODUCE.md) | Exact environment and reproduction steps |
| [`docs/MEASUREMENT_POLICY.md`](docs/MEASUREMENT_POLICY.md) | Evidence classes and reporting rules |
| [`docs/PHYSICAL_CAPTURE.md`](docs/PHYSICAL_CAPTURE.md) | TX/RX interfaces, session layout, exact camera workflow |
| [`docs/M9_PHYSICAL_VALIDATION.md`](docs/M9_PHYSICAL_VALIDATION.md) | M9 report: physical still and packet results, comparison, history |
| [`docs/M10_CHANNEL_EFFICIENCY.md`](docs/M10_CHANNEL_EFFICIENCY.md) | M10 report: baseline repeats, per-frame utilisation, loss decomposition, bottleneck |
| [`docs/M11_PACKET_UTILISATION.md`](docs/M11_PACKET_UTILISATION.md) | M11 report: packet-fill root cause, six arms, measured gains, reliability |
| [`docs/M11_HANDOFF_AND_LOVEQR.md`](docs/M11_HANDOFF_AND_LOVEQR.md) | M11 finish plan and LoveQR product architecture |
| [`TODO.md`](TODO.md) | Ordered remaining work for M11 and LoveQR |
| [`docs/HARDWARE_PLAN.md`](docs/HARDWARE_PLAN.md) | Physical-capture plan, devices, controls, raw-data policy |
| [`docs/LICENCES.md`](docs/LICENCES.md) | Project and third-party licences, provenance |
| [`docs/STATUS.md`](docs/STATUS.md) | Current milestone, verified/observed/rejected claims |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Design decisions and rejected alternatives |
| [`docs/MILESTONES.md`](docs/MILESTONES.md) | Incremental milestone history and next steps |

## Limitations (read before citing)

1. **The physical result is one device pair and one short packet.** An
   iPhone14,2 camera decoded the display in one indoor setting: a still burst
   whose unique image decoded at CRC 1/1 and cell/bit accuracy 1.000, a
   255/255 full packet with a SHA-verified 317-byte payload, and three M10
   baseline repeats that recovered the same payload at identical normalised
   rates. Distance, angle, ambient illuminance, absolute luminance, battery,
   thermal behaviour and sustained multi-packet throughput were not measured,
   so no physical boundary is claimed. Display brightness was varied only as a
   0–1 controller fraction, and both brightness attempts failed from hand-held
   framing drift. M11's 7.6–8.0× gains are measured on the same single device
   pair; its A4 multi-packet arm and 60 fps remain unmeasured. E01–E10 optics
   results still use a synthetic channel.
2. **The channel model is not a calibrated camera.** It applies perspective,
   photometric shifts, blur, noise, vignetting and JPEG, but not demosaicing,
   rolling-shutter row exposure during a spatial frame, motion blur from hand
   shake, auto-exposure transients, or display gamma measured from a device.
3. **FULL16 has minimum Hamming distance 1.** A single triangle error changes
   the nibble; the frame CRC and RS layer provide protection, not the alphabet.
4. **The 4-bit packet id caps a transfer at 16 packets.** This is a protocol
   property, not a tunable.
5. **Temporal blink IDs need a fast display.** A 26-chip word does not fit in a
   60 Hz display capture; the measured/arithmetic constraint is documented in
   E08.
6. **`OTL1` is not a general-purpose compressor.** It is a deterministic
   instruction dictionary for the optical link.

## Licence

MIT. See [`LICENSE`](LICENSE) and [`docs/LICENCES.md`](docs/LICENCES.md).
