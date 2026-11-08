# E11_physical — Physical optical validation (screen → camera)

- Run: `20261108T105237Z-72c1d8`
- Classification: **PHYSICAL (camera capture) + SOFTWARE (decode)**
- Evidence source: **PHYSICAL / CAMERA CAPTURE**
- Device: **iPhone14,2 (Continuity Camera, 'Arsh Camera')**
- Trials: 869
- Wall time: 33.55 s
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
    "format": "H.264 MP4 via AVFoundation",
    "fps": 30.0,
    "iso": "auto",
    "mode": "video",
    "notes": "capture command: python3 -m otl capture video 1 --out datasets/physical/m9-iphone14-2-packet-20261108T104529Z/captures/originals/packet_10fps.mp4 --duration 29 --fps 30 --size 1920x1440",
    "resolution": "1920x1440",
    "stabilization": "not applicable (hand-held, software capture)",
    "zoom": "1x"
  },
  "capture_source": "camera",
  "captures": 869,
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
    "notes": "Safari frontmost, player.html?fps=10; 255-frame packet loops every 25.5 s",
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
  "session_id": "m9-iphone14-2-packet-20261108T104529Z",
  "session_notes": "Full 255-frame packet 0 at 10 display fps (cycle 25.5 s). 29 s capture exceeds one cycle so every frame index is observed at least once.",
  "session_path": "datasets/physical/m9-iphone14-2-packet-20261108T104529Z",
  "transmitter": {
    "attached_utc": "2026-11-08T10:48:51.891236+00:00",
    "fps": 10.0,
    "frame_count": 255,
    "frames_sha256": "207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348",
    "hold": false,
    "payload_name": "payload.txt",
    "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
    "player_manifest": "display/player_manifest.json",
    "player_manifest_sha256": "635fab9b278ae6d634297668cf616ff07aaf8373bfddf9ed7ccbcc175af176d0"
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
      "n": 255.0,
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
      "n": 255.0,
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
    "format": "H.264 MP4 via AVFoundation",
    "fps": 30.0,
    "iso": "auto",
    "mode": "video",
    "notes": "capture command: python3 -m otl capture video 1 --out datasets/physical/m9-iphone14-2-packet-20261108T104529Z/captures/originals/packet_10fps.mp4 --duration 29 --fps 30 --size 1920x1440",
    "resolution": "1920x1440",
    "stabilization": "not applicable (hand-held, software capture)",
    "zoom": "1x"
  },
  "capture_source": "camera",
  "captures": {
    "attempt_failure_rate": 0.06098964326812428,
    "count": 869,
    "crc_rate": 0.9390103567318757,
    "decoded_crc_ok": 816,
    "detection_failures": 34,
    "duplicate_files": 0,
    "error_counts": {
      "E_DETECT": 34
    },
    "expected_frames": 255,
    "files": 869,
    "frame_delivery_rate": 1.0,
    "frame_index_matches": 0,
    "frame_loss_rate": 0.0,
    "ground_truth_attempts": 816,
    "ground_truth_frames": 255,
    "image_files": 869,
    "media_files": 1,
    "note": "count is unique image SHA-256 values; files includes byte-identical duplicates from a burst. crc_rate is the fraction of camera samples that decoded with a valid frame CRC; frame_delivery_rate is unique displayed frames / expected packet frames.",
    "unique_frames": 255
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
      "basis": "E09 all-channel simulated success rate vs E11 observed frame CRC rate",
      "delta": 0.18901035673187572,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "frame CRC success rate",
      "observed": 0.9390103567318757,
      "simulated": 0.75,
      "unit": "fraction"
    },
    {
      "basis": "E10 software decode mean vs E11 observed-image decode mean (same decoder)",
      "delta": 1.5374703162650816,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "decode latency",
      "observed": 7.341062142308057,
      "simulated": 5.803591826042975,
      "unit": "ms/frame"
    },
    {
      "basis": "E01 theoretical 60 fps vs E11 unique delivered frames / observed display period",
      "delta": -6320.087991200898,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "raw payload bit rate",
      "observed": 879.9120087991021,
      "simulated": 7200,
      "unit": "bps"
    },
    {
      "basis": "E09 projected 60 fps mean vs E11 SHA-verified payload / observed display period",
      "delta": -3429.9707284173564,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "metric": "net throughput at 60 fps",
      "observed": 99.44103628852598,
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
    "notes": "Safari frontmost, player.html?fps=10; 255-frame packet loops every 25.5 s",
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
    "decode_attempts": 869,
    "decode_ms": {
      "max": 11.314916991977952,
      "mean": 7.341062142308057,
      "min": 2.2562500089406967,
      "n": 869.0,
      "p50": 7.5084159907419235,
      "p95": 8.118641396868043,
      "std": 1.059804476838257
    },
    "decode_samples_fps": 136.2200701499029,
    "decode_wall_s": 6.379383001665701,
    "packet_decode_ms": 2.0261659956304356,
    "reassembly_ms": 0.04779099253937602,
    "reconstruction_ms": 2.0739569881698117,
    "resource": {
      "cpu_percent": 172.43203963710195,
      "cpu_s": 57.832032999999996,
      "max_rss_kb": 119200,
      "rss_kb": 119200,
      "wall_s": 33.53902970800118
    }
  },
  "note": "PHYSICAL camera bytes decoded by software. Accuracy is relative to the displayed frame only where the operator recorded an independent frame mapping; video frame identity comes from the OTL header.",
  "packet_summary": {
    "corrected_symbols": 0,
    "erased_frames": 0,
    "packet_loss_rate": 0.0,
    "packets_expected": 1,
    "packets_received": 1,
    "rs_nsym": 32
  },
  "packets": [
    {
      "decoded": true,
      "frames_present": 255,
      "packet_id": 0,
      "stats": {
        "block_failures": [],
        "corrected_per_block": [
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0
        ],
        "erasures": [],
        "frames_missing": 0,
        "frames_present": 255
      }
    }
  ],
  "session_id": "m9-iphone14-2-packet-20261108T104529Z",
  "status": "measured",
  "throughput": {
    "capture_duration_s": 28.970769999999998,
    "capture_fps": 30.0,
    "compressed": true,
    "compression_ratio": 1.0782312925170068,
    "display_fps_manifest": 10.0,
    "display_fps_observed": 9.999000099989797,
    "display_fps_used": 9.999000099989797,
    "expected_frames": 255,
    "frame_delivery_rate": 1.0,
    "frame_loss_rate": 0.0,
    "frames_captured": 869,
    "frames_decoded": 816,
    "net_bps": 99.44103628852598,
    "note": "raw_channel_bps and raw_payload_bps are gross rates at the observed display rate; rs_goodput_bps is the packet capacity after RS(255,223); net_bps is the SHA-verified application payload. Repeated camera samples of one displayed frame are counted once. net_bps is only reported when the complete payload was reassembled and its SHA-256 matched.",
    "original_bytes": 317,
    "packet_duration_s": 25.50255000000052,
    "payload_bytes": 317,
    "payload_error": null,
    "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
    "payload_success": true,
    "raw_channel_bps": 1199.8800119987757,
    "raw_payload_bps": 879.9120087991021,
    "rs_goodput_bps": 769.4916782831364,
    "unique_frames": 255,
    "wire_bytes": 294
  }
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

