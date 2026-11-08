# E11_physical — Physical optical validation (screen → camera)

- Run: `20261108T083809Z-fb44a4`
- Classification: **SOFTWARE FIXTURE — ingestion/decoder path only**
- Evidence source: **SOFTWARE FIXTURE (NOT PHYSICAL)**
- Device: none (no physical capture)
- Trials: 1
- Wall time: 0.04 s
- Quick mode: False

## Hypothesis

The existing OTL frame, renderer and decoder can recover FULL16 frames from real smartphone-camera images of a screen, with cell accuracy and CRC success lower than the simulated clean channel because of optics, exposure, rolling shutter, moiré and hand motion.

## Controlled variables

- protocol
- layout
- renderer
- decoder
- display frame sequence
- capture settings

## Independent variables

- device
- display
- distance
- angle
- ambient light
- exposure/focus

## Dependent variables

- frame CRC success
- cell/bit accuracy
- payload reconstruction
- decode latency
- capture/decode rate
- throughput

## Procedure

1. Render the payload to PNG frames and build a full-screen player.
2. Record the exact displayed frames, their hashes and the player manifest.
3. Capture the screen with a named smartphone camera, preserving originals.
4. Import the originals into a session without re-encoding them.
5. Decode every preserved image with the standard OTL decoder.
6. Record CRC, cell/bit accuracy, packet reconstruction, latency and rate.
7. Compare physical observations with the E01–E10 simulation baselines.

## Experiment metadata

```json
{
  "capture_settings": {
    "exposure": "",
    "focus": "",
    "format": "",
    "fps": null,
    "iso": "",
    "mode": "screen-capture",
    "notes": "",
    "resolution": "2560x1664",
    "stabilization": "",
    "zoom": ""
  },
  "capture_source": "fixture",
  "captures": 1,
  "device": {
    "camera": "none",
    "model": "macOS screencapture (software display capture, not a camera)",
    "notes": "",
    "os": "macOS",
    "serial": ""
  },
  "display": {
    "brightness": "",
    "height_px": 1664,
    "kind": "computer",
    "model": "Built-in Liquid Retina Display",
    "notes": "",
    "refresh_hz": 60.0,
    "width_px": 2560
  },
  "evidence_source": "SOFTWARE FIXTURE (NOT PHYSICAL)",
  "geometry": {
    "ambient_lux": null,
    "angle_deg": null,
    "distance_mm": null,
    "hand_held": null,
    "lighting": "",
    "notes": ""
  },
  "note": "Fixture images are rendered PNGs, not camera output.",
  "session_id": "display-capture-20261108T083805Z",
  "session_notes": "Fixture: actual HTML player displayed in Safari and captured with macOS screencapture. NOT camera optics.",
  "session_path": "datasets/fixtures/display-capture-20261108T083805Z",
  "transmitter": {
    "attached_utc": "2026-11-08T08:38:06.014437+00:00",
    "fps": 10.0,
    "frame_count": 255,
    "frames_sha256": "207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348",
    "hold": true,
    "payload_name": "payload.txt",
    "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
    "player_manifest": "display/player_manifest.json",
    "player_manifest_sha256": "72dfef512833fbaeaa8fbd8b5f481b9f1002603ad448bc68c9bc9cff3f32ec50"
  }
}
```

## Processed results

