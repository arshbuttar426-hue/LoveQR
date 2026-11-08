# Design decisions

Each decision records the alternatives that were considered and why they were
rejected. Decisions are reversible only with a new entry; the history is not
rewritten.

## D01 — Python 3.11+ with a pinned lockfile

**Decision.** Implement the lab in Python with `numpy`, `opencv-python`,
`Pillow`, `pytest` and optional `zstandard`, pinned in `requirements.lock`.

**Alternatives.** C++/Rust for speed; JavaScript for a browser demo.

**Why.** The bottleneck of this project is experiment turnaround and
reproducibility, not raw decoder throughput. Python keeps the protocol,
channel and analysis in one auditable language and lets another agent run the
whole lab from the folder. A compiled core can replace `otl.decoder` later
without changing the wire format.

## D02 — 4 bits per cell, 30 cells, 120-bit frame (FULL16)

**Decision.** A cell is four independently black/white triangles (16 patterns,
4 bits). The frame is 6 × 5 = 30 cells = 120 bits: 16-bit header, 88-bit data,
16-bit CRC.

**Alternatives.** Binary cells (1 bit/cell, 30 bits/frame); 8-level grey cells;
colour cells (e.g. RGB 8-colour); larger grids.

**Why.** FULL16 is the architecture under test and is easy to render and sample
deterministically. Binary cells were rejected because they do not exercise the
proposed 16-pattern alphabet. Colour was rejected for the first milestone
because it introduces display/camera colour calibration that would confound the
geometry and timing results. The grid size is fixed by the proposal; changing
it would change the protocol, not an implementation detail.

**Consequence.** Minimum Hamming distance is 1, so a single triangle error is a
nibble error. Protection comes from CRC-16 and Reed–Solomon, not the alphabet.
This is stated in `README.md`, `docs/PROTOCOL.md` and E02.

## D03 — 16-bit header = 4-bit packet id + 12-bit frame index

**Decision.** The frame header carries a 4-bit packet id and a 12-bit frame
index.

**Alternative.** 8-bit packet id + 8-bit frame index.

**Why.** A packet is 255 frames, so 12 bits cover the frame index with room to
spare; 4 bits give 16 packets, which is the capacity ceiling of the protocol
(39,216 bytes). This was chosen to match the proposed design and to keep the
header at two bytes. The ceiling is documented, not hidden.

**Rejected alternative.** Variable-length headers or an out-of-band packet
manifest: they add state and a second channel, which the proposal does not
have.

## D04 — Packet = 255 frames × 11 bytes with 11 × RS(255,223)

**Decision.** Each packet is exactly 255 frames. Its 2453-byte payload region is
split into 11 RS(255,223) blocks and byte-interleaved, so frame *n* carries
byte *n* of every block. `nsym = 32`.

**Alternatives.** RS(255,239) (nsym = 16); per-frame RS; fountain codes; no ECC.

**Why.** Interleaving turns a lost frame into exactly one erasure in every
block, which matches the dominant failure mode of a screen–camera link (whole
frames lost to sync/exposure). `nsym = 32` tolerates 32 lost frames per packet,
which is a useful margin for a 255-frame packet and still leaves 223 data bytes
per block. `nsym = 16` would tolerate only 16 lost frames (6.3%); a fountain
code would add complexity and non-determinism for a first milestone. Per-frame
RS would waste parity on frames that are already CRC-protected and would not
exploit interleaving.

**Consequence.** The packet layer is deterministic and testable in isolation
(E05, E06). Over-capacity input raises `E_ECC`; it never returns silent
corruption.

## D05 — CRC-16/CCITT-FALSE per frame, CRC-32 per file

**Decision.** CRC-16/CCITT-FALSE (poly `0x1021`, init `0xFFFF`, no reflection,
xorout 0) over header + data. CRC-32 (zlib polynomial) over the compressed
payload.

**Alternatives.** CRC-32 per frame; Fletcher-16; no frame CRC.

**Why.** CRC-16 fits the 120-bit frame and detects the error patterns the
channel produces. A 32-bit frame CRC would cost 16 payload bits (two bytes per
frame, ~18% of payload). Fletcher-16 is weaker for burst errors. The file CRC-32
is the end-to-end integrity check and is independent of the frame layer.

## D06 — Clean-room Reed–Solomon instead of `reedsolo`

**Decision.** Implement GF(256) RS in `otl/ecc/rs.py`; do not depend on
`reedsolo`.

