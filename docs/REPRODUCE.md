# Reproduction guide

This document lets another person or coding agent reproduce every result in the
repository from the folder alone. It assumes no prior state and no network
access beyond installing the pinned packages once.

## 1. Host used for the recorded results

| Item | Value |
| --- | --- |
| OS | macOS (Darwin), Apple silicon |
| CPU | Apple M5 |
| Python | 3.14.7 (Clang 21.0.0) |
| numpy | 2.4.4 |
| opencv-python | 4.13.0.92 |
| Pillow | 12.2.0 |
| pytest | 9.0.3 |
| zstandard | 0.25.0 |
| Package | `optical-transmission-lab` 0.1.0 |

The environment block is embedded in every `manifest.json`; the values above
are not assumptions about your machine. Results that depend on timing, CPU or
memory will differ on another host and are labelled as such.

## 2. Clean install

```bash
cd OPTICAL_TRANSMISSION_LAB
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.lock
python3 -m pip install -e . --no-deps
```

Or run the wrapper, which does the same and finishes with a selftest:

```bash
./bootstrap.sh
```

`requirements.lock` pins direct and transitive dependencies. `pip install -e .
--no-deps` is deliberate: the lockfile, not the package metadata, decides the
environment.

### Offline install

If the packages are already available in a local wheelhouse:

```bash
python3 -m pip install --no-index --find-links /path/to/wheels -r requirements.lock
python3 -m pip install --no-index --no-deps -e .
```

## 3. Verify the source

```bash
python3 scripts/checksums.py --verify
```

The manifest covers source files only. It deliberately excludes append-only
experiment runs, caches and the derived `results/` index. Regenerate it after
an intentional source change:

```bash
python3 scripts/checksums.py --write
```

### Verify that a re-run reproduces a run

`E09_end_to_end` records its payload generator, every seed, every payload
SHA-256, a `payload_manifest_sha256` and an `outcome_sha256`. Compare the two
newest complete runs with:

```bash
python3 scripts/verify_rerun.py --experiment E09_end_to_end
```

Exit status is `0` only when the payload set and the outcome set are identical.
Wall-clock, CPU, RSS and latency are excluded because they depend on host load;
everything that defines the result (payload bytes, success flag, frame counters,
error stages) is compared. Use `--help` for the explicit two-directory form.

## 4. Fast checks

```bash
python3 -m otl selftest      # dependency-free smoke checks, JSON output
python3 -m pytest            # 169 tests
```

Expected: `selftest` exits 0 with all checks `ok`; pytest exits 0. The suite is
deterministic; timing and RSS assertions are bounds, not exact values.

## 5. Protocol and pipeline inspection

```bash
python3 -m otl manifest
python3 -m otl info
```

`manifest` prints the frame arithmetic, packet capacity, RS parameters and
codebook metrics. `info` prints the default configuration and version.

## 6. Render and decode without a camera

```bash
python3 -m otl render --text "hello optical world" --name hello.txt \
    --out /tmp/otl_frames --limit 3
python3 -m otl decode /tmp/otl_frames/p00_f000.png --out /tmp/otl_decode.json
```

The decoder accepts a PNG or JPEG path, so it can be tested on prerecorded
captures. `--limit` is only for a quick look; omit it to render a full file.

## 7. End-to-end simulated transfer

```bash
python3 -m otl transfer-sim --text "hello" --channel mild --drop 0.03
python3 -m otl transfer-sim --bytes 6000 --channel brutal
```

Exit codes: `0` success, `2` expected OTL error (structured JSON on stderr),
`3` the transfer ran but did not verify. A non-zero exit is a result, not a
crash; keep the JSON.

## 8. Experiments

List, run one, run all:

```bash
python3 -m experiments.run_all --list
python3 -m experiments.run_all --only E01_capacity
python3 -m experiments.run_all --only E08_rolling --quick
python3 -m experiments.run_all --all
```

Every invocation creates a new immutable run directory:

