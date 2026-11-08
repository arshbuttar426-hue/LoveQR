# E05_erasures — Frame loss and Reed-Solomon erasure capacity

- Run: `20261108T073313Z-f3f316`
- Classification: **OBSERVED (software ECC) + THEORETICAL (capacity)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 138
- Wall time: 1.50 s
- Quick mode: False

## Hypothesis

Byte interleaving plus RS(255,223) tolerates up to 32 lost frames per packet, independent of whether the loss is random or bursty.

## Controlled variables

- one packet of 255 frames
- fixed payload
- nsym=32
- frame indices

## Independent variables

- number of lost frames
- loss pattern (random/burst)
- random seed

## Dependent variables

- packet decode success
- corrected positions
- block failures
- decode time

## Procedure

1. Encode one 2200-byte payload into a 255-frame packet.
2. Remove 0..40 frames at random or as one contiguous burst.
3. Decode the packet with the erasure-aware RS path and record success or the structured error.
4. Compare the observed boundary with 2*errors + erasures <= nsym.

## Processed results

```json
{
  "capacity_rule": "2*byte_errors + lost_frames <= nsym per RS block",
  "interleaving": "frame n carries byte n of every block, so a lost frame is one erasure per block",
  "max_lost_frames_decoded": 32,
  "nsym": 32,
  "smallest_failing_loss_count": 33,
  "theoretical_max_erasures": 32
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

With nsym=32, packets decode with up to 32 lost frames; the smallest failing loss count observed is 33. This matches the theoretical erasure capacity of 32 per RS block because interleaving turns each lost frame into exactly one erasure in every block. Random and burst loss behave the same at equal counts under byte interleaving.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E05_erasures
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
  "timestamp_utc": "2026-11-08T07:33:15.231738+00:00",
  "zstandard": "0.25.0"
}
```
