# E02_patterns — Separability of the 16 four-triangle cell patterns

- Run: `20261108T073253Z-75a59d`
- Classification: **OBSERVED (SIMULATED channel)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 80
- Wall time: 9.27 s
- Quick mode: False

## Hypothesis

Four independent black/white triangles give 16 visually distinct patterns, but the alphabet has minimum Hamming distance 1 and therefore needs CRC/RS protection.

## Controlled variables

- 30-cell layout
- FULL16 alphabet
- target cell positions
- distractor cells

## Independent variables

- cell pattern 0..15
- channel severity

## Dependent variables

- target-cell accuracy
- cell bit error rate
- confidence
- bit margin
- decode time

## Procedure

1. Build a frame with 15 target cells set to one pattern and 15 random distractors.
2. Render, apply the clean/mild/harsh synthetic channel, and decode the image.
3. Compare decoded cell values with the ground truth; repeat per pattern and severity.
4. Report per-pattern accuracy and the analytical pairwise Hamming distances.

## Processed results

```json
{
  "alphabet": {
    "bits_per_cell": 4,
    "min_hamming_distance": 1,
    "pattern_set": "full16",
    "size": 16,
    "table": [
      {
        "binary": "0000",
        "colors_top_right_bottom_left": [
          false,
          false,
          false,
          false
        ],
        "value": 0
      },
      {
        "binary": "0001",
        "colors_top_right_bottom_left": [
          false,
          false,
          false,
          true
        ],
        "value": 1
      },
      {
        "binary": "0010",
        "colors_top_right_bottom_left": [
          false,
          false,
          true,
          false
        ],
        "value": 2
      },
      {
        "binary": "0011",
        "colors_top_right_bottom_left": [
          false,
          false,
          true,
          true
        ],
        "value": 3
      },
      {
        "binary": "0100",
        "colors_top_right_bottom_left": [
          false,
          true,
          false,
          false
        ],
        "value": 4
      },
      {
        "binary": "0101",
        "colors_top_right_bottom_left": [
          false,
          true,
          false,
          true
        ],
        "value": 5
      },
      {
        "binary": "0110",
        "colors_top_right_bottom_left": [
          false,
          true,
          true,
          false
        ],
        "value": 6
      },
      {
        "binary": "0111",
        "colors_top_right_bottom_left": [
          false,
          true,
          true,
          true
        ],
        "value": 7
      },
      {
        "binary": "1000",
        "colors_top_right_bottom_left": [
          true,
          false,
          false,
          false
        ],
        "value": 8
      },
      {
        "binary": "1001",
        "colors_top_right_bottom_left": [
          true,
          false,
          false,
          true
        ],
        "value": 9
      },
      {
        "binary": "1010",
        "colors_top_right_bottom_left": [
          true,
          false,
          true,
          false
        ],
        "value": 10
      },
      {
        "binary": "1011",
        "colors_top_right_bottom_left": [
          true,
          false,
          true,
          true
        ],
        "value": 11
      },
      {
        "binary": "1100",
        "colors_top_right_bottom_left": [
          true,
          true,
          false,
          false
        ],
        "value": 12
      },
      {
        "binary": "1101",
        "colors_top_right_bottom_left": [
          true,
          true,
          false,
          true
        ],
        "value": 13
      },
      {
        "binary": "1110",
        "colors_top_right_bottom_left": [
          true,
          true,
          true,
          false
        ],
        "value": 14
      },
      {
        "binary": "1111",
        "colors_top_right_bottom_left": [
          true,
          true,
          true,
          true
        ],
        "value": 15
      }
    ],
    "values": [
      0,
      1,
      2,
      3,
      4,
      5,
      6,
      7,
      8,
      9,
      10,
      11,
      12,
      13,
      14,
      15
    ]
  },
  "bits_per_cell": 4,
  "distinct_patterns": 16,
  "max_pairwise_hamming_distance": 4,
  "mean_target_accuracy_by_severity": {
    "brutal": 0.3125,
    "clean": 1.0,
    "extreme": 1.0,
    "harsh": 1.0,
    "mild": 1.0
  },
  "min_pairwise_hamming_distance": 1,
  "note": "FULL16 uses all 16 combinations, so the minimum symbol distance is one triangle (1 bit). There is no intra-cell error correction; detection and correction rely on the frame CRC and RS layer."
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

Measured mean target-cell accuracy by severity: brutal=0.312, clean=1.000, extreme=1.000, harsh=1.000, mild=1.000. The 16-way decision was perfect in clean, extreme, harsh, mild; it degraded in brutal (figures above and per-pattern rows in the CSV). FULL16 has minimum Hamming distance 1 between cell symbols, so a single misclassified triangle changes the decoded nibble. This is why the protocol adds a CRC-16 per frame and RS(255,223) per packet instead of relying on the cell alphabet for protection.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E02_patterns
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
  "timestamp_utc": "2026-11-08T07:33:02.898882+00:00",
  "zstandard": "0.25.0"
}
```