**Alternatives.** `reedsolo`, `unireedsolomon`, a C library binding.

**Why.** Licence audit and determinism. The implementation is small, pure
Python, pinned to primitive polynomial `0x11D`, and tested against known
properties (errors, erasures, mixed, over-capacity). A third-party dependency
would add a licence and a version surface for ~400 lines of standard
mathematics. The algorithm is classical and clean-room; see `docs/LICENCES.md`.

## D07 — `OTL1` instruction container, not zlib/zstd

**Decision.** Define a small deterministic container with `LIT`, `REP`, `CPY`,
`INV`, `SEQ`.

**Alternatives.** zlib/deflate, zstd, LZ4, no compression.

**Why.** The proposal calls for a *shared instruction dictionary* with
REPEAT/COPY/INVERT/SEQUENCE, and the decoder must be inspectable and
deterministic. zlib/zstd are used only as reference points in E07. The container
is not claimed to beat general-purpose compressors; it is a protocol component.

**Consequence.** `OTL1` is versioned (`OTL1`, version 1) and every operand is
validated. A future opcode requires a version bump.

## D08 — Barker-13 sync and three searched IDs

**Decision.** A 26-chip word = Barker-13 sync + one of three 13-chip IDs. The
IDs are selected by `search_codebook()` under a sidelobe/cross-correlation
criterion.

**Alternatives.** A single long PN sequence; Golay pairs; a fixed table copied
from a paper.

**Why.** Barker-13 has the lowest possible aperiodic autocorrelation sidelobes
(±1) for its length, which makes sync detection robust. Three short IDs keep
the word at 26 chips. The search is deterministic and documented, so the
codebook can be reproduced without copying a table. A single long PN sequence
would make ID detection a joint search and increase latency.

## D09 — Fixed geometry in `otl/config.py`

**Decision.** `ScreenConfig` is the single source of truth: 1080 × 1350 canvas,
6 × 5 cells, 8 px gaps, 90 px margin, 48 px fiducials, 10 px border, 4×
supersampling.

**Alternatives.** Geometry computed ad hoc in the renderer and detector.

**Why.** Transmitter and receiver must agree on triangle centroids. Deriving
both from `Layout.triangle_polygon()` / `triangle_centroid()` makes a
disagreement a unit-test failure rather than a mysterious decode error.

**Consequence.** Changing the canvas or grid is a protocol change and requires
re-running E01–E10.

## D10 — Simulated channel is explicitly labelled

**Decision.** `otl/rx/channel.py` is a synthetic model. Every experiment
manifest contains `"simulation_only": true`; every report states
`SIMULATED / SOFTWARE`.

**Alternatives.** Call the results "measured"; omit the label for readability.

**Why.** The project's central epistemic rule is that `VERIFIED` requires a
physical capture with device, date, raw file and reproduction command. Without
that label, a reader could mistake a synthetic blur sweep for a phone result.
See `docs/MEASUREMENT_POLICY.md`.

## D11 — Append-only experiment runs

**Decision.** Each invocation creates
`experiments/<id>/runs/<UTC timestamp>-<nonce>/`; only `LATEST` and the derived
`results/` index are replaced.

**Alternatives.** Overwrite a single `results.json`; use git branches per run.

**Why.** Failed runs and raw trials are data. Overwriting destroys the ability
to audit a conclusion. A timestamp + nonce avoids collisions when two runs start
in the same second. The harness writes `raw/trials.jsonl` while running, so a
crash still leaves usable data.

## D12 — Decoder has no camera dependency

**Decision.** `decode_image(image, layout, receiver, protocol)` accepts any
grayscale array or image path. The camera only produces an array.

**Alternatives.** A decoder coupled to a capture class or a live camera loop.

**Why.** It makes the decoder testable on prerecorded PNG/JPEG, reproducible in
CI, and usable for physical captures without code changes. E10 verifies that
the same image decodes identically twice.

## D13 — Photometric references from fiducials and data area

**Decision.** `reference_levels()` combines fiducial percentiles with data-area
percentiles, taking `min(lows)` and `max(highs)`.

**Alternatives.** Fixed 0/255 thresholds; Otsu on the whole image; per-cell
Otsu only.

**Why.** Fixed thresholds fail under brightness/gamma/ambient changes. Whole-
image Otsu fails when the payload is mostly one colour. Per-cell Otsu fails for
all-black/all-white cells. The combined reference survives all-black,
all-white and inverted frames and is tested in `test_detect.py`.

