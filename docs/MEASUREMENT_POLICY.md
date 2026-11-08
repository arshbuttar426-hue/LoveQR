# Measurement and evidence policy

This project separates **what was measured** from **what was derived** and from
**what is still a proposal**. The rule is enforced in code
(`otl/types.py::Classification`, `otl/types.py::MeasurementSource`) and in every
experiment report.

## Evidence classes

| Class | Meaning | Allowed sources |
| --- | --- | --- |
| `VERIFIED` | A physical measurement with a named device, date, raw capture and reproduction command. | Real screen + real camera only. |
| `OBSERVED` | Measured in this project, but not a physical optical link. | Simulated channel, software timing, prerecorded images. |
| `THEORETICAL` | Derived from protocol arithmetic, information theory or a timing model. | Hand calculation / closed form. |
| `HYPOTHESIS` | Proposed and not yet tested. | Design documents, issue tracker. |
| `REJECTED` | Tested and failed; the failure is retained. | Experiment run with a recorded failure. |

`OBSERVED` is **not** a synonym for `VERIFIED`. A result produced by
`otl/rx/channel.py` is always `OBSERVED (SIMULATED)` and every report says so in
its header and manifest.

## Rules

1. **Never fabricate.** A number must come from executed code, a retained raw
   file, or an explicitly shown arithmetic derivation.
2. **Never overwrite raw data.** Each experiment invocation creates
   `experiments/<id>/runs/<UTC timestamp>-<nonce>/`. Only `LATEST` and the
   derived `results/` index are replaced.
3. **Record failures.** A failed run is data. The harness writes raw trials
   while running, then a traceback and a `REPORT.md` that states the run did not
   complete.
4. **Separate measured from theoretical.** E01 and E08 report arithmetic and
   software timings side by side, labelled separately.
5. **Separate software time from screen time.** `simulate_transfer` measures
   Python wall time. Projected screen time is `frames / display_fps` and is
   labelled `projected_*`.
6. **Name the device or say “none”.** Physical captures require `device`,
   `date`, `distance`, `angle`, `ambient light`, `brightness` and raw file
   hashes. Every software run records `simulation_only: true`; runs made after
   the final harness revision also record `device: null`, and every report
   header states `SIMULATED / SOFTWARE (no physical camera)`. Older run
   directories in this repository predate the explicit `device` field but carry
   `simulation_only: true` and the same report header.
7. **Do not claim a limit that was not reached.** If a sweep never fails, the
   report says “no failure inside the tested range”, not “robust”.
8. **Do not claim generality from one host.** CPU, memory and latency are
   host-specific; the environment block is embedded in every manifest.

## M9 evidence labels

M9 adds explicit labels that are carried into `manifest.json`,
`processed/summary.json` and `REPORT.md`:

| Label | Meaning |
| --- | --- |
| `PHYSICAL / CAMERA CAPTURE` | Finalized session with `capture_source` `camera` or `manual-import`; images are real camera bytes. Decoding is still software. |
| `SOFTWARE FIXTURE (NOT PHYSICAL)` | Finalized session with `capture_source = fixture`; useful for ingestion/geometry tests only. |
| `BLOCKED / NO PHYSICAL CAPTURE` | No session, invalid session, draft session, or no camera line of sight. No accuracy/throughput is claimed. |

Two M9 sessions and five M10 sessions currently carry
`PHYSICAL / CAMERA CAPTURE` under `datasets/physical/`: the M9 still burst and
packet, three M10 baseline repeats and two M10 brightness attempts. They have a
named device, display, date, preserved raw files, hashes and reproduction
commands. The M9 sessions do **not** have measured distance, angle, ambient
illuminance or display brightness. The M10 sessions measure brightness only as
a `DisplayServices` controller fraction (0–1), not as luminance in nits; both
brightness attempts lost fiducials to framing drift, so no brightness effect is
claimed. Distance, angle and ambient illuminance remain null. None of these
sessions is `VERIFIED` under this policy because the geometry/environment
fields are incomplete. Missing fields are recorded as null, never guessed.

M10 adds one more label to the E12 report: `PROJECTION — not measured` for
arithmetic rows such as 60 fps throughput. A projection is never counted as a
physical observation, even when its arithmetic uses measured payload bytes.

M11 adds a rule for optimisation arms: an arm is `PHYSICAL / CAMERA CAPTURE`
only when its locked session exists and its payload SHA-256 matches. An arm
that was only encoded and round-tripped in software is `OBSERVED (SOFTWARE)`
and must be named as such even when the arithmetic comparison is exact. A
failed capture (for example the A1 session where the phone was aimed away from
the display) is retained as a locked session, listed by E13 as a failed row
with a reason, and excluded from measured throughput. It is never deleted and
never silently replaced by a re-run. Five M11 arms are physical; A4
(`always_on`, 510 frames) has no physical session, so its 2× adaptive ratio is
software-only.

A physical result is not `VERIFIED` until the run directory contains:

- `raw/` or `captures/originals/` original image or video files, unmodified,
  with SHA-256 hashes;
- transmitter device model, display technology, resolution, refresh rate,
  brightness setting and colour profile;
- receiver device model, camera app or API, resolution, frame rate, exposure,
  ISO, focus mode and orientation;
- geometry: distance, horizontal/vertical angle, screen-to-camera alignment;
- environment: ambient illuminance (lux), colour temperature, flicker sources;
- timestamp and operator;
- the exact command that reproduced the decode from the raw files.

`datasets/physical/` is reserved for finalized sessions. Failed setup probes
belong under `datasets/physical/attempts/` and are not E11 sessions. Fixtures
belong under `datasets/fixtures/`. See `docs/PHYSICAL_CAPTURE.md` for the full
workflow.
