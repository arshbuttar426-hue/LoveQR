# E04_geometry — Resolution (distance proxy) and perspective (angle proxy)

- Run: `20261108T073311Z-cc0715`
- Classification: **OBSERVED (SIMULATED channel)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 21
- Wall time: 2.20 s
- Quick mode: False

## Hypothesis

Spatial decoding tolerates moderate resolution loss and perspective, with a measurable boundary set by cell size and the fiducial detector.

## Controlled variables

- clean optical channel
- canonical layout
- random frames
- decoder settings

## Independent variables

- downscale factor
- perspective amount

## Dependent variables

- CRC success rate
- cell accuracy
- cell bit error rate
- detection failures
- decode time

## Procedure

1. Render random frames at the canonical 1080x1350 canvas.
2. Apply either a downscale/upscale resolution proxy or a perspective warp.
3. Decode and compare with ground truth, recording detection failures separately.
4. Report success and accuracy against effective cell size / perspective amount.

## Processed results

```json
{
  "frames_per_point": 12,
  "perspective": [
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 143,
      "success_rate": 1.0,
      "value": 0.0
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 143,
      "success_rate": 1.0,
      "value": 0.02
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 143,
      "success_rate": 1.0,
      "value": 0.04
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 143,
      "success_rate": 1.0,
      "value": 0.06
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 143,
      "success_rate": 1.0,
      "value": 0.08
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 143,
      "success_rate": 1.0,
      "value": 0.1
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 143,
      "success_rate": 1.0,
      "value": 0.12
    },
    {
      "cell_accuracy": 0.16111111111111112,
      "effective_cell_px": 143,
      "success_rate": 0.0,
      "value": 0.16
    },
    {
      "cell_accuracy": 0.10277777777777777,
      "effective_cell_px": 143,
      "success_rate": 0.0,
      "value": 0.2
    },
    {
      "cell_accuracy": 0.08611111111111111,
      "effective_cell_px": 143,
      "success_rate": 0.0,
      "value": 0.25
    }
  ],
  "perspective_boundary": {
    "first_failing_cell_px": 143.0,
    "first_failing_value": 0.16,
    "last_full_success_cell_px": 143.0,
    "last_full_success_value": 0.12,
    "tested_values": [
      0.0,
      0.02,
      0.04,
      0.06,
      0.08,
      0.1,
      0.12,
      0.16,
      0.2,
      0.25
    ]
  },
  "resolution": [
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 143.0,
      "success_rate": 1.0,
      "value": 1.0
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 107.25,
      "success_rate": 1.0,
      "value": 0.75
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 71.5,
      "success_rate": 1.0,
      "value": 0.5
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 50.05,
      "success_rate": 1.0,
      "value": 0.35
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 35.75,
      "success_rate": 1.0,
      "value": 0.25
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 21.45,
      "success_rate": 1.0,
      "value": 0.15
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 14.3,
      "success_rate": 1.0,
      "value": 0.1
    },
    {
      "cell_accuracy": 1.0,
      "effective_cell_px": 8.58,
      "success_rate": 1.0,
      "value": 0.06
    },
    {
      "cell_accuracy": 0.9972222222222222,
      "effective_cell_px": 5.72,
      "success_rate": 0.9166666666666666,
      "value": 0.04
    },
    {
      "cell_accuracy": 0.9611111111111111,
      "effective_cell_px": 4.29,
      "success_rate": 0.25,
      "value": 0.03
    },
    {
      "cell_accuracy": 0.8972222222222223,
      "effective_cell_px": 2.86,
      "success_rate": 0.08333333333333333,
      "value": 0.02
    }
  ],
  "resolution_boundary": {
    "first_failing_cell_px": 5.72,
    "first_failing_value": 0.04,
    "last_full_success_cell_px": 8.58,
    "last_full_success_value": 0.06,
    "tested_values": [
      0.02,
      0.03,
      0.04,
      0.06,
      0.1,
      0.15,
      0.25,
      0.35,
      0.5,
      0.75,
      1.0
    ]
  }
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

The last fully successful downscale was 0.06 (8.6 effective px per cell) and the first failure was 0.04 (5.7 px per cell). Perspective stayed correct up to 0.12 and first failed at 0.16. Resolution loss makes triangle sampling windows overlap pattern boundaries; perspective is limited by the fiducial detector's fixed area/aspect gates and quadrant assumption, which are tuned for a cropped screen. The exact crossing points are in the per-trial CSV. The perspective sweep is an angle proxy, not a measurement of a real phone at a real angle.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E04_geometry
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
  "timestamp_utc": "2026-11-08T07:33:13.725030+00:00",
  "zstandard": "0.25.0"
}
```
