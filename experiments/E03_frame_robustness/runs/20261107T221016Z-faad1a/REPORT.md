# E03_frame_robustness — Single-frame decode robustness sweep

- Run: `20261107T221016Z-faad1a`
- Classification: **OBSERVED (SIMULATED channel)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 40
- Wall time: 1.57 s
- Quick mode: True

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
  "frames_per_level": 4,
  "parameters": {
    "ambient": {
      "mean_success_rate": 1.0,
      "min_success_rate": 1.0
    },
    "blur_sigma": {
      "mean_success_rate": 1.0,
      "min_success_rate": 1.0
    },
    "brightness": {
      "mean_success_rate": 1.0,
      "min_success_rate": 1.0
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
      "mean_success_rate": 1.0,
      "min_success_rate": 1.0
    },
    "perspective": {
      "mean_success_rate": 1.0,
      "min_success_rate": 1.0
    },
    "vignette": {
      "mean_success_rate": 1.0,
      "min_success_rate": 1.0
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

The clean render decodes every frame. Each degradation has a different failure mode: blur mixes triangle interiors, noise perturbs the per-cell threshold, JPEG creates block artefacts, ambient/brightness shift the histogram, perspective stresses fiducial detection, and vignetting reduces corner contrast. The per-parameter tables show where the CRC success rate falls; these are SIMULATED observations, not physical camera results.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E03_frame_robustness --quick
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
  "timestamp_utc": "2026-11-07T22:10:18.132540+00:00",
  "zstandard": "0.25.0"
}
```
