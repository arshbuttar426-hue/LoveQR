# E12_channel_efficiency — Physical channel efficiency and reliability

Hypothesis: The gap between RS(255,223) goodput and application throughput is dominated by unused packet capacity (payload utilisation), not by display refresh, camera capture, detection, decoding or RS correction; independent baseline sessions repeat the protocol rates while camera-sample reliability may vary.

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
python3 -m experiments.run_all --only E12_channel_efficiency
```
