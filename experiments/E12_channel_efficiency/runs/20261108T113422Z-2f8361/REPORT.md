# E12_channel_efficiency — Physical channel efficiency and reliability

- Run: `20261108T113422Z-2f8361`
- Classification: **PHYSICAL (camera capture) + SOFTWARE (decode/analysis)**
- Evidence source: **PHYSICAL / CAMERA CAPTURE**
- Device: **iPhone14,2 (Continuity Camera, 'Arsh Camera')**
- Trials: 7
- Wall time: 228.42 s
- Quick mode: False

## Hypothesis

The gap between RS(255,223) goodput and application throughput is dominated by unused packet capacity (payload utilisation), not by display refresh, camera capture, detection, decoding or RS correction; independent baseline sessions repeat the protocol rates while camera-sample reliability may vary.

## Controlled variables

- protocol
- layout
- renderer
- decoder
- payload
- frame set
- display playback rate

## Independent variables

- device
- display
- distance
- angle
- ambient light
- display brightness
- capture settings

## Dependent variables

- gross channel rate
- gross payload rate
- RS goodput
- application throughput
- application payload utilisation per frame
- CRC and unique-frame delivery
- RS corrections and packet loss
- decode latency and throughput
- baseline repeatability
- bottleneck attribution

## Procedure

1. Freeze the successful M9 protocol, payload, frame set and decoder.
2. Read only finalized physical sessions with a valid session.lock.json.
3. Decode every preserved camera sample and count unique displayed frames.
4. Compute gross channel, gross payload, RS goodput and application rates with the observed display period as denominator.
5. Compute application bytes per frame and the loss decomposition from channel to application.
6. Aggregate independent baseline sessions and report throughput and reliability spread separately.
7. Vary only factors for which actual values are recorded; leave the rest UNMEASURED.
8. Label measured values and arithmetic projections separately.

## Experiment metadata

```json
{
  "evidence_source": "PHYSICAL / CAMERA CAPTURE",
  "note": "E12 reads finalized sessions only. It never modifies session files or earlier run directories.",
  "sessions": [
    "m10-baseline-01-20261108T112241Z",
    "m10-baseline-02-20261108T112441Z",
    "m10-baseline-03-20261108T112602Z",
    "m10-brightness-065-20261108T112854Z",
    "m10-brightness-090-20261108T113031Z",
    "m9-iphone14-2-20261108T103717Z",
    "m9-iphone14-2-packet-20261108T104529Z"
  ]
}
```

## Processed results

