# E10_determinism — Determinism, prerecorded-image decoding and resource benchmark

- Run: `20261107T222117Z-08f6b9`
- Classification: **OBSERVED (software)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 1
- Wall time: 0.82 s
- Quick mode: True

## Hypothesis

Every stage is deterministic for fixed inputs and seeds, the decoder works on prerecorded images without a camera, and latency/memory are measurable and stable.

## Controlled variables

- fixed frames
- fixed layout/config
- fixed seed
- same host

## Independent variables

- repeat index
- input source (memory vs PNG)

## Dependent variables

- hash equality
- CRC success
- cell accuracy
- latency
- CPU
- RSS

## Procedure

1. Render a corpus of random frames twice and compare hashes.
2. Save the corpus as PNG, decode from disk twice, and compare cell sequences.
3. Run the end-to-end pipeline twice with the same seed and compare results.
4. Benchmark render/decode latency and record CPU/RSS.

## Processed results

```json
{}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- ProtocolError: [E_PROTOCOL] protocol.FileHeader: file name too long for the header {'name': 'determinism.bin', 'max_bytes': 13}

## Conclusion

The run did not complete. Raw trials written before the failure are retained; see failures and the traceback in manifest.json.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E10_determinism --quick
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
  "timestamp_utc": "2026-11-07T22:21:18.609074+00:00",
  "zstandard": "0.25.0"
}
```
