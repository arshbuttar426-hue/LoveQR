# E07_compression — Shared instruction dictionary (OTL1) compression effectiveness

- Run: `20261108T074405Z-c06991`
- Classification: **OBSERVED (software)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 30
- Wall time: 0.19 s
- Quick mode: False

## Hypothesis

A small deterministic LIT/REPEAT/COPY/INVERT/SEQUENCE codec reduces screen time for structured payloads while remaining byte-exact and cheap enough for the transmitter.

## Controlled variables

- OTL1 encoder settings
- corpus contents
- payload sizes

## Independent variables

- corpus type
- payload size

## Dependent variables

- compression ratio
- encode/decode time
- opcode counts
- packets needed

## Procedure

1. Build a deterministic corpus of text, CSV, code, JSON, sparse, repeated, alternating and random bytes.
2. Compress at 512, 4096 and 16384 bytes with the OTL1 encoder.
3. Decompress and verify byte-exact round-trip.
4. Record ratio, timings, opcode mix and the number of packets the compressed payload needs.

## Processed results

```json
{
  "container": "OTL1",
  "mean_ratio_by_corpus": {
    "alternating": 44.56538789428814,
    "csv": 1.3319615123096915,
    "inverted_text": 19.08610093623992,
    "json": 17.145679299934454,
    "random": 0.9842451677214966,
    "repeat_abcd": 43.729482991253555,
    "source_code": 25.689510489510493,
    "sparse_binary": 9.368078199868213,
    "text": 19.08610093623992,
    "zeros": 58.50925352597179
  },
  "note": "OTL1 is a deterministic, dependency-free dictionary codec designed for the on-screen instruction set; zlib/zstd numbers are references, not part of the protocol. Each size is generated independently, so the random corpus is not compressible by block repetition.",
  "opcodes": [
    "LIT",
    "REPEAT",
    "COPY",
    "INVERT",
    "SEQUENCE"
  ],
  "random_ratio_max": 0.9915874841130545,
  "random_ratio_mean": 0.9842451677214966,
  "random_ratio_min": 0.9715370018975332,
  "zstd_available": true
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

OTL1 compresses repetitive, textual and structured payloads strongly (highest mean ratio: zeros at 58.5×), leaves incompressible random data at roughly unit ratio (mean 0.984 (range 0.972–0.992)), and always round-trips byte-exactly. Because the compressed payload determines the number of packets, compression directly reduces screen time. OTL1 does not claim to beat zlib/zstd on general data; its purpose is a small, deterministic, inspectable instruction stream.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E07_compression
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
  "timestamp_utc": "2026-11-08T07:44:05.696114+00:00",
  "zstandard": "0.25.0"
}
```
