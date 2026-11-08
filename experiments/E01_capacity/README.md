# E01_capacity — Protocol arithmetic and raw capacity

Hypothesis: The proposed 30-cell, four-triangle alphabet yields 120 raw bits per screen frame, 88 payload bits after the 16-bit header and 16-bit CRC, and the 4-bit packet id limits a transfer to 16 packets.

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
python3 -m experiments.run_all --only E01_capacity
```
