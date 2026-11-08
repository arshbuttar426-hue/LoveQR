# E11_physical — Physical optical validation (screen → camera)

- Run: `20261108T103744Z-0fb343`
- Classification: **PHYSICAL (camera capture) + SOFTWARE (decode)**
- Evidence source: **PHYSICAL / CAMERA CAPTURE**
- Device: **iPhone14,2 (Continuity Camera, 'Arsh Camera')**
- Trials: 15
- Wall time: 0.39 s
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
    "exposure": "auto",
    "focus": "auto (Continuity Camera)",
    "format": "PNG via AVFoundation",
    "fps": 30.0,
    "iso": "auto",
    "mode": "still burst",
    "notes": "exact command: python3 -m otl capture still 1 --out /private/var/folders/7r/8thcpkq94zn87lx_m5q2dl680000gn/T/opencode/probe43 --frames 15 --fps 30 --size 1920x1440",
    "resolution": "1920x1440",
    "stabilization": "not applicable (still burst)",
    "zoom": "1x"
  },
  "capture_source": "camera",
  "captures": 15,
  "device": {
    "camera": "rear camera via Continuity Camera; 1920x1440 at 30 fps",
    "model": "iPhone14,2 (Continuity Camera, 'Arsh Camera')",
    "notes": "AVFoundation device index 1",
    "os": "iOS (version not exposed by AVFoundation)",
    "serial": ""
  },
  "display": {
    "brightness": "not measured (macOS default)",
    "height_px": 1664,
    "kind": "computer",
    "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
    "notes": "Safari frontmost, player_hold.html held on frame 0",
    "refresh_hz": 60.0,
    "width_px": 2560
  },
  "evidence_source": "PHYSICAL / CAMERA CAPTURE",
  "geometry": {
    "ambient_lux": null,
    "angle_deg": null,
    "distance_mm": null,
    "hand_held": null,
    "lighting": "indoor",
    "notes": "operator hand-positioned the iPhone facing the display; distance, angle and ambient illuminance were not measured"
  },
  "note": "Decoding is software; the image bytes are physical camera output.",
  "session_id": "m9-iphone14-2-20261108T103717Z",
  "session_notes": "First physical capture that decoded: 15/15 frame CRC, cell accuracy 1.000 after the D22 classifier fix. The displayed frame is p00_f000.png (hold mode).",
  "session_path": "datasets/physical/m9-iphone14-2-20261108T103717Z",
  "transmitter": {
    "attached_utc": "2026-11-08T10:37:23.045636+00:00",
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
      "max": 0.0,
      "mean": 0.0,
      "min": 0.0,
      "n": 0.0,
      "p50": 0.0,
      "p95": 0.0,
      "std": 0.0
    },
    "bit_accuracy_mean": null,
    "bit_error_rate": null,
    "cell_accuracy": {
      "max": 0.0,
      "mean": 0.0,
      "min": 0.0,
      "n": 0.0,
      "p50": 0.0,
      "p95": 0.0,
      "std": 0.0
    },
    "cell_accuracy_mean": null,
    "cell_error_rate": null
  },
  "capture_settings": {
    "exposure": "auto",
    "focus": "auto (Continuity Camera)",
    "format": "PNG via AVFoundation",
    "fps": 30.0,
    "iso": "auto",
    "mode": "still burst",
    "notes": "exact command: python3 -m otl capture still 1 --out /private/var/folders/7r/8thcpkq94zn87lx_m5q2dl680000gn/T/opencode/probe43 --frames 15 --fps 30 --size 1920x1440",
    "resolution": "1920x1440",
    "stabilization": "not applicable (still burst)",
    "zoom": "1x"
  },
  "capture_source": "camera",
  "captures": {
    "count": 15,
    "crc_rate": 1.0,
    "decoded_crc_ok": 15,
    "frame_index_matches": 15,
    "frame_loss_rate": 0.0,
    "ground_truth_frames": 0
  },
  "comparison": [
    {
      "basis": "E02 clean simulated channel vs E11 observed captures with known frames",
      "delta": null,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "clean-cell accuracy",
      "observed": null,
      "simulated": 1.0,
      "unit": "fraction"
    },
    {
      "basis": "E09 all-channel simulated success rate vs E11 observed frame CRC rate",
      "delta": 0.25,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "frame CRC success rate",
      "observed": 1.0,
      "simulated": 0.75,
      "unit": "fraction"
    },
    {
      "basis": "E10 software decode mean vs E11 observed-image decode mean (same decoder)",
      "delta": 1.6491277074237587,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "decode latency",
      "observed": 7.452719533466734,
      "simulated": 5.803591826042975,
      "unit": "ms/frame"
    },
    {
      "basis": "E01 theoretical 60 fps vs E11 decoded frames / capture duration",
      "delta": null,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "raw payload bit rate",
      "observed": null,
      "simulated": 7200,
      "unit": "bps"
    },
    {
      "basis": "E09 projected 60 fps mean vs E11 reassembled payload / capture duration",
      "delta": null,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "net throughput at 60 fps",
      "observed": null,
      "simulated": 3529.4117647058824,
      "unit": "bps"
    }
  ],
  "device": {
    "camera": "rear camera via Continuity Camera; 1920x1440 at 30 fps",
    "model": "iPhone14,2 (Continuity Camera, 'Arsh Camera')",
    "notes": "AVFoundation device index 1",
    "os": "iOS (version not exposed by AVFoundation)",
    "serial": ""
  },
  "display": {
    "brightness": "not measured (macOS default)",
    "height_px": 1664,
    "kind": "computer",
    "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
    "notes": "Safari frontmost, player_hold.html held on frame 0",
    "refresh_hz": 60.0,
    "width_px": 2560
  },
  "evidence_source": "PHYSICAL / CAMERA CAPTURE",
  "geometry": {
    "ambient_lux": null,
    "angle_deg": null,
    "distance_mm": null,
    "hand_held": null,
    "lighting": "indoor",
    "notes": "operator hand-positioned the iPhone facing the display; distance, angle and ambient illuminance were not measured"
  },
  "latency": {
    "decode_fps": 134.17920740334588,
    "decode_ms": {
      "max": 11.643834004644305,
      "mean": 7.452719533466734,
      "min": 6.9951670011505485,
      "n": 15.0,
      "p50": 7.140416011679918,
      "p95": 8.690737704455383,
      "std": 1.1250530849940568
    },
    "decode_wall_s": 0.11179079300200101,
    "packet_decode_ms": 0.058707999414764345,
    "reassembly_ms": 0.0002079905243590474,
    "reconstruction_ms": 0.05891598993912339,
    "resource": {
      "cpu_percent": 168.61343035569487,
      "cpu_s": 0.6423289999999999,
      "max_rss_kb": 107504,
      "rss_kb": 107504,
      "wall_s": 0.38094770899624564
    }
  },
  "note": "PHYSICAL camera bytes decoded by software. Accuracy is relative to the displayed frame only where the operator recorded an independent frame mapping; video frame identity comes from the OTL header.",
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
  "session_id": "m9-iphone14-2-20261108T103717Z",
  "status": "measured",
  "throughput": {
    "capture_duration_s": null,
    "capture_fps": 30.0,
    "frames_decoded": 15,
    "frames_delivered": 15,
    "net_bps": null,
    "note": "net_bps is only reported when a complete payload was reassembled and its SHA-256 matched the transmitted payload.",
    "payload_bytes": 0,
    "payload_error": null,
    "payload_sha256": null,
    "payload_success": false,
    "raw_channel_bps": null,
    "raw_payload_bps": null
  }
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