```json
{
  "accuracy": {
    "bit_accuracy": {
      "max": 1.0,
      "mean": 1.0,
      "min": 1.0,
      "n": 1.0,
      "p50": 1.0,
      "p95": 1.0,
      "std": 0.0
    },
    "bit_accuracy_mean": 1.0,
    "cell_accuracy": {
      "max": 1.0,
      "mean": 1.0,
      "min": 1.0,
      "n": 1.0,
      "p50": 1.0,
      "p95": 1.0,
      "std": 0.0
    },
    "cell_accuracy_mean": 1.0
  },
  "capture_settings": {
    "exposure": "",
    "focus": "",
    "format": "",
    "fps": null,
    "iso": "",
    "mode": "screen-capture",
    "notes": "",
    "resolution": "2560x1664",
    "stabilization": "",
    "zoom": ""
  },
  "capture_source": "fixture",
  "captures": {
    "count": 1,
    "crc_rate": 1.0,
    "decoded_crc_ok": 1,
    "frame_index_matches": 1,
    "ground_truth_frames": 1
  },
  "comparison": [
    {
      "basis": "E02 clean simulated channel vs E11 physical captures with known frames",
      "delta": 0.0,
      "metric": "clean-cell accuracy",
      "physical": 1.0,
      "simulated": 1.0,
      "unit": "fraction"
    },
    {
      "basis": "E09 all-channel simulated success rate vs E11 physical frame CRC rate",
      "delta": 0.25,
      "metric": "frame CRC success rate",
      "physical": 1.0,
      "simulated": 0.75,
      "unit": "fraction"
    },
    {
      "basis": "E10 software decode mean vs E11 physical-image decode mean (same decoder)",
      "delta": 7.867325177721796,
      "metric": "decode latency",
      "physical": 13.670917003764771,
      "simulated": 5.803591826042975,
      "unit": "ms/frame"
    },
    {
      "basis": "E01 theoretical 60 fps vs E11 measured decoded frames / capture duration",
      "delta": null,
      "metric": "raw payload bit rate",
      "physical": null,
      "simulated": 7200,
      "unit": "bps"
    },
    {
      "basis": "E09 projected 60 fps mean vs E11 reassembled payload / capture duration",
      "delta": null,
      "metric": "net throughput at 60 fps",
      "physical": null,
      "simulated": 3529.4117647058824,
      "unit": "bps"
    }
  ],
  "device": {
    "camera": "none",
    "model": "macOS screencapture (software display capture, not a camera)",
    "notes": "",
    "os": "macOS",
    "serial": ""
  },
  "display": {
    "brightness": "",
    "height_px": 1664,
    "kind": "computer",
    "model": "Built-in Liquid Retina Display",
    "notes": "",
    "refresh_hz": 60.0,
    "width_px": 2560
  },
  "evidence_source": "SOFTWARE FIXTURE (NOT PHYSICAL)",
  "geometry": {
    "ambient_lux": null,
    "angle_deg": null,
    "distance_mm": null,
    "hand_held": null,
    "lighting": "",
    "notes": ""
  },
  "latency": {
    "decode_fps": 73.14798266455824,
    "decode_ms": {
      "max": 13.670917003764771,
      "mean": 13.670917003764771,
      "min": 13.670917003764771,
      "n": 1.0,
      "p50": 13.670917003764771,
      "p95": 13.670917003764771,
      "std": 0.0
    },
    "decode_wall_s": 0.013670917003764771
  },
  "note": "SOFTWARE FIXTURE: the images are rendered PNGs, not camera data.",
  "packets": [
    {
      "decoded": false,
      "error": {
        "code": "E_RECONSTRUCT",
        "component": "protocol",
        "details": {
          "block": 0,
          "cause": {
            "code": "E_ECC",
            "component": "ecc",
            "details": {
              "erasures": 254,
              "nsym": 32
            },
            "message": "too many erasures",
            "operation": "decode"
          },
          "erasures": 254,
          "packet_id": 0
        },
        "message": "RS block could not be corrected",
        "operation": "decode_packet"
      },
      "frames_present": 1,
      "packet_id": 0
    }
  ],
  "session_id": "display-capture-20261108T083805Z",
  "status": "fixture",
  "throughput": {
    "capture_duration_s": null,
    "frames_decoded": 1,
    "frames_delivered": 1,
    "net_bps": null,
    "note": "net_bps is only reported when a complete payload was reassembled and its SHA-256 matched the transmitted payload.",
    "payload_bytes": 0,
    "payload_error": null,
    "payload_sha256": null,
    "payload_success": false,
    "raw_payload_bps": null
  }
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

SOFTWARE FIXTURE, NOT PHYSICAL EVIDENCE. Session display-capture-20261108T083805Z contains 1 rendered fixture images; 1 passed the frame CRC (100.0%). This run exercises the capture ingestion and E11 analysis path only. It must not be reported as a camera measurement or used to upgrade any claim to VERIFIED.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E11_physical
```

The run directory is immutable; re-running creates a new run id.

## Environment

```json
{
  "cpu_count": 10,
  "device": null,
  "evidence_source": "SOFTWARE FIXTURE (NOT PHYSICAL)",
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
  "timestamp_utc": "2026-11-08T08:38:09.245200+00:00",
  "zstandard": "0.25.0"
}
```
