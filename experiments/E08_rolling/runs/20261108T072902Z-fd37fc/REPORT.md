# E08_rolling — Temporal blink IDs under a rolling-shutter capture

- Run: `20261108T072902Z-fd37fc`
- Classification: **OBSERVED (SIMULATED rolling shutter) + THEORETICAL (timing)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 60
- Wall time: 1.87 s
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
{
  "physical_limit": "visible display symbols = height * row_time / symbol_period; camera frame rate does not multiply display refresh rate",
  "readout_us_default": 27000.0,
  "success_when_word_does_not_fit": 0.0,
  "success_when_word_fits": 0.9285714285714286,
  "successful_words": 39,
  "trials_with_word_fit": 42,
  "word_chips": 26
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

A 26-chip word is recovered only when the rolling readout spans at least 26 display symbol periods. At 60 Hz (16.7 ms per symbol) a 27 ms readout sees only ~1.6 symbols, so a full blink word cannot fit in one capture; 240 Hz is still far short. At 1000 Hz the same readout sees ~27 symbols and all three IDs decode. This is the central temporal constraint of the proposed architecture, and it is a physical/arithmetic result, not a software limitation.

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
  "timestamp_utc": "2026-11-08T07:29:04.301193+00:00",
  "zstandard": "0.25.0"
}
```