PHYSICAL / CAMERA CAPTURE. Session m9-iphone14-2-packet-20261108T104529Z from iPhone14,2 (Continuity Camera, 'Arsh Camera') capturing a Apple M5 built-in Liquid Retina (MacBook Air): 869 camera samples, 816 passed the frame CRC (93.9%); 255/255 unique displayed frames (100.0%). Mean cell accuracy 1.000 and bit accuracy 1.000 over 255 unique frames with a display mapping. A complete payload of 317 bytes was recovered from 294 compressed bytes (1.08x) and its SHA-256 matched the transmitted payload. At the observed 10.00 display fps the gross channel rate is 1200 bps, the gross payload rate is 880 bps, the RS(255,223) goodput is 769 bps and the SHA-verified application rate is 99 bps. Decode latency 7.34 ms per camera sample, packet decode + reassembly 2.07 ms, decode throughput 136.2 samples/s. All physical numbers come from the preserved camera files; decoding is software. Compare with E01–E10 only through the comparison table, which states the basis of every pair.

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
      "format": "H.264 MP4 via AVFoundation",
      "fps": 30.0,
      "iso": "auto",
      "mode": "video",
      "notes": "capture command: python3 -m otl capture video 1 --out datasets/physical/m9-iphone14-2-packet-20261108T104529Z/captures/originals/packet_10fps.mp4 --duration 29 --fps 30 --size 1920x1440",
      "resolution": "1920x1440",
      "stabilization": "not applicable (hand-held, software capture)",
      "zoom": "1x"
    },
    "display": {
      "brightness": "not measured (macOS default)",
      "height_px": 1664,
      "kind": "computer",
      "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
      "notes": "Safari frontmost, player.html?fps=10; 255-frame packet loops every 25.5 s",
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
  "timestamp_utc": "2026-11-08T10:53:11.265847+00:00",
  "zstandard": "0.25.0"
}
```
