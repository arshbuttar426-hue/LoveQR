# E11_physical — Physical optical validation (screen → camera)

- Run: `20261108T102619Z-b8b38b`
- Classification: **BLOCKED — no physical camera capture available**
- Evidence source: **BLOCKED / NO PHYSICAL CAPTURE**
- Device: none (no physical capture)
- Trials: 1
- Wall time: 0.00 s
- Quick mode: False

## Hypothesis

The existing OTL frame, renderer and decoder can recover FULL16 frames from real smartphone-camera images of a screen, with cell accuracy and CRC success lower than the simulated clean channel because of optics, exposure, rolling shutter, moiré and hand motion.

## Controlled variables

- protocol
- layout
- renderer
- decoder
- display frame sequence
- capture settings

## Independent variables

- device
- display
- distance
- angle
- ambient light
- exposure/focus

## Dependent variables

- frame CRC success
- cell/bit accuracy
- payload reconstruction
- decode latency
- capture/decode rate
- throughput

## Procedure

1. Render the payload to PNG frames and build a full-screen player.
2. Record the exact displayed frames, their hashes and the player manifest.
3. Capture the screen with a named smartphone camera, preserving originals.
4. Import the originals into a session without re-encoding them.
5. Decode every preserved image with the standard OTL decoder.
6. Record CRC, cell/bit accuracy, packet reconstruction, latency and rate.
7. Compare physical observations with the E01–E10 simulation baselines.

## Experiment metadata

```json
{
  "evidence_source": "BLOCKED / NO PHYSICAL CAPTURE",
  "note": "No physical result was produced. Nothing in this run is a camera measurement; do not cite it as one.",
  "problems": [],
  "session": ""
}
```

## Processed results

```json
{
  "captures": 0,
  "evidence_source": "BLOCKED / NO PHYSICAL CAPTURE",
  "note": "No camera images were available. This run is not a simulation of a link and it is not a physical measurement; it records the missing prerequisite.",
  "problems": [],
  "reason": "no session directory under datasets/physical and no --session argument",
  "status": "blocked"
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

BLOCKED: no physical capture session was available. Reason: no session directory under datasets/physical and no --session argument. No decoding accuracy, throughput or latency is reported for a physical link because no physical link was measured. Capture a session with `otl session new`, `otl capture` or `otl session ingest`, then re-run `python3 -m experiments.run_all --only E11_physical --session <dir>`.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E11_physical
```

The run directory is immutable; re-running creates a new run id.

## Environment

```json
{
  "cpu_count": 10,
  "device": null,
  "evidence_source": "BLOCKED / NO PHYSICAL CAPTURE",
  "machine": "arm64",
  "numpy": "2.4.4",
  "opencv": "4.13.0",
  "otl_version": "0.1.0",
  "pillow": "12.2.0",
  "platform": "macOS-27.2-arm64-arm-64bit-Mach-O",
  "processor": "arm",
  "pytest": "9.0.3",
  "python": "3.14.7 (main, Aug  5 2026, 10:29:49) [Clang 21.0.0 (clang-2100.1.1.101)]",
  "python_executable": "/opt/homebrew/opt/python@3.14/bin/python3.14",
  "simulation_only": true,
  "timestamp_utc": "2026-11-08T10:26:19.105154+00:00",
  "zstandard": "0.25.0"
}
```
