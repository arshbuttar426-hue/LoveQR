# E01_capacity — Protocol arithmetic and raw capacity

- Run: `20261108T073253Z-7694c3`
- Classification: **THEORETICAL (arithmetic) + OBSERVED (software timings)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 33
- Wall time: 0.04 s
- Quick mode: False

## Hypothesis

The proposed 30-cell, four-triangle alphabet yields 120 raw bits per screen frame, 88 payload bits after the 16-bit header and 16-bit CRC, and the 4-bit packet id limits a transfer to 16 packets.

## Controlled variables

- cell alphabet FULL16
- header 16 bits
- CRC 16 bits
- RS(255,223)

## Independent variables

- display frame rate
- frame loss rate

## Dependent variables

- raw bit rate
- framed payload rate
- RS goodput
- packet duration

## Procedure

1. Derive frame and packet arithmetic from the typed ProtocolConfig.
2. Compute raw, framed-payload and RS-goodput rates for each frame rate and loss rate.
3. Measure pack/unpack and RS encode/decode time on 2000 random frames and one packet.
4. Record all values with explicit analytical/software provenance.

## Processed results

```json
{
  "crc_bits": 16,
  "frame_bits": 120,
  "framed_payload_bps_at_60fps": 5280,
  "frames_per_packet": 255,
  "header_bits": 16,
  "max_packets": 16,
  "max_payload_bytes": 39216,
  "max_payload_kib": 38.296875,
  "packet0_payload_bytes": 2421,
  "packet_duration_s_at_60fps": 4.25,
  "packet_payload_bytes": 2453,
  "payload_bits": 88,
  "payload_bytes_per_frame": 11,
  "raw_bps_at_60fps": 7200,
  "rs_code_rate": 0.8745098039215686,
  "rs_goodput_bps_at_60fps": 4617.411764705882,
  "software": {
    "pack_us_per_frame": 1.4237084978958592,
    "unpack_us_per_frame": 3.9935835011419845
  }
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

The 30-cell FULL16 frame carries 120 raw bits, of which 88 are payload (11 bytes). At 60 display frames/s the raw rate is 7200 bps, the framed payload rate is 5280 bps, and the RS(255,223) goodput is 4617 bps. A packet occupies 4.25 s at 60 fps and the 4-bit packet id caps a transfer at 16 packets (39216 bytes before compression). These are THEORETICAL arithmetic values; software timings are OBSERVED on the run machine.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E01_capacity
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
  "timestamp_utc": "2026-11-08T07:32:53.613070+00:00",
  "zstandard": "0.25.0"
}
```
