# E08_rolling — Temporal blink IDs under a rolling-shutter capture

- Run: `20261108T073129Z-226c78`
- Classification: **OBSERVED (SIMULATED rolling shutter) + THEORETICAL (timing)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 60
- Wall time: 1.84 s
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
  "by_display_fps": {
    "1000": {
      "correct": 36.0,
      "trials": 45.0,
      "word_fits": 39.0
    },
    "120": {
      "correct": 0.0,
      "trials": 3.0,
      "word_fits": 0.0
    },
    "2000": {
      "correct": 3.0,
      "trials": 3.0,
      "word_fits": 3.0
    },
    "240": {
      "correct": 0.0,
      "trials": 3.0,
      "word_fits": 0.0
    },
    "500": {
      "correct": 0.0,
      "trials": 3.0,
      "word_fits": 0.0
    },
    "60": {
      "correct": 0.0,
      "trials": 3.0,
      "word_fits": 0.0
    }
  },
  "physical_limit": "visible display symbols = height * row_time / symbol_period; camera frame rate does not multiply display refresh rate; exposure must also be no longer than one symbol period",
  "readout_us_default": 27000.0,
  "success_when_temporal_budget_ok": 1.0,
  "success_when_word_does_not_fit": 0.0,
  "success_when_word_fits": 0.9285714285714286,
  "successful_words": 39,
  "trials_with_temporal_budget": 39,
  "trials_with_word_fit": 42,
  "word_chips": 26
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

A 26-chip word is recovered only when the rolling readout spans at least 26 display symbol periods; the lowest tested display rate with a fitting word was 1000 Hz. At 60 Hz a 27.0 ms readout sees ~1.62 symbols, so a full blink word cannot fit in one capture. Separately, 3 trial(s) had a fitting readout but an exposure up to 2.50 symbol periods long; integrating several chips per row destroyed the word. Exposure must therefore be no longer than one symbol period as well as the readout spanning the word. This is the central temporal constraint of the proposed architecture, and it is a physical/arithmetic result, not a software limitation.

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
  "timestamp_utc": "2026-11-08T07:31:31.252925+00:00",
  "zstandard": "0.25.0"
}
```
