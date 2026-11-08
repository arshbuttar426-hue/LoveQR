# Architecture

The library is split into layers with one-directional dependencies. Each layer
can be tested without the layer above it, and the decoder can be tested without
a camera.

```text
                       ┌──────────────────────────────┐
                       │            otl.cli           │
                       └──────────────┬───────────────┘
                                      │
                       ┌──────────────▼───────────────┐
                       │          otl.pipeline        │
                       │  compress → packets → render │
                       │  → channel → decode → RS     │
                       └───┬────────┬────────┬────────┘
                           │        │        │
        ┌──────────────────▼─┐  ┌───▼─────┐  ┌▼─────────────────┐
        │   otl.compress     │  │ otl.tx  │  │     otl.rx       │
        │   OTL1 dictionary  │  │renderer │  │ channel/detect/  │
        └────────────────────┘  └────┬────┘  │ rolling/sync     │
                                     │       └───────┬──────────┘
                                     │               │
                              ┌──────▼───────────────▼──────┐
                              │        otl.decoder          │
                              │   spatial / temporal        │
                              └──────────────┬──────────────┘
                                             │
                              ┌──────────────▼──────────────┐
                              │   otl.protocol / otl.ecc    │
                              │ frame, packet, blink, CRC,  │
                              │ Reed–Solomon                │
                              └──────────────┬──────────────┘
                                             │
                              ┌──────────────▼──────────────┐
                              │ otl.config / types / errors │
                              │ geometry, enums, error codes│
                              └─────────────────────────────┘
```

## Data flow

### Transmit

1. **Compress** the file with `OTL1` (optional, deterministic).
2. **Build a file header** (32 bytes) and split the payload into packets.
3. **Encode each packet**: 11 RS(255,223) blocks, then byte-interleave so frame
   *n* carries byte *n* of every block.
4. **Pack each frame**: 16-bit header + 11 bytes + CRC-16 → 30 cell values.
5. **Render** each frame: cached 16-pattern tiles, four corner fiducials, solid
   outer border, supersampled and downsampled once per layout.

### Receive

1. **Detect** four corner fiducials with thresholded connected components;
   quadrants are relative to the captured image so a screen that occupies only
   part of a camera frame is still found.
2. **Rectify** the quadrilateral onto the canonical canvas with a homography.
3. **Sample** the four triangle centroids of every cell with a disk mean.
4. **Calibrate** black/white levels from fiducials and the data area.
5. **Classify** each triangle into a bit; pack into a 4-bit cell value.
6. **Unpack** the frame and check CRC-16.
7. **De-interleave** the 11 bytes of accepted frames and RS-decode each block
   with missing frames as erasures.
8. **Reassemble** packets, verify CRC-32, decompress, compare with the input.

## Interfaces

The public contract is intentionally small and typed:

| Function | Input | Output | Notes |
| --- | --- | --- | --- |
| `pack_frame(header, data, cfg)` | `FrameHeader`, 11 bytes | 30 cell values | Raises `FrameFormatError` on bad length/value. |
| `unpack_frame(cells, cfg)` | 30 cells | `DecodedFrame` | Bad CRC is reported, not raised. |
| `encode_packet(id, chunk, header, nsym)` | bytes | `Packet` | 255 frames of 11 bytes. |
| `decode_packet(id, frames, nsym)` | frame index → 11 bytes | `DecodedPacket` | Missing frames are erasures. |
| `compress(data, cfg)` / `decompress(data)` | bytes | bytes + `CompressionStats` | Exact roundtrip. |
| `render_frame(cells, layout, screen)` | 30 cells | `uint8` image | Deterministic. |
| `build_player(frames, out, cfg)` | PNG paths | HTML + `player_manifest.json` | Deterministic TX interface; hold/playback. |
| `capture_still(device, out, ...)` | AVFoundation index | preserved frames + log | RX interface; keeps every raw frame. |
| `ingest_image(session, path, ...)` | photo path | `CaptureFile` | Copies original verbatim; derives PNG only if unreadable. |
| `new_session(root, id, ...)` | metadata | session directory | Refuses an existing directory. |
| `validate_session` / `finalize_session` | session path | problems / lock | Finalization is the physical-evidence gate. |
| `apply_channel(image, cfg, seed)` | image | `uint8` image | Simulated only. |
| `decode_image(image, layout, receiver, protocol)` | image | `SpatialDecode` | Works on prerecorded PNG/JPEG. |
| `simulate_transfer(data, name, cfg, ...)` | bytes | `PipelineResult` | Never hides a failed packet. |