## D14 — Border ring outside the fiducials

**Decision.** The renderer draws a solid border ring outside the fiducials with
a white gap between the ring and the data area.

**Alternatives.** No border; border touching the fiducials.

**Why.** A border that touches the fiducials merges them into one connected
component and breaks detection. A separate ring gives the detector a stable
outer boundary without changing the fiducial geometry. The gap is part of the
layout and is tested by the renderer regression hash.

## D15 — Quick and full modes in one experiment definition

**Decision.** Every experiment accepts `--quick`, which reduces sweep sizes but
does not change the code path.

**Alternatives.** Separate quick scripts.

**Why.** A separate script drifts from the full experiment. One definition with
a size switch means a quick run exercises the same measurement code as a full
run; only the number of levels changes.

## D16 — No git repository in the working folder

**Decision.** The project is delivered as a plain folder; checksums are provided
by `CHECKSUMS.sha256` rather than a git commit.

**Alternatives.** Initialise a git repository and tag a commit.

**Why.** The working folder is not a git repository and the deliverable must be
self-contained. The checksum manifest gives an equivalent integrity check for
source files and is verifiable with `sha256sum -c`.

## D17 — Deterministic payloads inside experiments

**Decision.** Every experiment generates its "random" payloads from a seeded
generator (`numpy.random.default_rng(seed)`), never from `os.urandom`. The
SHA-256 of each payload is still recorded in the raw trial.

**Alternatives.** `os.urandom` for a stronger notion of randomness; a fixed
byte-repeated block for every size.

**Why.** Re-running an experiment must reproduce the same input bytes, otherwise
a reported success rate cannot be checked against a stored run. A repeated
4096-byte block is worse: it makes the "random" corpus compressible by block
repetition and inflated E07's ratio, so E07 now generates fresh bytes per size.
`os.urandom` was found in E09 during the reproducibility audit and replaced;
the affected run is retained as historical data and superseded by a new run.

## D18 — Experiment metadata and reproducibility fingerprints

**Decision.** `RunContext.metadata` is serialised into both `manifest.json`
(`experiment_metadata`) and `processed/summary.json`. E09 records its payload
generator, every seed, every payload SHA-256, a `payload_manifest_sha256` over
the payload set and an `outcome_sha256` over the per-trial outcomes.
`scripts/verify_rerun.py` compares two runs on exactly those fingerprints.

**Alternatives.** Put the generator details only in the report prose; trust that
a re-run is reproducible without checking.

**Why.** A reported success rate is only auditable if the inputs can be
regenerated and the outcomes compared. The fingerprints make the check a
one-command operation and let the comparison ignore wall-clock and CPU numbers,
which legitimately differ between runs. A re-run that produces the same two
fingerprints has reproduced the payloads and the outcomes; one that does not is
a visible mismatch instead of an unnoticed drift.

## D19 — Image-relative fiducial quadrants

**Decision.** `find_fiducials` assigns candidate fiducials to quadrants of the
**captured image**, not of the canonical 1080×1350 canvas. The score uses
distance to the corresponding image corner plus an area penalty.

**Alternatives.** Keep the canonical-canvas quadrants and require the screen to
fill the frame; add a separate camera-only detector.

**Why.** The first real display capture (2560×1664, screen occupying a centered
region) produced four correct fiducials but failed the canvas-relative
quadrant test. A phone photo always contains background around the screen, so
canvas-relative quadrants cannot work. The change is geometric, not a protocol
change, and the existing detector tests still pass.

## D20 — A physical claim requires a finalized session

**Decision.** E11 labels a session `PHYSICAL / CAMERA CAPTURE` only when
`capture_source` is `camera` or `manual-import`, `status == "final"` and
`session.lock.json` exists. A draft is `BLOCKED / NO PHYSICAL CAPTURE`.

**Alternatives.** Analyze drafts for convenience and label them later.

**Why.** Finalization is the step that hashes the manifest and captures and
freezes the session. Without it, a draft could be edited after the report was
written. Requiring the lock makes the evidence claim mechanically checkable.

## D21 — Fixtures are labelled, never promoted

**Decision.** `capture_source = "fixture"` is always
`SOFTWARE FIXTURE (NOT PHYSICAL)`, even if the fixture is a real screen capture
or a rendered PNG ingested through the same path. Only `camera` or
`manual-import` can become physical.

**Alternatives.** Treat a screen capture as "physical display" evidence.

