# E05_erasures — Frame loss and Reed-Solomon erasure capacity

Hypothesis: Byte interleaving plus RS(255,223) tolerates up to 32 lost frames per packet, independent of whether the loss is random or bursty.

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
python3 -m experiments.run_all --only E05_erasures
```