```json
{
  "baseline_repeatability": {
    "crc_rate": {
      "cv": 0.15678620221319503,
      "max": 0.8887652947719689,
      "mean": 0.7315954385976633,
      "min": 0.6182432432432432,
      "n": 3.0,
      "p50": 0.6877777777777778,
      "std": 0.11470407037422435
    },
    "decode_ms_mean": {
      "cv": 0.026610927338304606,
      "max": 7.659340287565202,
      "mean": 7.452629247863208,
      "min": 7.185109293811718,
      "n": 3.0,
      "p50": 7.513438162212705,
      "std": 0.19832137539421155
    },
    "estimated": false,
    "frame_delivery_rate": {
      "cv": 0.016835875742536838,
      "max": 1.0,
      "mean": 0.9882352941176471,
      "min": 0.9647058823529412,
      "n": 3.0,
      "p50": 1.0,
      "std": 0.016637806616154053
    },
    "metrics": {
      "application_bps": {
        "cv": 0.0,
        "max": 99.44103628852598,
        "mean": 99.44103628852598,
        "min": 99.44103628852598,
        "n": 3.0,
        "p50": 99.44103628852598,
        "std": 0.0
      },
      "application_payload_utilisation_per_frame": {
        "cv": 0.0,
        "max": 0.11301247771836008,
        "mean": 0.11301247771836008,
        "min": 0.11301247771836008,
        "n": 3.0,
        "p50": 0.11301247771836008,
        "std": 0.0
      },
      "application_share_of_rs_goodput": {
        "cv": 0.0,
        "max": 0.1292295148797391,
        "mean": 0.1292295148797391,
        "min": 0.1292295148797391,
        "n": 3.0,
        "p50": 0.1292295148797391,
        "std": 0.0
      },
      "channel_bps": {
        "cv": 0.0,
        "max": 1199.8800119987757,
        "mean": 1199.8800119987757,
        "min": 1199.8800119987757,
        "n": 3.0,
        "p50": 1199.8800119987757,
        "std": 0.0
      },
      "gross_payload_bps": {
        "cv": 0.0,
        "max": 879.9120087991021,
        "mean": 879.9120087991021,
        "min": 879.9120087991021,
        "n": 3.0,
        "p50": 879.9120087991021,
        "std": 0.0
      },
      "rs_goodput_bps": {
        "cv": 0.0,
        "max": 769.4916782831364,
        "mean": 769.4916782831364,
        "min": 769.4916782831364,
        "n": 3.0,
        "p50": 769.4916782831364,
        "std": 0.0
      }
    },
    "n": 3,
    "note": "Repeatability is claimed only when at least two independent physical sessions deliver the full payload with 100% unique-frame delivery and the throughput metrics agree within 1% CV. Reliability (camera-sample CRC rate) may vary; it is reported separately and is not used to hide sample failures.",
    "repeatable": false,
    "sessions": [
      "m10-baseline-01-20261108T112241Z",
      "m10-baseline-02-20261108T112441Z",
      "m10-baseline-03-20261108T112602Z"
    ],
    "throughput_cv": 0.0
  },
  "bottleneck": {
    "baseline_throughput_cv": 0.0,
    "display": {
      "hardware_to_playback_ratio": 6.000600000000123,
      "note": "The 60 Hz panel was driven at the configured 10 fps. The 6x difference is a playback configuration choice, not a measured 60 fps result.",
      "panel_refresh_hz": 60.0,
      "playback_fps": 9.999000099989797
    },
    "loss_ranking": [
      {
        "bps": 677.2656067726423,
        "fraction_of_channel": 0.5644444444444444,
        "stage": "unused_packet_capacity"
      },
      {
        "bps": 319.9680031996736,
        "fraction_of_channel": 0.2666666666666667,
        "stage": "framing_header_and_crc"
      },
      {
        "bps": 110.4203305159657,
        "fraction_of_channel": 0.09202614379084963,
        "stage": "reed_solomon_parity"
      }
    ],
    "not_bottlenecks": [
      {
        "evidence": "30.0 fps camera vs 9.999 fps display; 3.00x headroom",
        "stage": "camera capture",
        "status": "measured"
      },
      {
        "evidence": "133.9 decoded samples/s vs 30.0 fps camera; 4.46x headroom",
        "stage": "decode",
        "status": "measured"
      },
      {
        "evidence": "0 corrected symbols and 0 erased frames",
        "stage": "reed-solomon correction",
        "status": "measured"
      },
      {
        "evidence": "1/1 packets; loss 0.0",
        "stage": "packet loss",
        "status": "measured"
      },
      {
        "evidence": "816/869 camera samples passed CRC, but unique-frame delivery was 1.000",
        "stage": "detection / CRC",
        "status": "measured; did not reduce delivered frames"
      }
    ],
    "note": "Attribution uses the measured loss decomposition, not opinion. A stage is called limiting only when its measured loss is the largest positive term or when it prevents delivery.",
    "packet": {
      "packet_bytes": 2453,
      "packet_fill_application": 0.1292295148797391,
      "packet_fill_wire": 0.11985324092947411,
      "packet_payload_capacity_utilisation": 0.12143742255266418,
      "payload_bytes": 317,
      "wire_bytes": 294
    },
    "per_frame": {
      "application_bytes_per_frame": 1.2431372549019608,
      "application_payload_utilisation_per_frame": 0.11301247771836008,
      "frame_payload_capacity_bytes": 11,
      "wire_bytes_per_frame": 1.1529411764705881,
      "wire_payload_utilisation_per_frame": 0.10481283422459892
    },
    "primary": "application payload utilisation (unused packet capacity)",
    "primary_fraction_of_channel": 0.5644444444444444,
    "primary_loss_bps": 677.2656067726423,
    "primary_stage": "unused_packet_capacity",
    "secondary_fraction_of_channel": 0.2666666666666667,
    "secondary_loss_bps": 319.9680031996736,
    "secondary_stage": "framing_header_and_crc"
  },
  "brightness_series": [
    {
      "application_bps": null,
      "bit_margin_mean": 0.764662945139335,
      "brightness_fraction": 0.65,
      "contrast_mean": 0.7224215373050179,
      "crc_rate": 0.45790934320074006,
      "decode_ms_mean": 5.55442683820608,
      "frame_delivery_rate": 0.6862745098039216,
      "payload_success": false,
      "rs_goodput_bps": null,
      "session_id": "m10-brightness-065-20261108T112854Z"
    },
    {
      "application_bps": null,
      "bit_margin_mean": 0.7495867818201112,
      "brightness_fraction": 0.9,
      "contrast_mean": 0.701959413135883,
      "crc_rate": 0.4717832957110609,
      "decode_ms_mean": 5.091504529012766,
      "frame_delivery_rate": 0.5725490196078431,
      "payload_success": false,
      "rs_goodput_bps": null,
      "session_id": "m10-brightness-090-20261108T113031Z"
    }
  ],
  "definitions": {
    "application_bps": "SHA-verified application payload bytes x 8 / packet duration",
    "application_payload_utilisation_per_frame": "(application payload bytes / expected displayed frames) / 11 payload bytes per frame",
    "denominator": "The observed display frame period is the shared denominator. Camera samples and panel refresh are not denominators.",
    "gross_channel_bps": "120 bits/frame x observed display fps",
    "gross_payload_bps": "88 payload bits/frame x observed display fps",
    "packet_fill": "application wire bytes / 2,453 RS data bytes",
    "rs_goodput_bps": "2,453 RS data bytes/packet x 8 / (255 frames / observed display fps)"
  },
  "evidence_source": "PHYSICAL / CAMERA CAPTURE",
  "factor_coverage": {
    "ambient_lux": {
      "measured": false,
      "statuses": [
        "UNMEASURED"
      ],
      "values": [],
      "varied": false
    },
    "angle_deg": {
      "measured": false,
      "statuses": [
        "UNMEASURED"
      ],
      "values": [],
      "varied": false
    },
    "display_brightness_fraction": {
      "measured": true,
      "statuses": [
        "MEASURED (DisplayServicesGetBrightness)",
        "UNMEASURED"
      ],
      "values": [
        0.65,
        0.9
      ],
      "varied": true
    },
    "distance_mm": {
      "measured": false,
      "statuses": [
        "UNMEASURED"
      ],
      "values": [],
      "varied": false
    },
    "lighting": {
      "measured": false,
      "statuses": [
        "OPERATOR-RECORDED"
      ],
      "values": [
        "indoor, unchanged from M9; illuminance not measured",
        "indoor, unchanged from baseline; illuminance not measured",
        "indoor"
      ],
      "varied": true
    },
    "unvaried": [
      "distance_mm",
      "angle_deg",
      "ambient_lux"
    ]
  },
  "frozen_configuration": {
    "config_sha256": "7e1db99b9118a6b1530a5c0742900ae285cdab3b1ff6667a4c825765e71263b3",
    "deviations": [],
    "frames_sha256": "207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348",
    "note": "The M9 frame format, packet layout, RS(255,223), compression, renderer and decoder geometry are unchanged.",
    "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
    "reference_session": "m9-iphone14-2-packet-20261108T104529Z",
    "sessions_checked": 7
  },
  "measured_vs_projection": {
    "baseline_repeatability": {
      "crc_rate": {
        "cv": 0.15678620221319503,
        "max": 0.8887652947719689,
        "mean": 0.7315954385976633,
        "min": 0.6182432432432432,
        "n": 3.0,
        "p50": 0.6877777777777778,
        "std": 0.11470407037422435
      },
      "decode_ms_mean": {
        "cv": 0.026610927338304606,
        "max": 7.659340287565202,
        "mean": 7.452629247863208,
        "min": 7.185109293811718,
        "n": 3.0,
        "p50": 7.513438162212705,
        "std": 0.19832137539421155
      },
      "estimated": false,
      "frame_delivery_rate": {
        "cv": 0.016835875742536838,
        "max": 1.0,
        "mean": 0.9882352941176471,
        "min": 0.9647058823529412,
        "n": 3.0,
        "p50": 1.0,
        "std": 0.016637806616154053
      },
      "metrics": {
        "application_bps": {
          "cv": 0.0,
          "max": 99.44103628852598,
          "mean": 99.44103628852598,
          "min": 99.44103628852598,
          "n": 3.0,
          "p50": 99.44103628852598,
          "std": 0.0
        },
        "application_payload_utilisation_per_frame": {
          "cv": 0.0,
          "max": 0.11301247771836008,
          "mean": 0.11301247771836008,
          "min": 0.11301247771836008,
          "n": 3.0,
          "p50": 0.11301247771836008,
          "std": 0.0
        },
        "application_share_of_rs_goodput": {
          "cv": 0.0,
          "max": 0.1292295148797391,
          "mean": 0.1292295148797391,
          "min": 0.1292295148797391,
          "n": 3.0,
          "p50": 0.1292295148797391,
          "std": 0.0
        },
        "channel_bps": {
          "cv": 0.0,
          "max": 1199.8800119987757,
          "mean": 1199.8800119987757,
          "min": 1199.8800119987757,
          "n": 3.0,
          "p50": 1199.8800119987757,
          "std": 0.0
        },
        "gross_payload_bps": {
          "cv": 0.0,
          "max": 879.9120087991021,
          "mean": 879.9120087991021,
          "min": 879.9120087991021,
          "n": 3.0,
          "p50": 879.9120087991021,
          "std": 0.0
        },
        "rs_goodput_bps": {
          "cv": 0.0,
          "max": 769.4916782831364,
          "mean": 769.4916782831364,
          "min": 769.4916782831364,
          "n": 3.0,
          "p50": 769.4916782831364,
          "std": 0.0
        }
      },
      "n": 3,
      "note": "Repeatability is claimed only when at least two independent physical sessions deliver the full payload with 100% unique-frame delivery and the throughput metrics agree within 1% CV. Reliability (camera-sample CRC rate) may vary; it is reported separately and is not used to hide sample failures.",
      "repeatable": false,
      "sessions": [
        "m10-baseline-01-20261108T112241Z",
        "m10-baseline-02-20261108T112441Z",
        "m10-baseline-03-20261108T112602Z"
      ],
      "throughput_cv": 0.0
    },
    "measured": {
      "application_bps": 99.44103628852598,
      "application_payload_utilisation_per_frame": 0.11301247771836008,
      "application_share_of_rs_goodput": 0.1292295148797391,
      "channel_bps": 1199.8800119987757,
      "display_fps": 9.999000099989797,
      "gross_payload_bps": 879.9120087991021,
      "rs_goodput_bps": 769.4916782831364,
      "session_id": "m9-iphone14-2-packet-20261108T104529Z",
      "status": "MEASURED"
    },
    "note": "Measured values come from preserved camera files and the standard decoder. Projections are arithmetic at the stated fps and payload size; no 60 fps physical capture was performed.",
    "projection": {
      "full_one_packet_at_60fps": {
        "application_bps": 4557.176470588235,
        "channel_bps": 7200.0,
        "duration_s": 4.25,
        "fps": 60.0,
        "frames": 255,
        "gross_payload_bps": 5280.0,
        "packet_payload_capacity_bytes": 2421,
        "packets": 1,
        "payload_bytes": 2421,
        "payload_capacity_utilisation": 1.0,
        "rs_goodput_bps": 4617.411764705882,
        "status": "PROJECTION \u2014 not measured"
      },
      "maximum_16_packet_transfer_at_60fps": {
        "application_bps": 4613.64705882353,
        "channel_bps": 7200.0,
        "duration_s": 68.0,
        "fps": 60.0,
        "frames": 4080,
        "gross_payload_bps": 5280.0,
        "packet_payload_capacity_bytes": 39216,
        "packets": 16,
        "payload_bytes": 39216,
        "payload_capacity_utilisation": 1.0,
        "rs_goodput_bps": 4617.411764705882,
        "status": "PROJECTION \u2014 not measured"
      },
      "same_payload_at_60fps": {
        "application_bps": 596.7058823529412,
        "channel_bps": 7200.0,
        "duration_s": 4.25,
        "fps": 60.0,
        "frames": 255,
        "gross_payload_bps": 5280.0,
        "packet_payload_capacity_bytes": 2421,
        "packets": 1,
        "payload_bytes": 317,
        "payload_capacity_utilisation": 0.13093762907889303,
        "rs_goodput_bps": 4617.411764705882,
        "status": "PROJECTION \u2014 not measured"
      },
      "same_payload_at_observed_fps": {
        "application_bps": 99.44103628852598,
        "channel_bps": 1199.8800119987757,
        "duration_s": 25.50255000000052,
        "fps": 9.999000099989797,
        "frames": 255,
        "gross_payload_bps": 879.9120087991021,
        "packet_payload_capacity_bytes": 2421,
        "packets": 1,
        "payload_bytes": 317,
        "payload_capacity_utilisation": 0.13093762907889303,
        "rs_goodput_bps": 769.4916782831364,
        "status": "PROJECTION \u2014 not measured"
      },
      "status": "PROJECTION \u2014 not measured"
    }
  },
  "sessions": [
    {
      "capture_settings": {
        "exposure": "auto",
        "focus": "auto (Continuity Camera)",
        "format": "H.264 MP4 via AVFoundation",
        "fps": 30.0,
        "iso": "auto",
        "mode": "video",
        "notes": "Safari bounds approximately {0,28,1280,832}; player.html?fps=10; M10 baseline repeat 1",
        "resolution": "1920x1440",
        "stabilization": "not applicable (hand-held, software capture)",
        "zoom": "1x"
      },
      "capture_source": "camera",
      "captures": {
        "all_files": 889,
        "crc_failures_after_detection": 243,
        "crc_ok": 549,
        "crc_rate": 0.6182432432432432,
        "detection_failures": 96,
        "error_counts": {
          "E_DETECT": 96
        },
        "expected_frames": 255,
        "frame_delivery_rate": 1.0,
        "frame_loss_rate": 0.0,
        "ground_truth_frames": 255,
        "image_files": 888,
        "media_files": 1,
        "sample_redundancy": 3.4823529411764707,
        "samples_per_frame": {
          "cv": 0.32000278697264484,
          "max": 6.0,
          "mean": 2.152941176470588,
          "min": 1.0,
          "n": 255.0,
          "p50": 2.0,
          "std": 0.6889471766587529
        },
        "unique_frames": 255,
        "unique_images": 888
      },
      "device": {
        "camera": "rear camera, Continuity Camera, AVFoundation index 1",
        "model": "iPhone14,2 (Continuity Camera, 'Arsh Camera')",
        "notes": "",
        "os": "iOS (Continuity Camera via macOS)",
        "serial": ""
      },
      "display": {
        "brightness": "not measured (macOS default, unchanged from M9)",
        "height_px": 1664,
        "kind": "computer",
        "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
        "notes": "",
        "refresh_hz": 60.0,
        "width_px": 2560
      },
      "efficiency": {
        "application_bits_per_frame": 9.945098039215686,
        "application_bps": 99.44103628852598,
        "application_bytes_per_frame": 1.2431372549019608,
        "application_payload_capacity_utilisation": 0.13093762907889303,
        "application_payload_utilisation_per_frame": 0.11301247771836008,
        "application_share_of_channel": 0.08287581699346405,
        "application_share_of_gross_payload": 0.11301247771836008,
        "application_share_of_rs_goodput": 0.1292295148797391,
        "channel_bps": 1199.8800119987757,
        "compressed": true,
        "compression_ratio": 1.0782312925170068,
        "data_bytes_per_frame": 11,
        "display_fps": 9.999000099989797,
        "dominant_loss": {
          "bps": 677.2656067726423,
          "fraction_of_channel": 0.5644444444444444,
          "stage": "unused_packet_capacity"
        },
        "expected_frames": 255,
        "file_header_bytes": 32,
        "frame_bits": 120,
        "frame_payload_utilisation": 0.7333333333333333,
        "frame_protocol_overhead": 0.26666666666666666,
        "gross_payload_bps": 879.9120087991021,
        "losses": [
          {
            "bps": 319.9680031996736,
            "fraction_of_channel": 0.2666666666666667,
            "stage": "framing_header_and_crc"
          },
          {
            "bps": 110.4203305159657,
            "fraction_of_channel": 0.09202614379084963,
            "stage": "reed_solomon_parity"
          },
          {
            "bps": 677.2656067726423,
            "fraction_of_channel": 0.5644444444444444,
            "stage": "unused_packet_capacity"
          },
          {
            "bps": -7.214964778031856,
            "fraction_of_channel": -0.0060130718954248385,
            "stage": "compression_gain"
          }
        ],
        "note": "Measured rates use the observed display period and SHA-verified payload. The per-frame utilisation denominator is 11 payload bytes/frame; the packet denominator is 2,453 RS data bytes.",
        "packet_bytes": 2453,
        "packet_duration_s": 25.50255000000052,
        "packet_fill_application": 0.1292295148797391,
        "packet_fill_file_object": 0.13289849164288625,
        "packet_fill_wire": 0.11985324092947411,
        "packet_payload_capacity_bytes": 2421,
        "packet_payload_capacity_utilisation": 0.12143742255266418,
        "payload_bits_per_frame": 88,
        "payload_bytes": 317,
        "residual_bps": 0.0,
        "rs_code_rate": 0.8745098039215686,
        "rs_goodput_bps": 769.4916782831364,
        "rs_overhead_fraction": 0.12549019607843137,
        "rs_to_application_gap_bps": 670.0506419946104,
        "rs_to_application_ratio": 7.738170347003154,
        "wire_bytes": 294,
        "wire_bytes_per_frame": 1.1529411764705881,
        "wire_payload_bps": 92.22607151049412,
        "wire_payload_utilisation_per_frame": 0.10481283422459892,
        "wire_share_of_rs_goodput": 0.11985324092947411
      },
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "factor": {
        "factors": {
          "ambient_lux": {
            "status": "UNMEASURED",
            "unit": "lux",
            "value": null
          },
          "angle_deg": {
            "status": "UNMEASURED",
            "unit": "deg",
            "value": null
          },
          "display_brightness_fraction": {
            "status": "UNMEASURED",
            "unit": "fraction of controller range (0..1); not nits",
            "value": null
          },
          "distance_mm": {
            "status": "UNMEASURED",
            "unit": "mm",
            "value": null
          },
          "lighting": {
            "status": "OPERATOR-RECORDED",
            "unit": "description",
            "value": "indoor, unchanged from M9; illuminance not measured"
          }
        },
        "unmeasured": [
          "distance_mm",
          "angle_deg",
          "ambient_lux",
          "display_brightness_fraction"
        ]
      },
      "geometry": {
        "ambient_lux": null,
        "angle_deg": null,
        "distance_mm": null,
        "hand_held": null,
        "lighting": "indoor, unchanged from M9; illuminance not measured",
        "notes": "baseline repeat of frozen M9 setup; distance, angle and ambient lux not measured"
      },
      "latency": {
        "decode_ms": {
          "max": 8.923417000914924,
          "mean": 7.185109293811718,
          "min": 2.1600829932140186,
          "n": 888.0,
          "p50": 7.680999995500315,
          "p95": 8.304545951250475,
          "std": 1.648829192725929
        },
        "decode_samples_fps": 139.17672774459604,
        "decode_wall_s": 6.380377052904805,
        "packet_decode_ms": 2.1067920024506748,
        "reassembly_ms": 0.057792000006884336,
        "reconstruction_ms": 2.164584002457559,
        "resource": {
          "cpu_percent": 147.22585385012752,
          "cpu_s": 54.959444000000005,
          "max_rss_kb": 119664,
          "rss_kb": 119664,
          "wall_s": 37.330022249996546
        }
      },
      "media": [
        {
          "bytes": 358184442,
          "kind": "video",
          "path": "captures/originals/packet_10fps.mp4",
          "sha256": "a86c611f2e3d264e5a28c3dc9164a07d2f9900d522a0ade859f637309889451b"
        }
      ],
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
      "payload": {
        "compressed": true,
        "compression_ratio": 1.0782312925170068,
        "original_bytes": 317,
        "payload_bytes": 317,
        "wire_bytes": 294
      },
      "reliability": {
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
        "corrected_symbols": 0,
        "erased_frames": 0,
        "expected_payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "packet_loss_rate": 0.0,
        "packets_expected": 1,
        "packets_received": 1,
        "payload_error": null,
        "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "payload_success": true,
        "rs_nsym": 32
      },
      "series": "baseline",
      "session_id": "m10-baseline-01-20261108T112241Z",
      "session_lock_sha256": "cfd9ffd35a50f876b9a1ce9c6a3aada978fcc4c80923b9952d84b93c77ea82fb",
      "session_path": "/Users/arshbuttar/OPTICAL_TRANSMISSION_LAB/datasets/physical/m10-baseline-01-20261108T112241Z",
      "signal": {
        "bit_margin": {
          "max": 0.8588082861474674,
          "mean": 0.8200093973978437,
          "min": 0.7619612302360839,
          "n": 792.0,
          "p50": 0.8246864092810442,
          "p95": 0.844488271628986,
          "std": 0.018932026241679337
        },
        "camera_luma_p50": {
          "max": 87.0,
          "mean": 60.398648648648646,
          "min": 29.0,
          "n": 888.0,
          "p50": 61.0,
          "p95": 66.0,
          "std": 8.08171097156435
        },
        "camera_luma_p99": {
          "max": 237.0,
          "mean": 224.9301914414412,
          "min": 119.0,
          "n": 888.0,
          "p50": 232.0,
          "p95": 234.0,
          "std": 23.650046013218418
        },
        "contrast": {
          "max": 0.7686274509803922,
          "mean": 0.7539463260051495,
          "min": 0.7215686274509804,
          "n": 792.0,
          "p50": 0.7568627450980392,
          "p95": 0.7647058823529411,
          "std": 0.008847120192579763
        },
        "fiducial_confidence": {
          "max": 0.872517154207295,
          "mean": 0.8550280418427053,
          "min": 0.4529411764705882,
          "n": 792.0,
          "p50": 0.8607342663381836,
          "p95": 0.8673852562239659,
          "std": 0.026933357530096395
        },
        "note": "Camera pixel statistics measure the received image, not display nits or ambient illuminance."
      },
      "status": "ok",
      "timing": {
        "camera_to_display_ratio": 3.0003000000000615,
        "capture_duration_s": 29.97092,
        "capture_fps": 30.0,
        "decode_to_capture_ratio": 4.6392242581532015,
        "display_fps_manifest": 10.0,
        "display_fps_observed": 9.999000099989797,
        "display_fps_used": 9.999000099989797,
        "expected_frames": 255,
        "packet_duration_s": 25.50255000000052,
        "unique_frames": 255
      },
      "transmitter": {
        "attached_utc": "2026-11-08T11:22:41.475284+00:00",
        "fps": 10.0,
        "frame_count": 255,
        "frames_sha256": "207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348",
        "hold": false,
        "payload_name": "payload.txt",
        "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "player_manifest": "display/player_manifest.json",
        "player_manifest_sha256": "635fab9b278ae6d634297668cf616ff07aaf8373bfddf9ed7ccbcc175af176d0"
      }
    },
    {
      "capture_settings": {
        "exposure": "auto",
        "focus": "auto (Continuity Camera)",
        "format": "H.264 MP4 via AVFoundation",
        "fps": 30.0,
        "iso": "auto",
        "mode": "video",
        "notes": "Safari bounds approximately {0,28,1280,832}; player.html?fps=10; M10 baseline repeat 2",
        "resolution": "1920x1440",
        "stabilization": "not applicable (hand-held, software capture)",
        "zoom": "1x"
      },
      "capture_source": "camera",
      "captures": {
        "all_files": 901,
        "crc_failures_after_detection": 281,
        "crc_ok": 619,
        "crc_rate": 0.6877777777777778,
        "detection_failures": 0,
        "error_counts": {},
        "expected_frames": 255,
        "frame_delivery_rate": 1.0,
        "frame_loss_rate": 0.0,
        "ground_truth_frames": 255,
        "image_files": 900,
        "media_files": 1,
        "sample_redundancy": 3.5294117647058822,
        "samples_per_frame": {
          "cv": 0.3578415998439014,
          "max": 5.0,
          "mean": 2.4274509803921567,
          "min": 2.0,
          "n": 255.0,
          "p50": 2.0,
          "std": 0.8686429423661762
        },
        "unique_frames": 255,
        "unique_images": 900
      },
      "device": {
        "camera": "rear camera, Continuity Camera, AVFoundation index 1",
        "model": "iPhone14,2 (Continuity Camera, 'Arsh Camera')",
        "notes": "",
        "os": "iOS (Continuity Camera via macOS)",
        "serial": ""
      },
      "display": {
        "brightness": "not measured (macOS default, unchanged from M9)",
        "height_px": 1664,
        "kind": "computer",
        "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
        "notes": "",
        "refresh_hz": 60.0,
        "width_px": 2560
      },
      "efficiency": {
        "application_bits_per_frame": 9.945098039215686,
        "application_bps": 99.44103628852598,
        "application_bytes_per_frame": 1.2431372549019608,
        "application_payload_capacity_utilisation": 0.13093762907889303,
        "application_payload_utilisation_per_frame": 0.11301247771836008,
        "application_share_of_channel": 0.08287581699346405,
        "application_share_of_gross_payload": 0.11301247771836008,
        "application_share_of_rs_goodput": 0.1292295148797391,
        "channel_bps": 1199.8800119987757,
        "compressed": true,
        "compression_ratio": 1.0782312925170068,
        "data_bytes_per_frame": 11,
        "display_fps": 9.999000099989797,
        "dominant_loss": {
          "bps": 677.2656067726423,
          "fraction_of_channel": 0.5644444444444444,
          "stage": "unused_packet_capacity"
        },
        "expected_frames": 255,
        "file_header_bytes": 32,
        "frame_bits": 120,
        "frame_payload_utilisation": 0.7333333333333333,
        "frame_protocol_overhead": 0.26666666666666666,
        "gross_payload_bps": 879.9120087991021,
        "losses": [
          {
            "bps": 319.9680031996736,
            "fraction_of_channel": 0.2666666666666667,
            "stage": "framing_header_and_crc"
          },
          {
            "bps": 110.4203305159657,
            "fraction_of_channel": 0.09202614379084963,
            "stage": "reed_solomon_parity"
          },
          {
            "bps": 677.2656067726423,
            "fraction_of_channel": 0.5644444444444444,
            "stage": "unused_packet_capacity"
          },
          {
            "bps": -7.214964778031856,
            "fraction_of_channel": -0.0060130718954248385,
            "stage": "compression_gain"
          }
        ],
        "note": "Measured rates use the observed display period and SHA-verified payload. The per-frame utilisation denominator is 11 payload bytes/frame; the packet denominator is 2,453 RS data bytes.",
        "packet_bytes": 2453,
        "packet_duration_s": 25.50255000000052,
        "packet_fill_application": 0.1292295148797391,
        "packet_fill_file_object": 0.13289849164288625,
        "packet_fill_wire": 0.11985324092947411,
        "packet_payload_capacity_bytes": 2421,
        "packet_payload_capacity_utilisation": 0.12143742255266418,
        "payload_bits_per_frame": 88,
        "payload_bytes": 317,
        "residual_bps": 0.0,
        "rs_code_rate": 0.8745098039215686,
        "rs_goodput_bps": 769.4916782831364,
        "rs_overhead_fraction": 0.12549019607843137,
        "rs_to_application_gap_bps": 670.0506419946104,
        "rs_to_application_ratio": 7.738170347003154,
        "wire_bytes": 294,
        "wire_bytes_per_frame": 1.1529411764705881,
        "wire_payload_bps": 92.22607151049412,
        "wire_payload_utilisation_per_frame": 0.10481283422459892,
        "wire_share_of_rs_goodput": 0.11985324092947411
      },
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "factor": {
        "factors": {
          "ambient_lux": {
            "status": "UNMEASURED",
            "unit": "lux",
            "value": null
          },
          "angle_deg": {
            "status": "UNMEASURED",
            "unit": "deg",
            "value": null
          },
          "display_brightness_fraction": {
            "status": "UNMEASURED",
            "unit": "fraction of controller range (0..1); not nits",
            "value": null
          },
          "distance_mm": {
            "status": "UNMEASURED",
            "unit": "mm",
            "value": null
          },
          "lighting": {
            "status": "OPERATOR-RECORDED",
            "unit": "description",
            "value": "indoor, unchanged from M9; illuminance not measured"
          }
        },
        "unmeasured": [
          "distance_mm",
          "angle_deg",
          "ambient_lux",
          "display_brightness_fraction"
        ]
      },
      "geometry": {
        "ambient_lux": null,
        "angle_deg": null,
        "distance_mm": null,
        "hand_held": null,
        "lighting": "indoor, unchanged from M9; illuminance not measured",
        "notes": "baseline repeat of frozen M9 setup; distance, angle and ambient lux not measured"
      },
      "latency": {
        "decode_ms": {
          "max": 8.903166992240585,
          "mean": 7.659340287565202,
          "min": 6.9229579967213795,
          "n": 900.0,
          "p50": 7.6216454981477,
          "p95": 8.263703507691389,
          "std": 0.3345162856551138
        },
        "decode_samples_fps": 130.5595472267346,
        "decode_wall_s": 6.893406258808682,
        "packet_decode_ms": 2.0637080015148968,
        "reassembly_ms": 0.037417004932649434,
        "reconstruction_ms": 2.101125006447546,
        "resource": {
          "cpu_percent": 141.5804259029217,
          "cpu_s": 52.375131,
          "max_rss_kb": 120656,
          "rss_kb": 120656,
          "wall_s": 36.99320062500192
        }
      },
      "media": [
        {
          "bytes": 372339961,
          "kind": "video",
          "path": "captures/originals/packet_10fps.mp4",
          "sha256": "d040664b11d95276365932349c4da27441f07606fb1a49b741f23c55bc1f444c"
        }
      ],
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
      "payload": {
        "compressed": true,
        "compression_ratio": 1.0782312925170068,
        "original_bytes": 317,
        "payload_bytes": 317,
        "wire_bytes": 294
      },
      "reliability": {
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
        "corrected_symbols": 0,
        "erased_frames": 0,
        "expected_payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "packet_loss_rate": 0.0,
        "packets_expected": 1,
        "packets_received": 1,
        "payload_error": null,
        "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "payload_success": true,
        "rs_nsym": 32
      },
      "series": "baseline",
      "session_id": "m10-baseline-02-20261108T112441Z",
      "session_lock_sha256": "a43502f7c407280c58d3d8d36cbf8f788a73d7667de2c375b9f7e7e7cc6dab5f",
      "session_path": "/Users/arshbuttar/OPTICAL_TRANSMISSION_LAB/datasets/physical/m10-baseline-02-20261108T112441Z",
      "signal": {
        "bit_margin": {
          "max": 0.8530049482681064,
          "mean": 0.8125297438802553,
          "min": 0.7245847331093692,
          "n": 900.0,
          "p50": 0.8221651241639701,
          "p95": 0.8401523517554065,
          "std": 0.02469287387889925
        },
        "camera_luma_p50": {
          "max": 74.0,
          "mean": 64.30666666666667,
          "min": 55.0,
          "n": 900.0,
          "p50": 64.0,
          "p95": 72.0,
          "std": 3.9241927690786147
        },
        "camera_luma_p99": {
          "max": 236.0,
          "mean": 231.64444444444445,
          "min": 227.0,
          "n": 900.0,
          "p50": 232.0,
          "p95": 234.0,
          "std": 1.707572097785567
        },
        "contrast": {
          "max": 0.7764705882352941,
          "mean": 0.7471108932461875,
          "min": 0.7215686274509804,
          "n": 900.0,
          "p50": 0.7490196078431373,
          "p95": 0.7607843137254902,
          "std": 0.00924599274896366
        },
        "fiducial_confidence": {
          "max": 0.8861016949152543,
          "mean": 0.8539257193583921,
          "min": 0.7596872875594833,
          "n": 900.0,
          "p50": 0.8532731319803346,
          "p95": 0.8775548253199584,
          "std": 0.015558147393122777
        },
        "note": "Camera pixel statistics measure the received image, not display nits or ambient illuminance."
      },
      "status": "ok",
      "timing": {
        "camera_to_display_ratio": 3.0003000000000615,
        "capture_duration_s": 29.970869999999998,
        "capture_fps": 30.0,
        "decode_to_capture_ratio": 4.35198490755782,
        "display_fps_manifest": 10.0,
        "display_fps_observed": 9.999000099989797,
        "display_fps_used": 9.999000099989797,
        "expected_frames": 255,
        "packet_duration_s": 25.50255000000052,
        "unique_frames": 255
      },
      "transmitter": {
        "attached_utc": "2026-11-08T11:24:41.988491+00:00",
        "fps": 10.0,
        "frame_count": 255,
        "frames_sha256": "207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348",
        "hold": false,
        "payload_name": "payload.txt",
        "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "player_manifest": "display/player_manifest.json",
        "player_manifest_sha256": "635fab9b278ae6d634297668cf616ff07aaf8373bfddf9ed7ccbcc175af176d0"
      }
    },
    {
      "capture_settings": {
        "exposure": "auto",
        "focus": "auto (Continuity Camera)",
        "format": "H.264 MP4 via AVFoundation",
        "fps": 30.0,
        "iso": "auto",
        "mode": "video",
        "notes": "Safari bounds approximately {0,28,1280,832}; player.html?fps=10; M10 baseline repeat 3",
        "resolution": "1920x1440",
        "stabilization": "not applicable (hand-held, software capture)",
        "zoom": "1x"
      },
      "capture_source": "camera",
      "captures": {
        "all_files": 900,
        "crc_failures_after_detection": 74,
        "crc_ok": 799,
        "crc_rate": 0.8887652947719689,
        "detection_failures": 26,
        "error_counts": {
          "E_DETECT": 26
        },
        "expected_frames": 255,
        "frame_delivery_rate": 0.9647058823529412,
        "frame_loss_rate": 0.03529411764705881,
        "ground_truth_frames": 246,
        "image_files": 899,
        "media_files": 1,
        "sample_redundancy": 3.654471544715447,
        "samples_per_frame": {
          "cv": 0.33879505364441453,
          "max": 6.0,
          "mean": 3.247967479674797,
          "min": 1.0,
          "n": 246.0,
          "p50": 3.0,
          "std": 1.1003953165117366
        },
        "unique_frames": 246,
        "unique_images": 899
      },
      "device": {
        "camera": "rear camera, Continuity Camera, AVFoundation index 1",
        "model": "iPhone14,2 (Continuity Camera, 'Arsh Camera')",
        "notes": "",
        "os": "iOS (Continuity Camera via macOS)",
        "serial": ""
      },
      "display": {
        "brightness": "not measured (macOS default, unchanged from M9)",
        "height_px": 1664,
        "kind": "computer",
        "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
        "notes": "",
        "refresh_hz": 60.0,
        "width_px": 2560
      },
      "efficiency": {
        "application_bits_per_frame": 9.945098039215686,
        "application_bps": 99.44103628852598,
        "application_bytes_per_frame": 1.2431372549019608,
        "application_payload_capacity_utilisation": 0.13093762907889303,
        "application_payload_utilisation_per_frame": 0.11301247771836008,
        "application_share_of_channel": 0.08287581699346405,
        "application_share_of_gross_payload": 0.11301247771836008,
        "application_share_of_rs_goodput": 0.1292295148797391,
        "channel_bps": 1199.8800119987757,
        "compressed": true,
        "compression_ratio": 1.0782312925170068,
        "data_bytes_per_frame": 11,
        "display_fps": 9.999000099989797,
        "dominant_loss": {
          "bps": 677.2656067726423,
          "fraction_of_channel": 0.5644444444444444,
          "stage": "unused_packet_capacity"
        },
        "expected_frames": 255,
        "file_header_bytes": 32,
        "frame_bits": 120,
        "frame_payload_utilisation": 0.7333333333333333,
        "frame_protocol_overhead": 0.26666666666666666,
        "gross_payload_bps": 879.9120087991021,
        "losses": [
          {
            "bps": 319.9680031996736,
            "fraction_of_channel": 0.2666666666666667,
            "stage": "framing_header_and_crc"
          },
          {
            "bps": 110.4203305159657,
            "fraction_of_channel": 0.09202614379084963,
            "stage": "reed_solomon_parity"
          },
          {
            "bps": 677.2656067726423,
            "fraction_of_channel": 0.5644444444444444,
            "stage": "unused_packet_capacity"
          },
          {
            "bps": -7.214964778031856,
            "fraction_of_channel": -0.0060130718954248385,
            "stage": "compression_gain"
          }
        ],
        "note": "Measured rates use the observed display period and SHA-verified payload. The per-frame utilisation denominator is 11 payload bytes/frame; the packet denominator is 2,453 RS data bytes.",
        "packet_bytes": 2453,
        "packet_duration_s": 25.50255000000052,
        "packet_fill_application": 0.1292295148797391,
        "packet_fill_file_object": 0.13289849164288625,
        "packet_fill_wire": 0.11985324092947411,
        "packet_payload_capacity_bytes": 2421,
        "packet_payload_capacity_utilisation": 0.12143742255266418,
        "payload_bits_per_frame": 88,
        "payload_bytes": 317,
        "residual_bps": 0.0,
        "rs_code_rate": 0.8745098039215686,
        "rs_goodput_bps": 769.4916782831364,
        "rs_overhead_fraction": 0.12549019607843137,
        "rs_to_application_gap_bps": 670.0506419946104,
        "rs_to_application_ratio": 7.738170347003154,
        "wire_bytes": 294,
        "wire_bytes_per_frame": 1.1529411764705881,
        "wire_payload_bps": 92.22607151049412,
        "wire_payload_utilisation_per_frame": 0.10481283422459892,
        "wire_share_of_rs_goodput": 0.11985324092947411
      },
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "factor": {
        "factors": {
          "ambient_lux": {
            "status": "UNMEASURED",
            "unit": "lux",
            "value": null
          },
          "angle_deg": {
            "status": "UNMEASURED",
            "unit": "deg",
            "value": null
          },
          "display_brightness_fraction": {
            "status": "UNMEASURED",
            "unit": "fraction of controller range (0..1); not nits",
            "value": null
          },
          "distance_mm": {
            "status": "UNMEASURED",
            "unit": "mm",
            "value": null
          },
          "lighting": {
            "status": "OPERATOR-RECORDED",
            "unit": "description",
            "value": "indoor, unchanged from M9; illuminance not measured"
          }
        },
        "unmeasured": [
          "distance_mm",
          "angle_deg",
          "ambient_lux",
          "display_brightness_fraction"
        ]
      },
      "geometry": {
        "ambient_lux": null,
        "angle_deg": null,
        "distance_mm": null,
        "hand_held": null,
        "lighting": "indoor, unchanged from M9; illuminance not measured",
        "notes": "baseline repeat of frozen M9 setup; distance, angle and ambient lux not measured"
      },
      "latency": {
        "decode_ms": {
          "max": 8.930249998229556,
          "mean": 7.513438162212705,
          "min": 2.3149170010583475,
          "n": 899.0,
          "p50": 7.632166001712903,
          "p95": 8.214724707067944,
          "std": 0.9328223798063309
        },
        "decode_samples_fps": 133.09485995762827,
        "decode_wall_s": 6.754580907829222,
        "packet_decode_ms": 2.9302920011105016,
        "reassembly_ms": 0.0297920050797984,
        "reconstruction_ms": 2.9600840061903,
        "resource": {
          "cpu_percent": 141.5539573355545,
          "cpu_s": 51.75588499999999,
          "max_rss_kb": 120736,
          "rss_kb": 120736,
          "wall_s": 36.562654958004714
        }
      },
      "media": [
        {
          "bytes": 363563987,
          "kind": "video",
          "path": "captures/originals/packet_10fps.mp4",
          "sha256": "2ee66c2b88cf266b363bae4c4a4841b6cc90168f420cfab93925a7d1114f726f"
        }
      ],
      "packets": [
        {
          "decoded": true,
          "frames_present": 246,
          "packet_id": 0,
          "stats": {
            "block_failures": [],
            "corrected_per_block": [
              9,
              9,
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
            "erasures": [
              239,
              240,
              241,
              242,
              243,
              244,
              245,
              246,
              247
            ],
            "frames_missing": 9,
            "frames_present": 246
          }
        }
      ],
      "payload": {
        "compressed": true,
        "compression_ratio": 1.0782312925170068,
        "original_bytes": 317,
        "payload_bytes": 317,
        "wire_bytes": 294
      },
      "reliability": {
        "bit_accuracy": {
          "max": 1.0,
          "mean": 1.0,
          "min": 1.0,
          "n": 246.0,
          "p50": 1.0,
          "p95": 1.0,
          "std": 0.0
        },
        "bit_accuracy_mean": 1.0,
        "cell_accuracy": {
          "max": 1.0,
          "mean": 1.0,
          "min": 1.0,
          "n": 246.0,
          "p50": 1.0,
          "p95": 1.0,
          "std": 0.0
        },
        "cell_accuracy_mean": 1.0,
        "corrected_symbols": 18,
        "erased_frames": 9,
        "expected_payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "packet_loss_rate": 0.0,
        "packets_expected": 1,
        "packets_received": 1,
        "payload_error": null,
        "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "payload_success": true,
        "rs_nsym": 32
      },
      "series": "baseline",
      "session_id": "m10-baseline-03-20261108T112602Z",
      "session_lock_sha256": "bfbef22d5ae9926d29b44aea83ef15b10fa619933125e15b9a45e77e823c15a2",
      "session_path": "/Users/arshbuttar/OPTICAL_TRANSMISSION_LAB/datasets/physical/m10-baseline-03-20261108T112602Z",
      "signal": {
        "bit_margin": {
          "max": 0.8461964849735749,
          "mean": 0.8107195132840249,
          "min": 0.7345829485995691,
          "n": 873.0,
          "p50": 0.8119469703928233,
          "p95": 0.8328060065945003,
          "std": 0.01610414378949493
        },
        "camera_luma_p50": {
          "max": 83.0,
          "mean": 66.62402669632925,
          "min": 57.0,
          "n": 899.0,
          "p50": 66.0,
          "p95": 73.0,
          "std": 3.533239748206798
        },
        "camera_luma_p99": {
          "max": 235.0,
          "mean": 230.9822024471635,
          "min": 225.0,
          "n": 899.0,
          "p50": 231.0,
          "p95": 234.0,
          "std": 1.9337512861998152
        },
        "contrast": {
          "max": 0.8666666666666667,
          "mean": 0.7422500729959797,
          "min": 0.7176470588235294,
          "n": 873.0,
          "p50": 0.7411764705882353,
          "p95": 0.7568627450980392,
          "std": 0.010232373002161349
        },
        "fiducial_confidence": {
          "max": 0.877572375305197,
          "mean": 0.8433952221823506,
          "min": 0.45961106955871356,
          "n": 873.0,
          "p50": 0.84435117173837,
          "p95": 0.8702224179696103,
          "std": 0.02902547397520679
        },
        "note": "Camera pixel statistics measure the received image, not display nits or ambient illuminance."
      },
      "status": "ok",
      "timing": {
        "camera_to_display_ratio": 3.0003000000000615,
        "capture_duration_s": 29.97086,
        "capture_fps": 30.0,
        "decode_to_capture_ratio": 4.436495331920942,
        "display_fps_manifest": 10.0,
        "display_fps_observed": 9.999000099989797,
        "display_fps_used": 9.999000099989797,
        "expected_frames": 255,
        "packet_duration_s": 25.50255000000052,
        "unique_frames": 246
      },
      "transmitter": {
        "attached_utc": "2026-11-08T11:26:02.849390+00:00",
        "fps": 10.0,
        "frame_count": 255,
        "frames_sha256": "207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348",
        "hold": false,
        "payload_name": "payload.txt",
        "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "player_manifest": "display/player_manifest.json",
        "player_manifest_sha256": "635fab9b278ae6d634297668cf616ff07aaf8373bfddf9ed7ccbcc175af176d0"
      }
    },
    {
      "capture_settings": {
        "exposure": "auto",
        "focus": "auto (Continuity Camera)",
        "format": "H.264 MP4 via AVFoundation",
        "fps": 30.0,
        "iso": "auto",
        "mode": "video",
        "notes": "Safari bounds approximately {0,28,1280,832}; player.html?fps=10; M10 brightness series 0.65",
        "resolution": "1920x1440",
        "stabilization": "not applicable (hand-held, software capture)",
        "zoom": "1x"
      },
      "capture_source": "camera",
      "captures": {
        "all_files": 1082,
        "crc_failures_after_detection": 131,
        "crc_ok": 495,
        "crc_rate": 0.45790934320074006,
        "detection_failures": 455,
        "error_counts": {
          "E_DETECT": 455
        },
        "expected_frames": 255,
        "frame_delivery_rate": 0.6862745098039216,
        "frame_loss_rate": 0.3137254901960784,
        "ground_truth_frames": 175,
        "image_files": 1081,
        "media_files": 1,
        "sample_redundancy": 6.177142857142857,
        "samples_per_frame": {
          "cv": 0.13849807273537462,
          "max": 3.0,
          "mean": 2.8285714285714287,
          "min": 1.0,
          "n": 175.0,
          "p50": 3.0,
          "std": 0.39175169145148825
        },
        "unique_frames": 175,
        "unique_images": 1081
      },
      "device": {
        "camera": "rear camera, Continuity Camera, AVFoundation index 1",
        "model": "iPhone14,2 (Continuity Camera, 'Arsh Camera')",
        "notes": "",
        "os": "iOS (Continuity Camera via macOS)",
        "serial": ""
      },
      "display": {
        "brightness": "start=0.650; end=0.650 (DisplayServicesGetBrightness fraction 0..1; nits not measured)",
        "height_px": 1664,
        "kind": "computer",
        "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
        "notes": "; brightness readback start=0.650 end=0.650",
        "refresh_hz": 60.0,
        "width_px": 2560
      },
      "efficiency": null,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "factor": {
        "factors": {
          "ambient_lux": {
            "status": "UNMEASURED",
            "unit": "lux",
            "value": null
          },
          "angle_deg": {
            "status": "UNMEASURED",
            "unit": "deg",
            "value": null
          },
          "display_brightness_fraction": {
            "status": "MEASURED (DisplayServicesGetBrightness)",
            "unit": "fraction of controller range (0..1); not nits",
            "value": 0.65
          },
          "distance_mm": {
            "status": "UNMEASURED",
            "unit": "mm",
            "value": null
          },
          "lighting": {
            "status": "OPERATOR-RECORDED",
            "unit": "description",
            "value": "indoor, unchanged from baseline; illuminance not measured"
          }
        },
        "unmeasured": [
          "distance_mm",
          "angle_deg",
          "ambient_lux"
        ]
      },
      "geometry": {
        "ambient_lux": null,
        "angle_deg": null,
        "distance_mm": null,
        "hand_held": null,
        "lighting": "indoor, unchanged from baseline; illuminance not measured",
        "notes": "brightness factor only; distance, angle and ambient lux not changed and not measured"
      },
      "latency": {
        "decode_ms": {
          "max": 9.037291994900443,
          "mean": 5.55442683820608,
          "min": 2.24491699191276,
          "n": 1081.0,
          "p50": 7.4838750006165355,
          "p95": 8.339749998413026,
          "std": 2.714510381015766
        },
        "decode_samples_fps": 180.03657787361752,
        "decode_wall_s": 6.004335412100772,
        "packet_decode_ms": 0.06033299723640084,
        "reassembly_ms": 0.000166997779160738,
        "reconstruction_ms": 0.06049999501556158,
        "resource": {
          "cpu_percent": 133.6850873115106,
          "cpu_s": 58.57487899999998,
          "max_rss_kb": 120848,
          "rss_kb": 120848,
          "wall_s": 43.81556700001238
        }
      },
      "media": [
        {
          "bytes": 558354862,
          "kind": "video",
          "path": "captures/originals/packet_10fps.mp4",
          "sha256": "36338560d96f4eab46eed4ee65a4a09ac85d37657cac17dfbe909a413c7e884b"
        }
      ],
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
                  "erasures": 80,
                  "nsym": 32
                },
                "message": "too many erasures",
                "operation": "decode"
              },
              "erasures": 80,
              "packet_id": 0
            },
            "message": "RS block could not be corrected",
            "operation": "decode_packet"
          },
          "frames_present": 175,
          "packet_id": 0
        }
      ],
      "payload": {
        "compressed": null,
        "compression_ratio": null,
        "original_bytes": 0,
        "payload_bytes": 0,
        "wire_bytes": 0
      },
      "reliability": {
        "bit_accuracy": {
          "max": 1.0,
          "mean": 1.0,
          "min": 1.0,
          "n": 175.0,
          "p50": 1.0,
          "p95": 1.0,
          "std": 0.0
        },
        "bit_accuracy_mean": 1.0,
        "cell_accuracy": {
          "max": 1.0,
          "mean": 1.0,
          "min": 1.0,
          "n": 175.0,
          "p50": 1.0,
          "p95": 1.0,
          "std": 0.0
        },
        "cell_accuracy_mean": 1.0,
        "corrected_symbols": 0,
        "erased_frames": 0,
        "expected_payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "packet_loss_rate": null,
        "packets_expected": null,
        "packets_received": 0,
        "payload_error": null,
        "payload_sha256": null,
        "payload_success": false,
        "rs_nsym": 32
      },
      "series": "brightness",
      "session_id": "m10-brightness-065-20261108T112854Z",
      "session_lock_sha256": "fec8186a37a5f9a3b043359ce9bcdf7f70e9ebe771876cc9ae73d6bab4092252",
      "session_path": "/Users/arshbuttar/OPTICAL_TRANSMISSION_LAB/datasets/physical/m10-brightness-065-20261108T112854Z",
      "signal": {
        "bit_margin": {
          "max": 0.7958451762553498,
          "mean": 0.764662945139335,
          "min": 0.7016824347080616,
          "n": 626.0,
          "p50": 0.7699354884386107,
          "p95": 0.7859015161778319,
          "std": 0.01752290106401525
        },
        "camera_luma_p50": {
          "max": 97.0,
          "mean": 89.22294172062905,
          "min": 82.0,
          "n": 1081.0,
          "p50": 88.0,
          "p95": 95.0,
          "std": 2.9329969148034296
        },
        "camera_luma_p99": {
          "max": 254.0,
          "mean": 248.12581868640126,
          "min": 228.0,
          "n": 1081.0,
          "p50": 249.0,
          "p95": 253.0,
          "std": 3.9194960290340473
        },
        "contrast": {
          "max": 0.7725490196078432,
          "mean": 0.7224215373050179,
          "min": 0.6705882352941176,
          "n": 626.0,
          "p50": 0.7254901960784313,
          "p95": 0.7647058823529411,
          "std": 0.023498492371681307
        },
        "fiducial_confidence": {
          "max": 0.9241202346041055,
          "mean": 0.8451414230633352,
          "min": 0.5940341942524554,
          "n": 626.0,
          "p50": 0.8508286408359083,
          "p95": 0.8914894474033322,
          "std": 0.040139561014882294
        },
        "note": "Camera pixel statistics measure the received image, not display nits or ambient illuminance."
      },
      "status": "ok",
      "timing": {
        "camera_to_display_ratio": 3.3057000000000154,
        "capture_duration_s": 29.984029999999997,
        "capture_fps": 30.0,
        "decode_to_capture_ratio": 6.001219262453917,
        "display_fps_manifest": 10.0,
        "display_fps_observed": 9.075233687267405,
        "display_fps_used": 9.075233687267405,
        "expected_frames": 255,
        "packet_duration_s": 28.09845000000013,
        "unique_frames": 175
      },
      "transmitter": {
        "attached_utc": "2026-11-08T11:28:54.894933+00:00",
        "fps": 10.0,
        "frame_count": 255,
        "frames_sha256": "207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348",
        "hold": false,
        "payload_name": "payload.txt",
        "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "player_manifest": "display/player_manifest.json",
        "player_manifest_sha256": "635fab9b278ae6d634297668cf616ff07aaf8373bfddf9ed7ccbcc175af176d0"
      }
    },
    {
      "capture_settings": {
        "exposure": "auto",
        "focus": "auto (Continuity Camera)",
        "format": "H.264 MP4 via AVFoundation",
        "fps": 30.0,
        "iso": "auto",
        "mode": "video",
        "notes": "Safari bounds approximately {0,28,1280,832}; player.html?fps=10; M10 brightness series 0.90",
        "resolution": "1920x1440",
        "stabilization": "not applicable (hand-held, software capture)",
        "zoom": "1x"
      },
      "capture_source": "camera",
      "captures": {
        "all_files": 887,
        "crc_failures_after_detection": 11,
        "crc_ok": 418,
        "crc_rate": 0.4717832957110609,
        "detection_failures": 457,
        "error_counts": {
          "E_DETECT": 457
        },
        "expected_frames": 255,
        "frame_delivery_rate": 0.5725490196078431,
        "frame_loss_rate": 0.4274509803921569,
        "ground_truth_frames": 146,
        "image_files": 886,
        "media_files": 1,
        "sample_redundancy": 6.068493150684931,
        "samples_per_frame": {
          "cv": 0.13941437592663605,
          "max": 3.0,
          "mean": 2.863013698630137,
          "min": 1.0,
          "n": 146.0,
          "p50": 3.0,
          "std": 0.3991452680639306
        },
        "unique_frames": 146,
        "unique_images": 886
      },
      "device": {
        "camera": "rear camera, Continuity Camera, AVFoundation index 1",
        "model": "iPhone14,2 (Continuity Camera, 'Arsh Camera')",
        "notes": "",
        "os": "iOS (Continuity Camera via macOS)",
        "serial": ""
      },
      "display": {
        "brightness": "start=0.900; end=0.900 (DisplayServicesGetBrightness fraction 0..1; nits not measured)",
        "height_px": 1664,
        "kind": "computer",
        "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
        "notes": "; brightness readback start=0.900 end=0.900",
        "refresh_hz": 60.0,
        "width_px": 2560
      },
      "efficiency": null,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "factor": {
        "factors": {
          "ambient_lux": {
            "status": "UNMEASURED",
            "unit": "lux",
            "value": null
          },
          "angle_deg": {
            "status": "UNMEASURED",
            "unit": "deg",
            "value": null
          },
          "display_brightness_fraction": {
            "status": "MEASURED (DisplayServicesGetBrightness)",
            "unit": "fraction of controller range (0..1); not nits",
            "value": 0.9
          },
          "distance_mm": {
            "status": "UNMEASURED",
            "unit": "mm",
            "value": null
          },
          "lighting": {
            "status": "OPERATOR-RECORDED",
            "unit": "description",
            "value": "indoor, unchanged from baseline; illuminance not measured"
          }
        },
        "unmeasured": [
          "distance_mm",
          "angle_deg",
          "ambient_lux"
        ]
      },
      "geometry": {
        "ambient_lux": null,
        "angle_deg": null,
        "distance_mm": null,
        "hand_held": null,
        "lighting": "indoor, unchanged from baseline; illuminance not measured",
        "notes": "brightness factor only; distance, angle and ambient lux not changed and not measured"
      },
      "latency": {
        "decode_ms": {
          "max": 9.12524999876041,
          "mean": 5.091504529012766,
          "min": 2.289875003043562,
          "n": 886.0,
          "p50": 2.8732084902003407,
          "p95": 8.425312000326812,
          "std": 2.737114395829417
        },
        "decode_samples_fps": 196.4055996222198,
        "decode_wall_s": 4.51107301270531,
        "packet_decode_ms": 0.05695900472346693,
        "reassembly_ms": 0.0002090091584250331,
        "reconstruction_ms": 0.057168013881891966,
        "resource": {
          "cpu_percent": 132.10467606744626,
          "cpu_s": 47.08077400000005,
          "max_rss_kb": 120896,
          "rss_kb": 120896,
          "wall_s": 35.638991291998536
        }
      },
      "media": [
        {
          "bytes": 473244725,
          "kind": "video",
          "path": "captures/originals/packet_10fps.mp4",
          "sha256": "7b6ada55e5ae1a9e2aff34b7b0d0bb2dd021fcf8645b50384151151153a40e3b"
        }
      ],
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
                  "erasures": 109,
                  "nsym": 32
                },
                "message": "too many erasures",
                "operation": "decode"
              },
              "erasures": 109,
              "packet_id": 0
            },
            "message": "RS block could not be corrected",
            "operation": "decode_packet"
          },
          "frames_present": 146,
          "packet_id": 0
        }
      ],
      "payload": {
        "compressed": null,
        "compression_ratio": null,
        "original_bytes": 0,
        "payload_bytes": 0,
        "wire_bytes": 0
      },
      "reliability": {
        "bit_accuracy": {
          "max": 1.0,
          "mean": 1.0,
          "min": 1.0,
          "n": 146.0,
          "p50": 1.0,
          "p95": 1.0,
          "std": 0.0
        },
        "bit_accuracy_mean": 1.0,
        "cell_accuracy": {
          "max": 1.0,
          "mean": 1.0,
          "min": 1.0,
          "n": 146.0,
          "p50": 1.0,
          "p95": 1.0,
          "std": 0.0
        },
        "cell_accuracy_mean": 1.0,
        "corrected_symbols": 0,
        "erased_frames": 0,
        "expected_payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "packet_loss_rate": null,
        "packets_expected": null,
        "packets_received": 0,
        "payload_error": null,
        "payload_sha256": null,
        "payload_success": false,
        "rs_nsym": 32
      },
      "series": "brightness",
      "session_id": "m10-brightness-090-20261108T113031Z",
      "session_lock_sha256": "d4db50fdb72c2e9ffadadacf110e8648c32daefe16d88d6ea5c8fac9ed3300f3",
      "session_path": "/Users/arshbuttar/OPTICAL_TRANSMISSION_LAB/datasets/physical/m10-brightness-090-20261108T113031Z",
      "signal": {
        "bit_margin": {
          "max": 0.7963996437453789,
          "mean": 0.7495867818201112,
          "min": 0.6559636270162587,
          "n": 429.0,
          "p50": 0.7508404344193818,
          "p95": 0.7683271370516687,
          "std": 0.01413455897461972
        },
        "camera_luma_p50": {
          "max": 106.0,
          "mean": 97.56884875846501,
          "min": 90.0,
          "n": 886.0,
          "p50": 98.0,
          "p95": 103.0,
          "std": 3.380881753121997
        },
        "camera_luma_p99": {
          "max": 253.0,
          "mean": 247.95598194130926,
          "min": 238.0,
          "n": 886.0,
          "p50": 249.0,
          "p95": 251.0,
          "std": 2.822691688774572
        },
        "contrast": {
          "max": 0.7607843137254902,
          "mean": 0.701959413135883,
          "min": 0.6549019607843137,
          "n": 429.0,
          "p50": 0.6941176470588235,
          "p95": 0.7450980392156863,
          "std": 0.024492096494915495
        },
        "fiducial_confidence": {
          "max": 0.8523357086302454,
          "mean": 0.7020664653039341,
          "min": 0.36410256410256414,
          "n": 429.0,
          "p50": 0.7205542725173211,
          "p95": 0.8363835683894164,
          "std": 0.10056649756705051
        },
        "note": "Camera pixel statistics measure the received image, not display nits or ambient illuminance."
      },
      "status": "ok",
      "timing": {
        "camera_to_display_ratio": 3.0003000000000064,
        "capture_duration_s": 29.97084,
        "capture_fps": 30.0,
        "decode_to_capture_ratio": 6.54685332074066,
        "display_fps_manifest": 10.0,
        "display_fps_observed": 9.99900009998998,
        "display_fps_used": 9.99900009998998,
        "expected_frames": 255,
        "packet_duration_s": 25.502550000000056,
        "unique_frames": 146
      },
      "transmitter": {
        "attached_utc": "2026-11-08T11:30:32.387452+00:00",
        "fps": 10.0,
        "frame_count": 255,
        "frames_sha256": "207e0af3350f5c0b30ef593c662f0449debef40a079bf37ddd2d965d95cd7348",
        "hold": false,
        "payload_name": "payload.txt",
        "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "player_manifest": "display/player_manifest.json",
        "player_manifest_sha256": "635fab9b278ae6d634297668cf616ff07aaf8373bfddf9ed7ccbcc175af176d0"
      }
    },
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
      "captures": {
        "all_files": 15,
        "crc_failures_after_detection": 0,
        "crc_ok": 1,
        "crc_rate": 1.0,
        "detection_failures": 0,
        "error_counts": {},
        "expected_frames": 255,
        "frame_delivery_rate": 0.00392156862745098,
        "frame_loss_rate": 0.996078431372549,
        "ground_truth_frames": 1,
        "image_files": 15,
        "media_files": 0,
        "sample_redundancy": 1.0,
        "samples_per_frame": {
          "cv": 0.0,
          "max": 1.0,
          "mean": 1.0,
          "min": 1.0,
          "n": 1.0,
          "p50": 1.0,
          "std": 0.0
        },
        "unique_frames": 1,
        "unique_images": 1
      },
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
      "efficiency": null,
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "factor": {
        "factors": {
          "ambient_lux": {
            "status": "UNMEASURED",
            "unit": "lux",
            "value": null
          },
          "angle_deg": {
            "status": "UNMEASURED",
            "unit": "deg",
            "value": null
          },
          "display_brightness_fraction": {
            "status": "UNMEASURED",
            "unit": "fraction of controller range (0..1); not nits",
            "value": null
          },
          "distance_mm": {
            "status": "UNMEASURED",
            "unit": "mm",
            "value": null
          },
          "lighting": {
            "status": "OPERATOR-RECORDED",
            "unit": "description",
            "value": "indoor"
          }
        },
        "unmeasured": [
          "distance_mm",
          "angle_deg",
          "ambient_lux",
          "display_brightness_fraction"
        ]
      },
      "geometry": {
        "ambient_lux": null,
        "angle_deg": null,
        "distance_mm": null,
        "hand_held": null,
        "lighting": "indoor",
        "notes": "operator hand-positioned the iPhone facing the display; distance, angle and ambient illuminance were not measured"
      },
      "latency": {
        "decode_ms": {
          "max": 8.352916003786959,
          "mean": 8.352916003786959,
          "min": 8.352916003786959,
          "n": 1.0,
          "p50": 8.352916003786959,
          "p95": 8.352916003786959,
          "std": 0.0
        },
        "decode_samples_fps": 119.71867064706868,
        "decode_wall_s": 0.008352916003786959,
        "packet_decode_ms": 0.05604198668152094,
        "reassembly_ms": 0.00012500095181167126,
        "reconstruction_ms": 0.05616698763333261,
        "resource": {
          "cpu_percent": 161.86237726962887,
          "cpu_s": 0.07933300000001964,
          "max_rss_kb": 120912,
          "rss_kb": 120912,
          "wall_s": 0.049012625007890165
        }
      },
      "media": [],
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
      "payload": {
        "compressed": null,
        "compression_ratio": null,
        "original_bytes": 0,
        "payload_bytes": 0,
        "wire_bytes": 0
      },
      "reliability": {
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
        "cell_accuracy_mean": 1.0,
        "corrected_symbols": 0,
        "erased_frames": 0,
        "expected_payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "packet_loss_rate": null,
        "packets_expected": null,
        "packets_received": 0,
        "payload_error": null,
        "payload_sha256": null,
        "payload_success": false,
        "rs_nsym": 32
      },
      "series": "m9_reference",
      "session_id": "m9-iphone14-2-20261108T103717Z",
      "session_lock_sha256": "2c952ab70aa5d5b4e3efbf50d76c3080c3f3e53284b281085eb82e4cb2c0874b",
      "session_path": "/Users/arshbuttar/OPTICAL_TRANSMISSION_LAB/datasets/physical/m9-iphone14-2-20261108T103717Z",
      "signal": {
        "bit_margin": {
          "max": 0.7611266294227188,
          "mean": 0.7611266294227188,
          "min": 0.7611266294227188,
          "n": 1.0,
          "p50": 0.7611266294227188,
          "p95": 0.7611266294227188,
          "std": 0.0
        },
        "camera_luma_p50": {
          "max": 90.0,
          "mean": 90.0,
          "min": 90.0,
          "n": 1.0,
          "p50": 90.0,
          "p95": 90.0,
          "std": 0.0
        },
        "camera_luma_p99": {
          "max": 239.0,
          "mean": 239.0,
          "min": 239.0,
          "n": 1.0,
          "p50": 239.0,
          "p95": 239.0,
          "std": 0.0
        },
        "contrast": {
          "max": 0.7019607843137254,
          "mean": 0.7019607843137254,
          "min": 0.7019607843137254,
          "n": 1.0,
          "p50": 0.7019607843137254,
          "p95": 0.7019607843137254,
          "std": 0.0
        },
        "fiducial_confidence": {
          "max": 0.8791064388961892,
          "mean": 0.8791064388961892,
          "min": 0.8791064388961892,
          "n": 1.0,
          "p50": 0.8791064388961892,
          "p95": 0.8791064388961892,
          "std": 0.0
        },
        "note": "Camera pixel statistics measure the received image, not display nits or ambient illuminance."
      },
      "status": "ok",
      "timing": {
        "camera_to_display_ratio": 3.0,
        "capture_duration_s": null,
        "capture_fps": 30.0,
        "decode_to_capture_ratio": 3.9906223549022894,
        "display_fps_manifest": 10.0,
        "display_fps_observed": null,
        "display_fps_used": 10.0,
        "expected_frames": 255,
        "packet_duration_s": 25.5,
        "unique_frames": 1
      },
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
    },
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
      "captures": {
        "all_files": 870,
        "crc_failures_after_detection": 19,
        "crc_ok": 816,
        "crc_rate": 0.9390103567318757,
        "detection_failures": 34,
        "error_counts": {
          "E_DETECT": 34
        },
        "expected_frames": 255,
        "frame_delivery_rate": 1.0,
        "frame_loss_rate": 0.0,
        "ground_truth_frames": 255,
        "image_files": 869,
        "media_files": 1,
        "sample_redundancy": 3.407843137254902,
        "samples_per_frame": {
          "cv": 0.27172740810180607,
          "max": 6.0,
          "mean": 3.2,
          "min": 1.0,
          "n": 255.0,
          "p50": 3.0,
          "std": 0.8695277059257795
        },
        "unique_frames": 255,
        "unique_images": 869
      },
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
      "efficiency": {
        "application_bits_per_frame": 9.945098039215686,
        "application_bps": 99.44103628852598,
        "application_bytes_per_frame": 1.2431372549019608,
        "application_payload_capacity_utilisation": 0.13093762907889303,
        "application_payload_utilisation_per_frame": 0.11301247771836008,
        "application_share_of_channel": 0.08287581699346405,
        "application_share_of_gross_payload": 0.11301247771836008,
        "application_share_of_rs_goodput": 0.1292295148797391,
        "channel_bps": 1199.8800119987757,
        "compressed": true,
        "compression_ratio": 1.0782312925170068,
        "data_bytes_per_frame": 11,
        "display_fps": 9.999000099989797,
        "dominant_loss": {
          "bps": 677.2656067726423,
          "fraction_of_channel": 0.5644444444444444,
          "stage": "unused_packet_capacity"
        },
        "expected_frames": 255,
        "file_header_bytes": 32,
        "frame_bits": 120,
        "frame_payload_utilisation": 0.7333333333333333,
        "frame_protocol_overhead": 0.26666666666666666,
        "gross_payload_bps": 879.9120087991021,
        "losses": [
          {
            "bps": 319.9680031996736,
            "fraction_of_channel": 0.2666666666666667,
            "stage": "framing_header_and_crc"
          },
          {
            "bps": 110.4203305159657,
            "fraction_of_channel": 0.09202614379084963,
            "stage": "reed_solomon_parity"
          },
          {
            "bps": 677.2656067726423,
            "fraction_of_channel": 0.5644444444444444,
            "stage": "unused_packet_capacity"
          },
          {
            "bps": -7.214964778031856,
            "fraction_of_channel": -0.0060130718954248385,
            "stage": "compression_gain"
          }
        ],
        "note": "Measured rates use the observed display period and SHA-verified payload. The per-frame utilisation denominator is 11 payload bytes/frame; the packet denominator is 2,453 RS data bytes.",
        "packet_bytes": 2453,
        "packet_duration_s": 25.50255000000052,
        "packet_fill_application": 0.1292295148797391,
        "packet_fill_file_object": 0.13289849164288625,
        "packet_fill_wire": 0.11985324092947411,
        "packet_payload_capacity_bytes": 2421,
        "packet_payload_capacity_utilisation": 0.12143742255266418,
        "payload_bits_per_frame": 88,
        "payload_bytes": 317,
        "residual_bps": 0.0,
        "rs_code_rate": 0.8745098039215686,
        "rs_goodput_bps": 769.4916782831364,
        "rs_overhead_fraction": 0.12549019607843137,
        "rs_to_application_gap_bps": 670.0506419946104,
        "rs_to_application_ratio": 7.738170347003154,
        "wire_bytes": 294,
        "wire_bytes_per_frame": 1.1529411764705881,
        "wire_payload_bps": 92.22607151049412,
        "wire_payload_utilisation_per_frame": 0.10481283422459892,
        "wire_share_of_rs_goodput": 0.11985324092947411
      },
      "evidence_source": "PHYSICAL / CAMERA CAPTURE",
      "factor": {
        "factors": {
          "ambient_lux": {
            "status": "UNMEASURED",
            "unit": "lux",
            "value": null
          },
          "angle_deg": {
            "status": "UNMEASURED",
            "unit": "deg",
            "value": null
          },
          "display_brightness_fraction": {
            "status": "UNMEASURED",
            "unit": "fraction of controller range (0..1); not nits",
            "value": null
          },
          "distance_mm": {
            "status": "UNMEASURED",
            "unit": "mm",
            "value": null
          },
          "lighting": {
            "status": "OPERATOR-RECORDED",
            "unit": "description",
            "value": "indoor"
          }
        },
        "unmeasured": [
          "distance_mm",
          "angle_deg",
          "ambient_lux",
          "display_brightness_fraction"
        ]
      },
      "geometry": {
        "ambient_lux": null,
        "angle_deg": null,
        "distance_mm": null,
        "hand_held": null,
        "lighting": "indoor",
        "notes": "operator hand-positioned the iPhone facing the display; distance, angle and ambient illuminance were not measured"
      },
      "latency": {
        "decode_ms": {
          "max": 8.673000003909692,
          "mean": 7.468342450894153,
          "min": 2.254207996884361,
          "n": 869.0,
          "p50": 7.648458005860448,
          "p95": 8.198533797985874,
          "std": 1.0686976999189017
        },
        "decode_samples_fps": 133.89851986236576,
        "decode_wall_s": 6.489989589827019,
        "packet_decode_ms": 2.077707991702482,
        "reassembly_ms": 0.03154099977109581,
        "reconstruction_ms": 2.109248991473578,
        "resource": {
          "cpu_percent": 137.96510822973403,
          "cpu_s": 52.29098299999998,
          "max_rss_kb": 120928,
          "rss_kb": 120928,
          "wall_s": 37.90159966600186
        }
      },
      "media": [
        {
          "bytes": 493558284,
          "kind": "video",
          "path": "captures/originals/packet_10fps.mp4",
          "sha256": "a9dceae8f863195b94bba33916447ee4605bad0cd196e703c824dec520f5873a"
        }
      ],
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
      "payload": {
        "compressed": true,
        "compression_ratio": 1.0782312925170068,
        "original_bytes": 317,
        "payload_bytes": 317,
        "wire_bytes": 294
      },
      "reliability": {
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
        "corrected_symbols": 0,
        "erased_frames": 0,
        "expected_payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "packet_loss_rate": 0.0,
        "packets_expected": 1,
        "packets_received": 1,
        "payload_error": null,
        "payload_sha256": "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d",
        "payload_success": true,
        "rs_nsym": 32
      },
      "series": "m9_reference",
      "session_id": "m9-iphone14-2-packet-20261108T104529Z",
      "session_lock_sha256": "9a6936ea85873b0827f4e995da510f092c898537b88a9f8b952d671754c36be4",
      "session_path": "/Users/arshbuttar/OPTICAL_TRANSMISSION_LAB/datasets/physical/m9-iphone14-2-packet-20261108T104529Z",
      "signal": {
        "bit_margin": {
          "max": 0.7864170900840444,
          "mean": 0.7563197151550968,
          "min": 0.6561280995785554,
          "n": 835.0,
          "p50": 0.757811864777809,
          "p95": 0.7750854291162028,
          "std": 0.014318556766813248
        },
        "camera_luma_p50": {
          "max": 107.0,
          "mean": 94.00805523590334,
          "min": 84.0,
          "n": 869.0,
          "p50": 93.0,
          "p95": 103.0,
          "std": 4.878376186354545
        },
        "camera_luma_p99": {
          "max": 254.0,
          "mean": 245.89528193325663,
          "min": 236.0,
          "n": 869.0,
          "p50": 247.0,
          "p95": 251.0,
          "std": 4.26610138275809
        },
        "contrast": {
          "max": 0.796078431372549,
          "mean": 0.7364719971821063,
          "min": 0.6941176470588235,
          "n": 835.0,
          "p50": 0.7333333333333333,
          "p95": 0.7803921568627451,
          "std": 0.020756230966366
        },
        "fiducial_confidence": {
          "max": 0.8785268785268785,
          "mean": 0.7793369939979644,
          "min": 0.5088607594936709,
          "n": 835.0,
          "p50": 0.8264580369843528,
          "p95": 0.8456195965417866,
          "std": 0.08628567964626707
        },
        "note": "Camera pixel statistics measure the received image, not display nits or ambient illuminance."
      },
      "status": "ok",
      "timing": {
        "camera_to_display_ratio": 3.0003000000000615,
        "capture_duration_s": 28.970769999999998,
        "capture_fps": 30.0,
        "decode_to_capture_ratio": 4.463283995412192,
        "display_fps_manifest": 10.0,
        "display_fps_observed": 9.999000099989797,
        "display_fps_used": 9.999000099989797,
        "expected_frames": 255,
        "packet_duration_s": 25.50255000000052,
        "unique_frames": 255
      },
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
  ],
  "status": "measured"
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

PHYSICAL / CAMERA CAPTURE. E12 analysed 7 finalized session(s); 4 delivered the complete SHA-verified payload. Baseline repeats: 3 session(s), repeatable=False (throughput CV 0.0). For the reference transfer the gross channel rate is 1199.88 bps, gross payload 879.91 bps, RS(255,223) goodput 769.49 bps and application throughput 99.44 bps. The application carries 1.243 bytes per displayed frame out of 11 (11.30%). The RS-to-application gap is 670.05 bps: framing 319.97 bps, RS parity 110.42 bps, unused packet capacity 677.27 bps, with compression recovering 7.21 bps. The dominant loss is application payload utilisation (unused packet capacity) at 677.27 bps (56.4% of the gross channel). Camera capture and decode have measured headroom; RS corrections and packet loss are zero; detection/CRC failures did not reduce unique-frame delivery. The panel ran at 9.999 fps, not 60 Hz; the 6x difference is a playback choice, and 60 fps values are projections, not measurements. Brightness was varied at measured [0.65, 0.9]; distance, angle and ambient illuminance remain UNMEASURED. All measured numbers come from preserved camera files; projections are labelled separately.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E12_channel_efficiency
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
      "notes": "Safari bounds approximately {0,28,1280,832}; player.html?fps=10; M10 baseline repeat 1",
      "resolution": "1920x1440",
      "stabilization": "not applicable (hand-held, software capture)",
      "zoom": "1x"
    },
    "display": {
      "brightness": "not measured (macOS default, unchanged from M9)",
      "height_px": 1664,
      "kind": "computer",
      "model": "Apple M5 built-in Liquid Retina (MacBook Air)",
      "notes": "",
      "refresh_hz": 60.0,
      "width_px": 2560
    },
    "model": "iPhone14,2 (Continuity Camera, 'Arsh Camera')",
    "notes": "",
    "os": "iOS (Continuity Camera via macOS)",
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
  "timestamp_utc": "2026-11-08T11:38:10.495622+00:00",
  "zstandard": "0.25.0"
}
```
