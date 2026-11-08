# E09_end_to_end — End-to-end simulated transfer

Hypothesis: The full pipeline (compression, packetisation, RS, rendering, simulated channel, spatial decode, reassembly) recovers files under clean/mild/harsh channels and moderate frame loss, with a measurable failure limit on a deliberately brutal stress channel.

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
python3 -m experiments.run_all --only E09_end_to_end
```