All public errors derive from `otl.errors.OTLError` and carry a stable
machine-readable `code` (`E_CONFIG`, `E_PROTOCOL`, `E_FRAME_FORMAT`, `E_CRC`,
`E_DETECT`, `E_SYNC`, `E_DECODE`, `E_ECC`, `E_COMPRESSION`, `E_CHANNEL`,
`E_RECONSTRUCT`, `E_MEASUREMENT`, `E_CAPTURE`, `E_UNSUPPORTED`). `to_dict()`
includes the component, operation and structured context.

## Geometry

`otl/config.py` is the single source of truth for geometry:

- `ScreenConfig` (1080 × 1350, 6 × 5 cells, 8 px gaps, 90 px margin,
  48 px fiducials, 10 px border, 4× supersampling).
- `compute_layout()` derives cell size, origin, data area and fiducial rects.
- `Layout.triangle_polygon()` and `Layout.triangle_centroid()` are used by the
  renderer and the sampler, so transmitter and receiver cannot disagree about
  where a triangle is.
- `ProtocolConfig` validates the 120-bit arithmetic at construction time.
- `CameraConfig` exposes `symbol_period_us` and `readout_us` for the temporal
  model.

## Determinism

- No global RNG. Every stochastic stage takes an explicit seed
  (`apply_channel(seed=...)`, `simulate_transfer(seed=...)`, experiment RNG).
- `FrameRenderer` pre-renders tiles once per layout; repeated calls produce
  byte-identical images (E10 checks hashes).
- `OTL1` is a greedy, deterministic encoder with a fixed match window.
- Reed–Solomon is pure Python over GF(256) with a fixed primitive polynomial
  (0x11D), so results do not depend on a C library version.
- `decode_image` has no camera object and no hidden state; decoding the same
  PNG twice yields the same cell sequence (E10).

## Configuration and serialisation

`ExperimentConfig` is a frozen dataclass tree (`ScreenConfig`, `ProtocolConfig`,
`ChannelConfig`, `CameraConfig`, `ReceiverConfig`, `ECCConfig`,
`CompressionConfig`, seed, quick). `config_to_dict()` / `load_config()` provide
JSON roundtrips without an extra dependency. Every experiment manifest embeds
the default config and the trial configs.

## Error handling

- Expected failures raise an `OTLError` subclass with a stable code.
- The decoder reports a bad CRC in `DecodedFrame.crc_ok` instead of raising, so
  the caller can count frame errors.
- The packet layer converts an uncorrectable RS block into
  `ReconstructionError` with the block index, erasure count and cause.
- The CLI prints structured JSON to stderr and exits 2 for expected OTL errors,
  3 for a decode/transfer that ran but failed verification.

## Testing strategy

| Layer | Test file | What it proves |
| --- | --- | --- |
| Patterns | `test_patterns.py` | Alphabet size, distance, complement, parity control sets |
| CRC | `test_crc.py` | Check value `123456789` → `0x29B1`, CRC-32 reference |
| RS | `test_rs.py` | Errors, erasures, mixed, over-capacity rejection |
| Compression | `test_compression.py` | Exact roundtrip on empty/repeat/sequence/random/inverted/text |
| Frame | `test_frame.py` | Bit layout, CRC, invalid lengths |
| Packet | `test_packet.py` | Header, capacity, interleave, erasure recovery |
| Blink | `test_blink.py` | Barker sidelobes, cross-correlation, each ID |
| Renderer | `test_renderer.py` | Determinism, fiducials, golden hash |
| Channel/detect | `test_channel.py`, `test_detect.py` | Degradations, fiducials, sampling, all-black/all-white |
| Temporal | `test_temporal.py` | Rolling-shutter word recovery, exposure limit |
| Pipeline | `test_pipeline.py` | Clean/degraded/multi-packet/drop/over-capacity |
| CLI | `test_cli.py` | JSON output, exit codes, selftest |
| Regression | `test_golden.py` | Frozen hashes for renderer and corpus |

Tests run with `python3 -m pytest`. The suite is deterministic; the only
host-dependent values are timing and RSS, which are not asserted for exact
values.

## Extension points

- **New alphabet**: add a `PatternSet` and implement `pattern_values` /
  `encode_symbol` / `decode_symbol`; `alphabet_manifest` reports distances.
- **New channel degradation**: add a field to `ChannelConfig` and a step in
  `apply_channel`; record it in `channel_manifest`.
- **New compression opcode**: extend the versioned `OTL1` table; bump
  `VERSION` if the bitstream changes.
- **New experiment**: implement `run(ctx)` and add an `ExperimentSpec` to
  `experiments/registry.py`; the harness handles run directories, raw JSONL,
  CSV, reports and the results index.
- **Physical capture**: load with `otl.rx.channel.load_capture(path,
  device=...)` and call `decode_image` directly; no code changes are required.
