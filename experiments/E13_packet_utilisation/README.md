# E13_packet_utilisation — M11 packet utilisation optimisation

Hypothesis: The 11.99% wire-packet fill is unused payload capacity, not protocol loss. Filling the packet with useful bytes, bundling logical payloads, choosing raw/compressed adaptively, using the OTL1 dictionary on repeated data and sizing RS parity to the measured channel can raise net application throughput while keeping SHA-256 exact reconstruction.

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
python3 -m experiments.run_all --only E13_packet_utilisation
```