PHYSICAL / CAMERA CAPTURE. Session m9-iphone14-2-20261108T103717Z from iPhone14,2 (Continuity Camera, 'Arsh Camera') capturing a Apple M5 built-in Liquid Retina (MacBook Air): 15 preserved images, 15 passed the frame CRC (100.0%). No independent per-frame mapping was recorded, so cell accuracy is not claimed; only CRC and payload results are reported. No complete payload was reassembled from this session. Measured decode latency 7.45 ms/frame and decoded-frame rate 134.2 fps. All physical numbers come from the preserved camera files; decoding is software. Compare with E01–E10 only through the comparison table, which states the basis of every pair.

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
  "device": {
    "camera": {
      "exposure": "auto",
      "focus": "auto (Continuity Camera)",
      "format": "PNG via AVFoundation",
      "fps": 30.0,
      "iso": "auto",
      "mode": "still burst",
      "notes": "exact command: python3 -m otl capture still 1 --out /private/var/folders/7r/8thcpkq94zn87lx_m5q2dl680000gn/T/opencode/probe43 --frames 15 --fps 30 --size 1920x1440",
      "resolution": "1920x1440",
      "stabilization": "not applicable (still burst)",
      "zoom": "1x"
    },
    "display": {
      "brightness": "not measured (macOS default)",
      "height_px": 1664,
      "kind": "computer",
      "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
      "notes": "Safari frontmost, player_hold.html held on frame 0",
      "refresh_hz": 60.0,
      "width_px": 2560
    },
    "model": "iPhone14,2 (Continuity Camera, 'Arsh Camera')",
    "notes": "AVFoundation device index 1",
    "os": "iOS (version not exposed by AVFoundation)",
    "serial": ""
  },
  "evidence_source": "PHYSICAL / CAMERA CAPTURE",
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
  "simulation_only": false,
  "timestamp_utc": "2026-11-08T10:37:45.058034+00:00",
  "zstandard": "0.25.0"
}
```
