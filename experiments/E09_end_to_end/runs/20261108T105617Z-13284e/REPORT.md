# E09_end_to_end — End-to-end simulated transfer

- Run: `20261108T105617Z-13284e`
- Classification: **OBSERVED (SIMULATED channel) + THEORETICAL (projected screen time)**
- Evidence source: **SIMULATED / SOFTWARE**
- Device: none (no physical capture)
- Trials: 64
- Wall time: 575.62 s
- Quick mode: False

## Hypothesis

The full pipeline (compression, packetisation, RS, rendering, simulated channel, spatial decode, reassembly) recovers files under clean/mild/harsh channels and moderate frame loss, with a measurable failure limit on a deliberately brutal stress channel.

## Controlled variables

- protocol
- layout
- renderer
- decoder
- RS settings
- seed

## Independent variables

- payload type/size
- channel severity
- frame-drop probability

## Dependent variables

- transfer success
- compression ratio
- frames decoded/dropped
- BER
- simulated throughput
- projected screen throughput
- decode latency
- reconstruction time
- CPU/memory

## Procedure

1. Generate text and seeded-random payloads at several sizes and hash each one.
2. Record the payload generator, every seed and every SHA-256 in the run manifest.
3. Run the complete simulate_transfer pipeline with clean/mild/harsh/brutal channels and 0/3% frame loss.
4. Record success, per-packet RS statistics, errors, throughput, latency, reconstruction time and resource use for every trial, including failures.
5. Re-derive each payload hash and fingerprint the payload set and the outcome set.
6. Separate simulated wall-clock throughput, projected 60 fps screen throughput, decode latency and reconstruction time.

## Experiment metadata

```json
{
  "channels": {
    "brutal": {
      "ambient": 60.0,
      "blur_sigma": 3.5,
      "brightness": 0.5,
      "gamma": 1.6,
      "jpeg_quality": 35,
      "motion_angle_deg": 0.0,
      "motion_blur_px": 0,
      "noise_sigma": 20.0,
      "perspective": 0.08,
      "seed": 0,
      "vignette": 0.6
    },
    "clean": {
      "ambient": 0.0,
      "blur_sigma": 0.0,
      "brightness": 1.0,
      "gamma": 1.0,
      "jpeg_quality": 100,
      "motion_angle_deg": 0.0,
      "motion_blur_px": 0,
      "noise_sigma": 0.0,
      "perspective": 0.0,
      "seed": 0,
      "vignette": 0.0
    },
    "harsh": {
      "ambient": 25.0,
      "blur_sigma": 1.4,
      "brightness": 0.82,
      "gamma": 1.15,
      "jpeg_quality": 80,
      "motion_angle_deg": 0.0,
      "motion_blur_px": 0,
      "noise_sigma": 4.0,
      "perspective": 0.03,
      "seed": 0,
      "vignette": 0.25
    },
    "mild": {
      "ambient": 12.0,
      "blur_sigma": 0.8,
      "brightness": 0.92,
      "gamma": 1.05,
      "jpeg_quality": 92,
      "motion_angle_deg": 0.0,
      "motion_blur_px": 0,
      "noise_sigma": 2.0,
      "perspective": 0.01,
      "seed": 0,
      "vignette": 0.12
    }
  },
  "evidence_source": "SIMULATED / SOFTWARE",
  "matrix": {
    "channels": [
      "clean",
      "mild",
      "harsh",
      "brutal"
    ],
    "drop_probabilities": [
      0.0,
      0.03
    ],
    "kinds": [
      "text",
      "random"
    ],
    "sizes": [
      100,
      1000,
      2400,
      6000
    ],
    "trials": 64
  },
  "payload_generator": {
    "random": {
      "bit_generator": "PCG64 (numpy default)",
      "draw": "integers(0, 256, size=payload_bytes, dtype=uint8).tobytes()",
      "factory": "numpy.random.default_rng",
      "seed_rule": "PAYLOAD_SEED_BASE + payload_bytes (PAYLOAD_SEED_BASE=7000)"
    },
    "text": {
      "method": "UTF-8 template repeated then truncated to payload_bytes",
      "seed": null,
      "template_bytes": 120,
      "template_sha256": "09ebc3935e427332dd0a4e38a0b3d53d7109f1c8bc62a48296fd2f2467239119"
    }
  },
  "payload_manifest_sha256": "9cf02deb1f14f95ed3521b5754216e45526f910a61b3e47704817287dd2e6e39",
  "payloads": [
    {
      "kind": "text",
      "payload_bytes": 100,
      "seed": null,
      "sha256": "982e9a33c8a4f51171b39d2fbd21f1e16bf0416b1a241f114980717670c5a715"
    },
    {
      "kind": "text",
      "payload_bytes": 1000,
      "seed": null,
      "sha256": "e5a0710f3c93b190a140e484194d2110861c45016ffb786f631f6d07cab68b0a"
    },
    {
      "kind": "text",
      "payload_bytes": 2400,
      "seed": null,
      "sha256": "947ac3800699cc6c46560d2ec64df7fbca169b55b16f3270a64f8f7b659bdf23"
    },
    {
      "kind": "text",
      "payload_bytes": 6000,
      "seed": null,
      "sha256": "174c81fb4fd750fccad135a0486648974c69b2cdabe79db6ed530739c50f51d5"
    },
    {
      "kind": "random",
      "payload_bytes": 100,
      "seed": 7100,
      "sha256": "9c32e072fc4ae9f6a38a6795f08ea6e8ebd3a737550bcab2a61be7eab8e2bfdf"
    },
    {
      "kind": "random",
      "payload_bytes": 1000,
      "seed": 8000,
      "sha256": "e2300ba37000dd5cffec239aca337104a616edc5014761b1606af3f4a52ae132"
    },
    {
      "kind": "random",
      "payload_bytes": 2400,
      "seed": 9400,
      "sha256": "41f6d6b9a9bf68051b4681abd607608f90e8410e153c6cfe71b379222569be98"
    },
    {
      "kind": "random",
      "payload_bytes": 6000,
      "seed": 13000,
      "sha256": "a8d61b53c8b26efaa90daa907b119c67f2a0153b74e7f89d2b4927d81c6664ba"
    }
  ],
  "physical_device": null,
  "pipeline_seed_rule": "9000 + payload_bytes + int(drop_probability * 1000)",
  "simulation_only": true
}
```

