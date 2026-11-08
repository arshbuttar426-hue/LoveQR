# E06_errors — Reed-Solomon byte-error and mixed error/erasure capacity

- Run: `20261107T221019Z-8b880e`
- Classification: **OBSERVED (software ECC) + THEORETICAL (capacity)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 22
- Wall time: 0.35 s
- Quick mode: True

## Hypothesis

The clean-room RS(255,223) decoder corrects up to 16 unknown byte errors per block, or a mix satisfying 2*errors + erasures <= 32, and rejects anything beyond that.

## Controlled variables

- one encoded packet
- block interleaving
- nsym=32
- frame indices

## Independent variables

- byte errors per block
- number of erased frames
- random seed

## Dependent variables

- decode success
- corrected positions
- block failures
- capacity used
- decode time

## Procedure

1. Encode one packet and keep a clean copy of every frame's 11 bytes.
2. Inject a fixed number of single-bit byte errors per RS block at random frame positions.
3. Optionally erase a number of whole frames (one erasure per block).
4. Decode and compare the observed success boundary with 2*errors + erasures <= 32.

## Processed results

```json
{
  "failures": 4,
  "max_capacity_used_success": 32,
  "min_capacity_used_failure": 34,
  "nsym": 32,
  "successes": 18,
  "theoretical_rule": "2*errors + erasures <= nsym"
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

The measured boundary follows 2*errors + erasures <= nsym. Cases at or below capacity decode; cases above it fail with E_ECC/E_RECONSTRUCT rather than returning corrupt data. This is an injected-error test of the RS layer, not an optical measurement: frame CRC would normally convert most optical byte errors into erasures.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E06_errors --quick
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
  "timestamp_utc": "2026-11-07T22:10:19.927279+00:00",
  "zstandard": "0.25.0"
}
```
