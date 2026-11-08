# E10_determinism — Determinism, prerecorded-image decoding and resource benchmark

- Run: `20261108T072943Z-9301d0`
- Classification: **OBSERVED (software)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 3
- Wall time: 4.60 s
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
{
  "artifacts": "artifacts/frames/*.png",
  "cell_accuracy": 1.0,
  "corpus_hash": "a2bdb40d0c222d9a18af38fba1cdff31bddc972457b82d2d7b40268515624b4c",
  "crc_ok_frames": 40,
  "decode_deterministic": true,
  "frames": 40,
  "latency_ms": {
    "decode_mean": 5.868839675167692,
    "decode_p50": 5.763978493632749,
    "decode_p95": 6.060516340221511,
    "render_mean": 0.8417447501415154
  },
  "pipeline_deterministic": true,
  "render_deterministic": true,
  "resource": {
    "cpu_percent": 717.038428041852,
    "cpu_s": 12.547226,
    "max_rss_kb": 123305984,
    "wall_s": 1.749867999998969
  }
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

Rendering is byte-identical across repeated calls, decoding the same prerecorded PNGs twice produces identical cell sequences, and the end-to-end pipeline reproduces the same drop pattern and output with a fixed seed. The decoder has no camera dependency. Latency and memory figures are OBSERVED software measurements on this host and will vary with hardware.

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
  "timestamp_utc": "2026-11-08T07:29:48.031482+00:00",
  "zstandard": "0.25.0"
}
```