**Why.** An OS screen capture bypasses the lens, sensor, focus, exposure and
rolling shutter. It is useful for testing ingestion and geometry, but calling
it physical would overstate the result. The label is part of the session and is
carried into every E11 report.

## D22 — A cell threshold needs real cell contrast

**Decision.** A cell gets its own black/white threshold only when its local
span is at least `local_threshold_fraction` (default 0.5) of the frame's
black-to-white span, in addition to the existing `min_contrast` test. Otherwise
the frame-global threshold is used.

**Alternatives.** Raise `min_contrast`; use a fixed absolute threshold; smooth
the samples more.

**Why.** The first physical camera images decoded with cell accuracy 0.70
because solid dark cells carried about 20 grey levels of sensor noise. The old
rule treated any local span above 8 % of 255 as a real black/white boundary and
split that noise into a false triangle in 9 of 20 solid cells. A real FULL16
cell contains both triangle colours and spans most of the frame range, so the
fraction test separates signal from noise. The frame format, packet layout,
Reed–Solomon, compression, renderer and decoder geometry are unchanged. The
physical still frames then decoded at cell/bit accuracy 1.000 and the
full packet decoded 255/255 frames with zero RS corrections. Regression test:
`tests/test_detect.py::test_solid_cells_do_not_turn_sensor_noise_into_triangles`.

## D23 — Physical throughput counts displayed frames, not camera samples

**Decision.** E11 reports frame delivery and throughput using unique
`(packet_id, frame_index)` values. A camera sample that repeats an already
delivered frame is retained in the raw trial list but is not new data. Rate
calculations use the observed display period, measured from the timestamps of
first appearances, and the payload is decompressed before its SHA-256 is
compared with the original file.

**Alternatives.** Divide by the 30 fps camera rate; count every decoded frame;
compare the compressed bytes with the original payload hash.

**Why.** A 30 fps camera sees each 10 fps display frame about three times, so
counting camera samples would triple the apparent throughput. The first video
reassembly also compared the compressed 294-byte wire payload with the 317-byte
original and reported a false mismatch, even though the bytes were perfect.
With unique-frame accounting and decompression, the measured packet is
255/255 frames, 0 erasures, 0 RS corrections and a matching SHA-256; the
measured 9.999 display fps makes the normalized rates match E01 arithmetic at
the same rate exactly.

## D24 — Every physical rate uses the observed display period

**Decision.** E12 computes gross channel, gross payload, RS goodput and
application throughput with one shared denominator: the packet duration
`255 / observed_display_fps`. Per-frame utilisation divides application bytes
by the 11 payload bytes actually carried in one displayed frame. Packet fill
divides by the 2,453 RS data bytes (or 2,421 for packet 0). The loss identity
is

```
channel − application
    = framing + RS parity + unused packet capacity − compression gain
```

and is checked to a zero residual.

**Alternatives.** Divide by the camera frame rate; use the raw panel refresh;
report bits per camera sample; quote application throughput without stating a
denominator.

**Why.** A 30 fps camera sees each 10 fps display frame about three times, so
camera-based denominators inflate or deflate every rate. The 60 Hz panel is not
the playback rate either. Using the observed display period makes the measured
rates match E01 arithmetic exactly and makes the three baseline repeats
directly comparable. It also separates the two different gaps: framing and RS
parity sit above RS goodput, while the RS-to-application gap is unused packet
capacity minus compression gain.

## D25 — Brightness is a controller fraction, not luminance

**Decision.** Display brightness is recorded only as a `DisplayServices`
fraction in 0–1, read back at the start and end of a session. E12 reports it as
**MEASURED (instrument readback)** and never converts it to nits. Distance,
camera angle and ambient illuminance remain `UNMEASURED` unless a calibrated
instrument supplies a value.

**Alternatives.** Treat the macOS brightness slider as a physical luminance;
infer distance from image size; estimate lux from the camera exposure.

**Why.** The fraction is a controller setting, not a photometric quantity, and
it is not comparable across displays. Inferring distance or lux from image
content would be a projection, not a measurement. When a factor was varied but
the capture was corrupted (the two brightness sessions lost fiducials to
framing drift), E12 marks the comparison **NOT INTERPRETABLE** rather than
attributing the failure to brightness.

## D26 — Repeatability is claimed for payload and rates, not for sample CRC

