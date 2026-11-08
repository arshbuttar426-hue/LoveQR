# E03_frame_robustness — Single-frame decode robustness sweep

- Run: `20261108T073302Z-8176cb`
- Classification: **OBSERVED (SIMULATED channel)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 69
- Wall time: 8.62 s
- Quick mode: False

## Hypothesis

One 120-bit frame can be recovered under moderate blur, noise, JPEG, ambient light, brightness, perspective and vignetting, with a parameter-dependent failure boundary.

## Controlled variables

- random frame contents
- layout
- decoder settings
- frame count per level

## Independent variables

- blur sigma
- noise sigma
- JPEG quality
- ambient offset
- brightness
- perspective
- vignette
- gamma

## Dependent variables

- CRC success rate
- cell accuracy
- cell bit error rate
- confidence
- decode time

## Procedure

1. Generate random valid frames and render each to the canonical screen.
2. Apply one channel parameter at a time over a fixed sweep, with seeded noise.
3. Decode every capture and compare header/data/CRC and cell values with ground truth.
4. Aggregate success and error rates per parameter level.

## Processed results

```json
{
  "failure_boundaries": {
    "ambient": {
      "first_failing_value": null,
      "last_full_success_value": 200.0,
      "min_success_rate": 1.0,
      "success_rate_at_first_failure": null
    },
    "blur_sigma": {
      "first_failing_value": 16.0,
      "last_full_success_value": 12.0,
      "min_success_rate": 0.16666666666666666,
      "success_rate_at_first_failure": 0.16666666666666666
    },
    "brightness": {
      "first_failing_value": 0.08,
      "last_full_success_value": 0.15,
      "min_success_rate": 0.0,
      "success_rate_at_first_failure": 0.0
    },
    "gamma": {
      "first_failing_value": null,
      "last_full_success_value": 2.8,
      "min_success_rate": 1.0,
      "success_rate_at_first_failure": null
    },
    "jpeg_quality": {
      "first_failing_value": null,
      "last_full_success_value": 5.0,
      "min_success_rate": 1.0,
      "success_rate_at_first_failure": null
    },
    "noise_sigma": {
      "first_failing_value": 90.0,
      "last_full_success_value": 60.0,
      "min_success_rate": 0.9166666666666666,
      "success_rate_at_first_failure": 0.9166666666666666
    },
    "perspective": {
      "first_failing_value": 0.18,
      "last_full_success_value": 0.12,
      "min_success_rate": 0.0,
      "success_rate_at_first_failure": 0.0
    },
    "vignette": {
      "first_failing_value": 0.9,
      "last_full_success_value": 0.8,
      "min_success_rate": 0.5,
      "success_rate_at_first_failure": 0.5
    }
  },
  "frames_per_level": 12,
  "parameters": {
    "ambient": {
      "mean_success_rate": 1.0,
      "min_success_rate": 1.0
    },
    "blur_sigma": {
      "mean_success_rate": 0.9242424242424242,
      "min_success_rate": 0.16666666666666666
    },
    "brightness": {
      "mean_success_rate": 0.8888888888888888,
      "min_success_rate": 0.0
    },
    "gamma": {
      "mean_success_rate": 1.0,
      "min_success_rate": 1.0
    },
    "jpeg_quality": {
      "mean_success_rate": 1.0,
      "min_success_rate": 1.0
    },
    "noise_sigma": {
      "mean_success_rate": 0.9907407407407407,
      "min_success_rate": 0.9166666666666666
    },
    "perspective": {
      "mean_success_rate": 0.75,
      "min_success_rate": 0.0
    },
    "vignette": {
      "mean_success_rate": 0.9375,
      "min_success_rate": 0.5
    }
  },
  "success_rule": "frame CRC-16 matches after spatial decode"
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

A failure boundary was measured for 5 of 8 parameters (blur_sigma first failed at 16; noise_sigma first failed at 90; brightness first failed at 0.08; perspective first failed at 0.18; vignette first failed at 0.9). No failure was reached within the tested range for jpeg_quality, ambient, gamma; the per-frame photometric calibration makes global brightness, gamma and ambient offset largely irrelevant until contrast is destroyed. Blur mixes triangle interiors, noise perturbs the per-cell threshold, JPEG creates block artefacts, perspective stresses fiducial detection, and vignetting reduces corner contrast. These are SIMULATED observations, not physical camera results; the exact crossing points are in processed/summary.csv.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E03_frame_robustness
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
  "timestamp_utc": "2026-11-08T07:33:11.522100+00:00",
  "zstandard": "0.25.0"
}
```
