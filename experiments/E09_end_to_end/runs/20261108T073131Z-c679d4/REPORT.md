# E09_end_to_end — End-to-end simulated transfer

- Run: `20261108T073131Z-c679d4`
- Classification: **OBSERVED (SIMULATED channel) + THEORETICAL (projected screen time)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 8
- Wall time: 39.37 s
- Quick mode: True

## Hypothesis

The full pipeline (compression, packetisation, RS, rendering, simulated channel, spatial decode, reassembly) recovers files under clean/mild channels and moderate frame loss, with a measurable harsh-channel limit.

## Controlled variables

- protocol
- layout
- renderer
- decoder
- RS settings
- seed

## Independent variables

- payload type/size
- channel severity
- frame-drop probability

## Dependent variables

- transfer success
- compression ratio
- frames decoded/dropped
- BER
- simulated throughput
- projected screen throughput
- CPU/memory

## Procedure

1. Build text and random payloads at several sizes.
2. Run the complete simulate_transfer pipeline with clean/mild/harsh channels and 0/3% frame loss.
3. Record success, per-packet RS statistics, errors, timings and resource use.
4. Separate simulated wall-clock throughput from projected 60 fps screen throughput.

## Processed results

```json
{
  "by_channel": {
    "clean": {
      "successes": 4,
      "trials": 4
    },
    "mild": {
      "successes": 4,
      "trials": 4
    }
  },
  "by_kind": {
    "random": {
      "successes": 4,
      "trials": 4
    },
    "text": {
      "successes": 4,
      "trials": 4
    }
  },
  "max_payload_decoded": 1000,
  "note": "Simulated wall time measures the Python pipeline. Projected screen time = frames / 60 fps; projected net bit rate uses that screen time. Neither is a physical camera measurement.",
  "success_rate": 1.0,
  "successes": 8,
  "trials": 8
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

8 of 8 simulated transfers succeeded across channels clean, mild at 0% independent frame loss, with payloads up to 1000 bytes (largest tested: 1000 bytes). Every trial succeeded, so the tested channels and loss rates are upper bounds on tolerated degradation rather than a measured cliff. Simulated wall time is a software benchmark, not screen time: the projected 60 fps screen time and projected net bit rate are reported separately for protocol planning.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E09_end_to_end --quick
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
  "timestamp_utc": "2026-11-08T07:32:10.784804+00:00",
  "zstandard": "0.25.0"
}
```