**Decision.** A baseline set is `repeatable` when at least two independent
physical sessions deliver the complete SHA-verified payload and the normalised
throughput metrics agree within 1% CV. Perfect unique-frame delivery is
reported separately as `frame_delivery_all_exact`. Camera-sample CRC rate is
reported as a reliability indicator, never as the repeatability criterion.

**Alternatives.** Require every session to have 100% frame delivery; judge
success by CRC-valid sample fraction.

**Why.** RS(255,223) is designed to absorb lost frames. In M10 one baseline
delivered only 246/255 frames and still recovered the exact payload after 9
erasures and 18 corrections; another delivered 255/255 at a lower sample CRC
rate (0.618). Sample CRC rate and frame coverage are different quantities, and
a criterion based on either alone would misstate what repeated. Reporting both
the payload/rate repeatability and the frame-delivery spread keeps the claim
honest.

## D27 — The frozen protocol is extended additively, never edited in place

**Decision.** M11 code lives in `otl/protocol/m11.py` and
`otl/compress/adaptive.py`. `otl/protocol/packet.py`, the frame codec, the
renderer, the player and the decoder keep their M9 defaults and behaviour.
Every M11 feature is opt-in through an explicit arm or parameter.

**Alternatives.** Edit `packet.py` to accept a variable header size; change the
default `nsym`; make adaptive compression the default.

**Why.** M9 and M10 evidence is frozen and must remain re-analysable with the
same code. An additive module lets E13 compare the original and optimised
paths with one import each, keeps the 183-test suite meaningful, and avoids
silently changing a baseline that documented physical results depend on.

## D28 — Packet fill is unused capacity, not a loss mechanism

**Decision.** Report packet utilisation against the fixed 2,453-byte data
region and name the remainder `unused_packet_padding`. The frozen 11.99% is
explained as payload size, not as decoding failure or protocol overhead.

**Alternatives.** Call the gap "protocol overhead"; quote application bytes per
displayed frame only; count padding as an error-correction cost.

**Why.** The packet is always 255 frames × 11 bytes. Padding bytes are
RS-encoded and displayed, so they consume channel time, but they are not a
loss the receiver causes and they disappear when a larger payload is used.
Separating `unused_packet_padding` from framing and parity makes the E12 and
E13 loss identities agree and identifies the real optimisation: fill the
container before trying to shrink the frame.

## D29 — Capacity-aware `nsym` must retain measured erasure margin

**Decision.** Ship `nsym=32` as the reference and expose `nsym=24` as the
physical safe arm. `nsym=16` exists in the capacity table but is not used for a
physical claim. An arm is only `OBSERVED (PHYSICAL)` when its payload SHA-256
matches and its erasure count stays below `nsym`.

**Alternatives.** Use `nsym=16` for the largest payload; choose `nsym` from
theory alone; report the 4.34% capacity gain without the reliability cost.

**Why.** The M10 worst case was 9 erasures. `nsym=24` keeps 15 erasures of
headroom against that baseline and measured 10 erasures with 14 of margin in
A5. `nsym=16` would have left only 7 erasures of baseline headroom and no
measured margin. The gain and the reliability are reported together so the
trade-off cannot be quoted one-sided.

## D30 — A failed capture is retained and reported, not deleted

**Decision.** Keep `m11-a1-fill-adaptive-20261108T122602Z` (6/255 unique
frames, payload failed) as a locked session. E13 lists it as a failed row with
a reason and excludes it from measured throughput. Software arms without a
locked physical session are labelled `OBSERVED (SOFTWARE)` and never promoted.

**Alternatives.** Delete the failed session; silently re-run until one succeeds;
treat the best attempt per arm as the result.

**Why.** The failure is real evidence about hand-held framing and capture
repeatability. Deleting it would make the success rate look better than it was,
and promoting software round-trips would blur the meaning of `PHYSICAL`. The
policy is the same one M10 used for its confounded brightness sessions.

## D31 — LoveQR is a separate product repository, not a rename

**Decision.** Keep `OPTICAL_TRANSMISSION_LAB` as the frozen research archive
with its evidence, and create `LoveQR` as a new product repository that depends
on the M11 codec rather than re-implementing it.

**Alternatives.** Rename this repository; vendor a copy of the lab code into the
product; keep product UI in the lab.

**Why.** The lab's value is its append-only evidence and reproduction commands;
a product needs a stable public API, packaging, demo assets and a UI that would
otherwise pollute the experiment tree. A separate repository with a pinned
dependency keeps both auditable and lets the product version independently.