## Processed results

```json
{
  "evidence_source": "SIMULATED / SOFTWARE",
  "failures": {
    "by_channel": {
      "brutal": {
        "failures": 16,
        "trials": 16
      },
      "clean": {
        "failures": 0,
        "trials": 16
      },
      "harsh": {
        "failures": 0,
        "trials": 16
      },
      "mild": {
        "failures": 0,
        "trials": 16
      }
    },
    "by_stage": {
      "frame_crc": 16,
      "packet": 16,
      "reassembly": 16
    },
    "count": 16,
    "rate": 0.25,
    "trials": [
      {
        "config": {
          "channel": "brutal",
          "compression": true,
          "drop_probability": 0.0,
          "payload_bytes": 100,
          "payload_kind": "text",
          "payload_seed": null,
          "pipeline_seed": 9100
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": true,
          "drop_probability": 0.03,
          "payload_bytes": 100,
          "payload_kind": "text",
          "payload_seed": null,
          "pipeline_seed": 9130
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": true,
          "drop_probability": 0.0,
          "payload_bytes": 1000,
          "payload_kind": "text",
          "payload_seed": null,
          "pipeline_seed": 10000
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": true,
          "drop_probability": 0.03,
          "payload_bytes": 1000,
          "payload_kind": "text",
          "payload_seed": null,
          "pipeline_seed": 10030
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": true,
          "drop_probability": 0.0,
          "payload_bytes": 2400,
          "payload_kind": "text",
          "payload_seed": null,
          "pipeline_seed": 11400
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 1,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": true,
          "drop_probability": 0.03,
          "payload_bytes": 2400,
          "payload_kind": "text",
          "payload_seed": null,
          "pipeline_seed": 11430
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": true,
          "drop_probability": 0.0,
          "payload_bytes": 6000,
          "payload_kind": "text",
          "payload_seed": null,
          "pipeline_seed": 15000
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": true,
          "drop_probability": 0.03,
          "payload_bytes": 6000,
          "payload_kind": "text",
          "payload_seed": null,
          "pipeline_seed": 15030
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": false,
          "drop_probability": 0.0,
          "payload_bytes": 100,
          "payload_kind": "random",
          "payload_seed": 7100,
          "pipeline_seed": 9100
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": false,
          "drop_probability": 0.03,
          "payload_bytes": 100,
          "payload_kind": "random",
          "payload_seed": 7100,
          "pipeline_seed": 9130
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": false,
          "drop_probability": 0.0,
          "payload_bytes": 1000,
          "payload_kind": "random",
          "payload_seed": 8000,
          "pipeline_seed": 10000
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": false,
          "drop_probability": 0.03,
          "payload_bytes": 1000,
          "payload_kind": "random",
          "payload_seed": 8000,
          "pipeline_seed": 10030
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": false,
          "drop_probability": 0.0,
          "payload_bytes": 2400,
          "payload_kind": "random",
          "payload_seed": 9400,
          "pipeline_seed": 11400
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 1,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": false,
          "drop_probability": 0.03,
          "payload_bytes": 2400,
          "payload_kind": "random",
          "payload_seed": 9400,
          "pipeline_seed": 11430
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": false,
          "drop_probability": 0.0,
          "payload_bytes": 6000,
          "payload_kind": "random",
          "payload_seed": 13000,
          "pipeline_seed": 15000
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 9,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      },
      {
        "config": {
          "channel": "brutal",
          "compression": false,
          "drop_probability": 0.03,
          "payload_bytes": 6000,
          "payload_kind": "random",
          "payload_seed": 13000,
          "pipeline_seed": 15030
        },
        "error_stages": [
          "frame_crc",
          "packet",
          "reassembly"
        ],
        "first_error": {
          "crc_ok": false,
          "decoded_frame_index": 0,
          "decoded_packet_id": 1,
          "frame_index": 0,
          "packet_id": 0,
          "stage": "frame_crc"
        }
      }
    ]
  },
  "latency": {
    "basis": "all trials; per-decoded-frame spatial decode time and total pipeline time",
    "spatial_decode_ms_per_frame": {
      "max": 14.411139892201806,
      "mean": 8.567711273391023,
      "min": 5.769492114332559,
      "n": 64.0,
      "p50": 7.848029288196251,
      "p95": 13.556246818434188,
      "std": 2.472075872791547
    },
    "total_pipeline_ms": {
      "max": 34514.11116699455,
      "mean": 8981.745121062204,
      "min": 1757.1595000044908,
      "n": 64.0,
      "p50": 7999.2134790009,
      "p95": 25260.227923300405,
      "std": 6940.416998046874
    }
  },
  "max_payload_decoded": 6000,
  "note": "SIMULATED / SOFTWARE. Simulated wall time is Python execution time; projected screen time = frames / 60 fps. Neither is a physical camera measurement. All trials, including failures, are retained in raw/trials.jsonl.",
  "reconstruction_time": {
    "basis": "all trials; reassembly + decompression, and Reed-Solomon ECC",
    "compression_ms": {
      "max": 4.942999992636032,
      "mean": 0.9133131400176353,
      "min": 0.0005830079317092896,
      "n": 64.0,
      "p50": 0.07264650048455223,
      "p95": 4.795118638867279,
      "std": 1.5581141079313363
    },
    "ecc_ms": {
      "max": 22.14424902922474,
      "mean": 3.364298828500978,
      "min": 0.05066599987912923,
      "n": 64.0,
      "p50": 2.1911454969085753,
      "p95": 10.286201052076649,
      "std": 4.765428477396884
    },
    "reassembly_plus_decompress_ms": {
      "max": 0.17250000382773578,
      "mean": 0.030227952947825543,
      "min": 0.0022909953258931637,
      "n": 64.0,
      "p50": 0.006770489562768489,
      "p95": 0.16898114918149074,
      "std": 0.04878627046890065
    }
  },
  "resource": {
    "cpu_percent": {
      "max": 274.5016201244262,
      "mean": 181.30250742372695,
      "min": 141.0208418776336,
      "n": 64.0,
      "p50": 156.38787853043635,
      "p95": 273.20457287965337,
      "std": 50.47269197107427
    },
    "peak_rss_kb_max": 183552,
    "rss_kb_max": 183552
  },
  "sha256_verification": {
    "mismatches": [],
    "outcome_sha256": "c4d98b2becddaaeeaccba18b6748afd69ed79e3926c704a39572a4f31983c075",
    "payload_manifest_sha256": "9cf02deb1f14f95ed3521b5754216e45526f910a61b3e47704817287dd2e6e39",
    "recomputed_from_generator": 64,
    "trials_hashed": 64,
    "verified_against_manifest": 64
  },
  "simulation_only": true,
  "success_rate": 0.75,
  "successes": {
    "by_channel": {
      "brutal": {
        "failures": 16,
        "successes": 0,
        "trials": 16
      },
      "clean": {
        "failures": 0,
        "successes": 16,
        "trials": 16
      },
      "harsh": {
        "failures": 0,
        "successes": 16,
        "trials": 16
      },
      "mild": {
        "failures": 0,
        "successes": 16,
        "trials": 16
      }
    },
    "by_kind": {
      "random": {
        "failures": 8,
        "successes": 24,
        "trials": 32
      },
      "text": {
        "failures": 8,
        "successes": 24,
        "trials": 32
      }
    },
    "by_size": {
      "100": {
        "failures": 4,
        "successes": 12,
        "trials": 16
      },
      "1000": {
        "failures": 4,
        "successes": 12,
        "trials": 16
      },
      "2400": {
        "failures": 4,
        "successes": 12,
        "trials": 16
      },
      "6000": {
        "failures": 4,
        "successes": 12,
        "trials": 16
      }
    },
    "count": 48,
    "rate": 0.75
  },
  "throughput": {
    "basis": "successful trials only; simulated execution and projected 60 fps screen time",
    "decode_fps_simulated": {
      "max": 145.12057670310992,
      "mean": 67.20091238507848,
      "min": 29.466502189012072,
      "n": 48.0,
      "p50": 32.38693294523141,
      "p95": 143.74524963420063,
      "std": 50.182359802566836
    },
    "projected_net_bps_at_60fps": {
      "max": 11294.117647058823,
      "mean": 3529.4117647058824,
      "min": 188.23529411764707,
      "n": 48.0,
      "p50": 2823.529411764706,
      "p95": 11294.117647058823,
      "std": 3355.066405935253
    },
    "projected_screen_s_at_60fps": {
      "max": 12.75,
      "mean": 5.3125,
      "min": 4.25,
      "n": 48.0,
      "p50": 4.25,
      "p95": 12.75,
      "std": 2.8111107680061274
    },
    "simulated_gross_bps": {
      "max": 10059.963101710491,
      "mean": 1582.0831454792167,
      "min": 98.0659354449764,
      "n": 48.0,
      "p50": 556.0441858484053,
      "p95": 8020.79329612905,
      "std": 2483.828113738665
    },
    "simulated_net_bps": {
      "max": 27117.25883540621,
      "mean": 3953.5195456334022,
      "min": 97.94006288306366,
      "n": 48.0,
      "p50": 2167.7110898940687,
      "p95": 10680.629127873824,
      "std": 5643.483486769513
    }
  },
  "trials": 64
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

48 of 64 simulated transfers succeeded (75.0%); 16 failed. Successes by channel: clean 16/16, mild 16/16, harsh 16/16, brutal 0/16. Failures: brutal 16/16; stages frame_crc×16, packet×16, reassembly×16. All 64 payload SHA-256 values were checked against the pre-run manifest (64/64 matched) and re-derived from the recorded generator specification (64/64 identical); payload manifest 9cf02deb1f14…, outcome fingerprint c4d98b2becdd…. Throughput (successful trials only): simulated net 3953.5 bps and projected 60 fps net 3529.4 bps. Latency: spatial decode 8.57 ms per decoded frame, total pipeline 8982 ms per trial. Reconstruction: reassembly+decompress 0.03 ms, RS ECC 3.36 ms per trial. Resources: 181% CPU of one core, peak RSS 183552 KiB. These are SIMULATED / SOFTWARE results, not a physical optical transmission benchmark.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E09_end_to_end
```

The run directory is immutable; re-running creates a new run id.

## Environment

```json
{
  "cpu_count": 10,
  "device": null,
  "evidence_source": "SIMULATED / SOFTWARE",
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
  "timestamp_utc": "2026-11-08T11:05:52.631980+00:00",
  "zstandard": "0.25.0"
}
```
