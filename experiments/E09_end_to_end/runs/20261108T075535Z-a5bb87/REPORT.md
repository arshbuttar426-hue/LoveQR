# E09_end_to_end — End-to-end simulated transfer

- Run: `20261108T075535Z-a5bb87`
- Classification: **OBSERVED (SIMULATED channel) + THEORETICAL (projected screen time)**
- Evidence source: **SIMULATED / SOFTWARE** (no physical camera)
- Trials: 8
- Wall time: 38.74 s
- Quick mode: True

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
      "mild"
    ],
    "drop_probabilities": [
      0.0
    ],
    "kinds": [
      "text",
      "random"
    ],
    "sizes": [
      100,
      1000
    ],
    "trials": 8
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
  "payload_manifest_sha256": "ebdfb818b85b0346cb012fdee80ad7fd2befbfa1bf5e1d4f78f10d0ea7318844",
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
      "clean": {
        "failures": 0,
        "trials": 4
      },
      "mild": {
        "failures": 0,
        "trials": 4
      }
    },
    "by_stage": {},
    "count": 0,
    "rate": 0.0,
    "trials": []
  },
  "latency": {
    "basis": "all trials; per-decoded-frame spatial decode time and total pipeline time",
    "spatial_decode_ms_per_frame": {
      "max": 7.828294960428121,
      "mean": 6.701608672037587,
      "min": 5.646997509528791,
      "n": 8.0,
      "p50": 6.670222780724312,
      "p95": 7.801325106585293,
      "std": 1.0155006824234134
    },
    "total_pipeline_ms": {
      "max": 7890.549374991679,
      "mean": 4824.791932496737,
      "min": 1777.4911250016885,
      "n": 8.0,
      "p50": 4820.143541495781,
      "p95": 7883.263148143305,
      "std": 3036.5103438377614
    }
  },
  "max_payload_decoded": 1000,
  "note": "SIMULATED / SOFTWARE. Simulated wall time is Python execution time; projected screen time = frames / 60 fps. Neither is a physical camera measurement. All trials, including failures, are retained in raw/trials.jsonl.",
  "reconstruction_time": {
    "basis": "all trials; reassembly + decompression, and Reed-Solomon ECC",
    "compression_ms": {
      "max": 0.7218329992610961,
      "mean": 0.22463537607109174,
      "min": 0.00029199873097240925,
      "n": 8.0,
      "p50": 0.09262499224860221,
      "p95": 0.7119745518139098,
      "std": 0.2893234934359319
    },
    "ecc_ms": {
      "max": 2.558958003646694,
      "mean": 2.0575260023179,
      "min": 1.8286249978700653,
      "n": 8.0,
      "p50": 1.910937498905696,
      "p95": 2.546328953030752,
      "std": 0.2808184767181044
    },
    "reassembly_plus_decompress_ms": {
      "max": 0.05358399357646704,
      "mean": 0.01933862040459644,
      "min": 0.004749992513097823,
      "n": 8.0,
      "p50": 0.010478994227014482,
      "p95": 0.04970459704054519,
      "std": 0.017900157776119002
    }
  },
  "resource": {
    "cpu_percent": {
      "max": 280.50150173744663,
      "mean": 218.08758733587894,
      "min": 158.6151062101294,
      "n": 8.0,
      "p50": 217.29600562506715,
      "p95": 279.22881334913643,
      "std": 59.304016463644636
    },
    "peak_rss_kb_max": 179808,
    "rss_kb_max": 179808
  },
  "sha256_verification": {
    "mismatches": [],
    "outcome_sha256": "48e1c9296dfb5457102208476a52f82e130bce8cba092d0e7b4aca6aa1abfa3e",
    "payload_manifest_sha256": "ebdfb818b85b0346cb012fdee80ad7fd2befbfa1bf5e1d4f78f10d0ea7318844",
    "recomputed_from_generator": 8,
    "trials_hashed": 8,
    "verified_against_manifest": 8
  },
  "simulation_only": true,
  "success_rate": 1.0,
  "successes": {
    "by_channel": {
      "clean": {
        "failures": 0,
        "successes": 4,
        "trials": 4
      },
      "mild": {
        "failures": 0,
        "successes": 4,
        "trials": 4
      }
    },
    "by_kind": {
      "random": {
        "failures": 0,
        "successes": 4,
        "trials": 4
      },
      "text": {
        "failures": 0,
        "successes": 4,
        "trials": 4
      }
    },
    "by_size": {
      "100": {
        "failures": 0,
        "successes": 4,
        "trials": 4
      },
      "1000": {
        "failures": 0,
        "successes": 4,
        "trials": 4
      }
    },
    "count": 8,
    "rate": 1.0
  },
  "throughput": {
    "basis": "successful trials only; simulated execution and projected 60 fps screen time",
    "decode_fps_simulated": {
      "max": 143.4606319059724,
      "mean": 87.51683892497707,
      "min": 32.317141415805274,
      "n": 8.0,
      "p50": 86.92999961331647,
      "p95": 143.2699350148835,
      "std": 55.081921442052156
    },
    "projected_net_bps_at_60fps": {
      "max": 1882.3529411764705,
      "mean": 1035.2941176470588,
      "min": 188.23529411764707,
      "n": 8.0,
      "p50": 1035.2941176470588,
      "p95": 1882.3529411764705,
      "std": 847.0588235294117
    },
    "projected_screen_s_at_60fps": {
      "max": 4.25,
      "mean": 4.25,
      "min": 4.25,
      "n": 8.0,
      "p50": 4.25,
      "p95": 4.25,
      "std": 0.0
    },
    "simulated_gross_bps": {
      "max": 4476.548028552389,
      "mean": 932.6250631332391,
      "min": 101.65530951867004,
      "n": 8.0,
      "p50": 473.8778851023056,
      "p95": 3267.088868791585,
      "std": 1371.3109104532064
    },
    "simulated_net_bps": {
      "max": 4476.548028552389,
      "mean": 1506.463306709418,
      "min": 101.38711032409498,
      "n": 8.0,
      "p50": 734.660707091785,
      "p95": 4461.474540226802,
      "std": 1733.6809757073574
    }
  },
  "trials": 8
}
```

Raw measurements: `raw/trials.jsonl` (one JSON object per trial).
Tabular metrics: `processed/summary.csv`.

## Failures

- None recorded.

## Conclusion

8 of 8 simulated transfers succeeded (100.0%); 0 failed. Successes by channel: clean 4/4, mild 4/4. No failures occurred inside the tested matrix. All 8 payload SHA-256 values were checked against the pre-run manifest (8/8 matched) and re-derived from the recorded generator specification (8/8 identical); payload manifest ebdfb818b85b…, outcome fingerprint 48e1c9296dfb…. Throughput (successful trials only): simulated net 1506.5 bps and projected 60 fps net 1035.3 bps. Latency: spatial decode 6.70 ms per decoded frame, total pipeline 4825 ms per trial. Reconstruction: reassembly+decompress 0.02 ms, RS ECC 2.06 ms per trial. Resources: 218% CPU of one core, peak RSS 179808 KiB. These are SIMULATED / SOFTWARE results, not a physical optical transmission benchmark.

## Reproduction

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 -m experiments.run_all --only E09_end_to_end --quick
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
  "timestamp_utc": "2026-11-08T07:56:13.771781+00:00",
  "zstandard": "0.25.0"
}
```
