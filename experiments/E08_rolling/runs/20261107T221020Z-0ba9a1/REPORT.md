# E08_rolling — Temporal blink IDs under a rolling-shutter capture

- Run: `20261107T221020Z-0ba9a1`
- Classification: **OBSERVED (SIMULATED rolling shutter) + THEORETICAL (timing)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 51
- Wall time: 637.65 s
- Quick mode: True

## Hypothesis

Rolling shutter exposes multiple display symbols per capture only when the readout time spans multiple symbol periods; a 26-chip word needs readout >= 26 symbol periods.

## Controlled variables

- camera height 1350
- uniform display frames
- sync+ID codebook
- phase 0

## Independent variables

- display frame rate
- exposure time
- row time
- sensor noise
- blink ID

## Dependent variables

- temporal lock
- correct ID
- visible symbols
- symbols per capture
- decode time

## Procedure

1. For each timing configuration, render the 26-chip sync+ID word as uniform full-frame symbols.
2. Integrate each camera row's exposure against the display timeline.
3. Optionally add sensor noise, then segment and decode the visible symbols.
4. Compare lock/ID success with the analytical readout/symbol-period ratio.

## Processed results

```json
{}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- ChannelError: [E_CHANNEL] channel.apply_channel: channel expects a single-channel image {'shape': (1350, 1350, 1080)}

## Conclusion

The run did not complete. Raw trials written before the failure are retained; see failures and the traceback in manifest.json.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E08_rolling --quick
```

The run directory is immutable; re-running creates a new run id.

## Environment

```json
{
  "cpu_count": 10,
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
  "timestamp_utc": "2026-11-07T22:20:57.924020+00:00",
  "zstandard": "0.25.0"
}
```