```text
experiments/<id>/runs/<UTC timestamp>-<nonce>/
├── manifest.json        spec, environment, wall time, failures
├── raw/trials.jsonl     one JSON object per trial, flushed while running
├── processed/summary.json
├── processed/summary.csv
├── REPORT.md
├── figures/             (reserved)
└── artifacts/           images/hashes produced by the experiment
```

`experiments/<id>/LATEST` points at the newest run. `results/index.json`,
`results/runs.jsonl` and `results/SUMMARY.md` are derived indexes; they are the
only files a run replaces.

### Expected wall time (recorded host, full mode)

| Experiment | Trials | Wall time |
| --- | ---: | ---: |
| E01_capacity | 33 | 0.04 s |
| E02_patterns | 80 | 9.27 s |
| E03_frame_robustness | 69 | 8.62 s |
| E04_geometry | 21 | 2.20 s |
| E05_erasures | 138 | 1.50 s |
| E06_errors | 72 | 1.02 s |
| E07_compression | 30 | 0.19 s |
| E08_rolling | 60 | 1.95 s |
| E09_end_to_end | 64 | 556.7 s (~9 min 17 s) |
| E10_determinism | 3 | 4.56 s |

E09 dominates because it renders and decodes hundreds of frames per trial. Its
64 full-mode trials take about nine minutes on the recorded host; two runs are
recorded so the rerun check can compare them. These are software wall times on
the recorded host, not screen time.

## 9. Interpreting a run

1. Open `REPORT.md` for the hypothesis, procedure, summary, failures and
   conclusion.
2. Open `processed/summary.json` for machine-readable aggregates.
3. Open `raw/trials.jsonl` for every trial, including failed ones.
4. Check `manifest.json` for `simulation_only`, environment and wall time.
5. Check `failures`: an empty list means the code did not raise, not that every
   trial succeeded. Per-trial success is in the raw JSONL and the CSV.

## 10. Reproduce a single reported number

Example: E05's "first failure at 33 lost frames".

```bash
python3 -m experiments.run_all --only E05_erasures
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("experiments/E05_erasures")
rid = (p / "LATEST").read_text().strip()
rows = [json.loads(l) for l in (p / "runs" / rid / "raw" / "trials.jsonl").read_text().splitlines()]
for r in rows:
    if r["config"]["lost_frames"] in (32, 33):
        print(r["config"], r["outputs"]["success"])
PY
```

The same pattern works for every experiment: the raw JSONL is the source of
truth and the summary is a derived aggregate.

## 11. Clean-room verification

The project does not vendor third-party source. To confirm:

```bash
find . -name '*.py' -not -path './.venv/*' -not -path './experiments/*/runs/*' \
    -exec grep -l 'Copyright' {} +
```

Only the project's own files should appear. `docs/LICENCES.md` records the
licence of every dependency and the basis of every algorithm.

## 12. Adding an experiment

1. Create `experiments/eXX_name.py` with a `run(ctx)` and an `ExperimentSpec`.
2. Call `ctx.record(...)` for every trial and `ctx.conclude(...)` once.
3. Add the spec to `experiments/registry.py`.
4. Run `python3 -m experiments.run_all --only EXX_name --quick`, then full.
5. Do not edit an existing run directory. Re-running creates a new one.

## 13. Common problems

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: otl` | package not installed and not on `PYTHONPATH` | `pip install -e . --no-deps`, or run from the project root. |
| `E_DETECT` on a real photo | fiducials cropped, merged or out of frame | capture the whole screen with margin; check `docs/HARDWARE_PLAN.md`. |
| `E_SYNC` on a temporal capture | flat sequence or exposure longer than one symbol | lock exposure; check `timing_report`. |
| `E_RECONSTRUCT` | more lost frames than RS capacity, or missing packet 0 | keep frame loss ≤ 32 per packet; retain packet 0. |
| `E_PROTOCOL` name too long | 13-byte header name limit | use a shorter file name. |
| E09 is slow | it renders/decodes a full packet per trial | run `--quick`, or run E09 alone. |
| Checksum mismatch after editing docs | manifest is stale | `python3 scripts/checksums.py --write`. |

## 14. Physical capture (M9/M10)

The transmitter player, camera capture, session, E11 and E12 commands are:

```bash
# Build a displayable player (already committed under datasets/physical/demo).
python3 -m otl play datasets/physical/demo/frames \
  --out /tmp/otl_player.html --no-embed --hold --autostart --frame 0

