# E11_physical — Physical optical validation (screen → camera)

- Run: `20261108T105701Z-f7df38`
- Classification: **PHYSICAL (camera capture) + SOFTWARE (decode)**
- Evidence source: **PHYSICAL / CAMERA CAPTURE**
- Device: **iPhone14,2 (Continuity Camera, 'Arsh Camera')**
- Trials: 1
- Wall time: 0.05 s
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
  "captures": 1,
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
      "max": 1.0,
      "mean": 1.0,
      "min": 1.0,
      "n": 1.0,
      "p50": 1.0,
      "p95": 1.0,
      "std": 0.0
    },
    "bit_accuracy_mean": 1.0,
    "bit_accuracy_per_capture_mean": 1.0,
    "bit_error_rate": 0.0,
    "cell_accuracy": {
      "max": 1.0,
      "mean": 1.0,
      "min": 1.0,
      "n": 1.0,
      "p50": 1.0,
      "p95": 1.0,
      "std": 0.0
    },
    "cell_accuracy_mean": 1.0,
    "cell_accuracy_per_capture_mean": 1.0,
    "cell_error_rate": 0.0
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
    "attempt_failure_rate": 0.0,
    "count": 1,
    "crc_rate": 1.0,
    "decoded_crc_ok": 1,
    "detection_failures": 0,
    "duplicate_files": 14,
    "error_counts": {},
    "expected_frames": 255,
    "files": 15,
    "frame_delivery_rate": 0.00392156862745098,
    "frame_index_matches": 1,
    "frame_loss_rate": 0.996078431372549,
    "ground_truth_attempts": 1,
    "ground_truth_frames": 1,
    "image_files": 15,
    "media_files": 0,
    "note": "count is unique image SHA-256 values; files includes byte-identical duplicates from a burst. crc_rate is the fraction of camera samples that decoded with a valid frame CRC; frame_delivery_rate is unique displayed frames / expected packet frames.",
    "unique_frames": 1
  },
  "comparison": [
    {
      "basis": "E02 clean simulated channel vs E11 observed captures with known frames",
      "delta": 0.0,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "clean-cell accuracy",
      "observed": 1.0,
      "simulated": 1.0,
      "unit": "fraction"
    },
    {
      "basis": "E09 64 simulated trials vs E11 one physical packet; sample sizes differ",
      "delta": -0.75,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "file-transfer success",
      "observed": 0.0,
      "simulated": 0.75,
      "unit": "fraction"
    },
    {
      "basis": "E10 software decode mean vs E11 observed-image decode mean (same decoder)",
      "delta": 7.012033173305099,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "decode latency",
      "observed": 12.815624999348074,
      "simulated": 5.803591826042975,
      "unit": "ms/frame"
    },
    {
      "basis": "E01 payload arithmetic at 60 fps vs E11 at the observed 10 fps; the rate ratio is mostly the display rate",
      "delta": null,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "raw payload bit rate at 60 fps",
      "observed": null,
      "simulated": 5280,
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
    "decode_attempts": 1,
    "decode_ms": {
      "max": 12.815624999348074,
      "mean": 12.815624999348074,
      "min": 12.815624999348074,
      "n": 1.0,
      "p50": 12.815624999348074,
      "p95": 12.815624999348074,
      "std": 0.0
    },
    "decode_samples_fps": 78.02974884571526,
    "decode_wall_s": 0.012815624999348074,
    "packet_decode_ms": 0.04620799154508859,
    "reassembly_ms": 0.00012500095181167126,
    "reconstruction_ms": 0.04633299249690026,
    "resource": {
      "cpu_percent": 168.8642975351246,
      "cpu_s": 0.07979000000000003,
      "max_rss_kb": 114576,
      "rss_kb": 114576,
      "wall_s": 0.04725095900357701
    }
  },
  "note": "PHYSICAL camera bytes decoded by software. Accuracy is relative to the displayed frame only where the operator recorded an independent frame mapping; video frame identity comes from the OTL header.",
  "packet_summary": {
    "corrected_symbols": 0,
    "erased_frames": 0,
    "packet_loss_rate": null,
    "packets_expected": null,
    "packets_received": 0,
    "rs_nsym": 32
  },
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
    "compressed": null,
    "compression_ratio": null,
    "display_fps_manifest": 10.0,
    "display_fps_observed": null,
    "display_fps_used": 10.0,
    "expected_frames": 255,
    "frame_delivery_rate": 0.00392156862745098,
    "frame_loss_rate": 0.996078431372549,
    "frames_captured": 1,
    "frames_decoded": 1,
    "net_bps": null,
    "note": "All rates are reported only when the complete payload was reassembled and its SHA-256 matched. raw_channel_bps and raw_payload_bps are gross rates at the observed display rate; rs_goodput_bps is the packet capacity after RS(255,223); net_bps is the SHA-verified application payload. Repeated camera samples of one displayed frame are counted once.",
    "original_bytes": 0,
    "packet_duration_s": 25.5,
    "payload_bytes": 0,
    "payload_error": null,
    "payload_sha256": null,
    "payload_success": false,
    "raw_channel_bps": null,
    "raw_payload_bps": null,
    "rs_goodput_bps": null,
    "unique_frames": 1,
    "wire_bytes": 0
  }
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

PHYSICAL / CAMERA CAPTURE. Session m9-iphone14-2-20261108T103717Z from iPhone14,2 (Continuity Camera, 'Arsh Camera') capturing a Apple M5 built-in Liquid Retina (MacBook Air): 1 camera samples, 1 passed the frame CRC (100.0%); 1/255 unique displayed frames (0.4%). Mean cell accuracy 1.000 and bit accuracy 1.000 over 1 unique frames with a display mapping. No complete payload was reassembled from this session. Decode latency 12.82 ms per camera sample, packet decode + reassembly 0.05 ms, decode throughput 78.0 samples/s. All physical numbers come from the preserved camera files; decoding is software. Compare with E01–E10 only through the comparison table, which states the basis of every pair.

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
  "timestamp_utc": "2026-11-08T10:57:02.050160+00:00",
  "zstandard": "0.25.0"
}
```
