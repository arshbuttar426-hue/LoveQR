# E03_frame_robustness — Single-frame decode robustness sweep

Hypothesis: One 120-bit frame can be recovered under moderate blur, noise, JPEG, ambient light, brightness, perspective and vignetting, with a parameter-dependent failure boundary.

This directory is append-only. Every invocation creates
`runs/<UTC timestamp>-<nonce>/` containing:

- `manifest.json` — spec, environment, wall time, failures
- `raw/trials.jsonl` — one JSON object per trial, written while running
- `processed/summary.json` — processed aggregates and conclusion
- `processed/summary.csv` — one row per trial
- `REPORT.md` — human-readable report
- `artifacts/` — any images or hashes produced by the experiment

`LATEST` contains the newest run id. Nothing in an older run directory is
modified by a later run.

Run it with:

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E03_frame_robustness
```