# Enumerate cameras and capture.
python3 -m otl capture list
python3 -m otl capture still 1 --out /tmp/otl_raw --frames 10

# Session lifecycle.
python3 -m otl session new m9-demo --root /tmp/otl_sessions \
  --source camera --device-model "iPhone" --display-model "MacBook display" \
  --mode photo --resolution 1920x1440
python3 -m otl session attach /tmp/otl_sessions/m9-demo \
  --frames datasets/physical/demo/frames \
  --player-manifest datasets/physical/demo/player_manifest.json
python3 -m otl session ingest /tmp/otl_sessions/m9-demo \
  /tmp/otl_raw/still_*/raw_010.png --frame 0:0
python3 -m otl session validate /tmp/otl_sessions/m9-demo
python3 -m otl session finalize /tmp/otl_sessions/m9-demo
python3 -m experiments.run_all --only E11_physical \
  --session /tmp/otl_sessions/m9-demo
```

The measured sessions can be re-analysed without a camera:

```bash
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/m9-iphone14-2-20261108T103717Z
python3 -m experiments.run_all --only E11_physical \
  --session datasets/physical/m9-iphone14-2-packet-20261108T104529Z

# E12 analyses every locked M9/M10 session (read-only).
python3 -m experiments.run_all --only E12_channel_efficiency
python3 -m experiments.run_all --only E12_channel_efficiency \
  --sessions datasets/physical/m10-baseline-01-20261108T112241Z,datasets/physical/m10-baseline-02-20261108T112441Z
```

Brightness instrumentation on macOS reports a controller fraction, not nits:

```bash
python3 scripts/display_brightness.py --get
python3 scripts/display_brightness.py --set 0.65
```

The preserved camera files are authoritative. A screen capture or rendered PNG
is a `SOFTWARE FIXTURE`, never physical evidence. See
`docs/PHYSICAL_CAPTURE.md`, `docs/M9_PHYSICAL_VALIDATION.md` and
`docs/M10_CHANNEL_EFFICIENCY.md`.

### M11 packet-utilisation arms

The M11 arms are deterministic, so their software round-trip can be reproduced
without a camera:

```bash
# build one arm (frames + frozen-M9 player + manifest)
python3 scripts/m11_prepare.py --arm A1_fill_adaptive \
  --out datasets/physical/m11-staging/A1_fill_adaptive --fps 10

# re-analyse every locked m11-* session
python3 -m experiments.run_all --only E13_packet_utilisation

# focus one session
python3 -m experiments.run_all --only E13_packet_utilisation \
  --sessions datasets/physical/m11-a1-fill-adaptive-20261108T122956Z

# M11 unit tests
python3 -m pytest tests/test_m11_packet_utilisation.py -q
```

A new physical arm uses `scripts/m11_capture_arm.py` with an existing Safari
window id; see `docs/PHYSICAL_CAPTURE.md` §4.8. The canonical E13 run is
`experiments/E13_packet_utilisation/runs/20261108T125654Z-e5001c/`.

## 15. What cannot be reproduced here

The optical results from E01–E10 are produced by `otl/rx/channel.py` and
`otl/rx/rolling.py`; they are simulated, not measurements of a real device. The
M9/M10/M11 physical results are specific to one iPhone14,2, one display and one
indoor setup; distance, angle, ambient illuminance and absolute luminance,
battery and thermal behaviour were not measured and cannot be reproduced from
the stored sessions. Display brightness was recorded only as a `DisplayServices`
controller fraction in the M10 attempts, both of which failed from framing
drift. M11's A4 (always-on, two-packet) arm has no physical session, so its 2×
adaptive-vs-always-on ratio is software-only. To capture a new physical result,
follow `docs/PHYSICAL_CAPTURE.md`, retain the raw files and finalize the
session.
