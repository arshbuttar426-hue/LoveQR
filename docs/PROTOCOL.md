# Protocol specification

This is the normative description of the bitstream implemented by `otl`. All
arithmetic is exact; the constants are validated in `ProtocolConfig`.

## 1. Cell alphabet (FULL16)

A cell is a square split into four triangles by its diagonals:

```text
        top
      /     \
 left |  +  | right
      \     /
       bottom
```

Bit order is **top (bit 3), right (bit 2), bottom (bit 1), left (bit 0)**;
`1` means white, `0` means black. A cell value is a 4-bit integer 0…15.

- 16 patterns per cell = 4 bits.
- Minimum Hamming distance between patterns = 1 (a single triangle flip changes
  the value). The alphabet provides **no** intra-cell error correction.
- `PARITY8` (even parity, 8 patterns, 3 bits) and `BALANCED6` (exactly two white
  triangles, 6 patterns) exist as control alphabets in `otl.codec.patterns`;
  they are not used by the main protocol.

## 2. Spatial frame

6 columns × 5 rows = **30 cells** = **120 raw bits**.

| Field | Bits | Encoding |
| --- | ---: | --- |
| Header | 16 | 4-bit packet id (MSB) + 12-bit frame index (LSB) |
| Data | 88 | 11 bytes |
| CRC | 16 | CRC-16/CCITT-FALSE over the 13 header+data bytes |
| **Total** | **120** | 30 cells |

- The 15 bytes are emitted big-endian: header, data, CRC.
- Each byte becomes two consecutive cells: high nibble first, then low nibble.
- Cells are ordered row-major: row 0 left→right, then row 1, … row 4.

### CRC-16/CCITT-FALSE

```text
poly   = 0x1021
init   = 0xFFFF
refin  = false
refout = false
xorout = 0x0000
check  = crc16_ccitt(b"123456789") = 0x29B1
```

The CRC covers the 2 header bytes and the 11 data bytes. A bad CRC is reported
as `DecodedFrame.crc_ok = false`; the frame is not silently accepted.

## 3. File header (32 bytes, packet 0 only)

Big-endian struct `>2sBBBBIIIB13s`:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 2 | magic `b"OT"` |
| 2 | 1 | version = 1 |
| 3 | 1 | flags: bit 0 = compressed |
| 4 | 1 | packet id (must be 0) |
| 5 | 1 | total packets (1…16) |
| 6 | 4 | original length (uint32) |
| 10 | 4 | payload length after compression (uint32) |
| 14 | 4 | CRC-32 of the payload (uint32, zlib polynomial) |
| 18 | 1 | name length (0…13) |
| 19 | 13 | UTF-8 name, NUL-padded |

The 13-byte name field is a hard limit. `FileHeader` raises `E_PROTOCOL` for a
longer name. The experiments use short names (`t100.bin`, `determ.bin`) for this
reason.

## 4. Packet layer

A packet is exactly **255 spatial frames**.

```text
packet payload region = 11 blocks × 223 data bytes = 2453 bytes
each block             = RS(255, 223), nsym = 32
frames                 = 255, frame n carries byte n of every block
```

- Block *b* is `region[b*223 : (b+1)*223]`, encoded to 255 bytes
  (223 data + 32 parity).
- Frame *n* is the 11 bytes `[block0[n], block1[n], …, block10[n]]`.
- Losing frame *n* removes byte *n* from every block: **one erasure per block**.
- RS capacity per block: `2·e + r ≤ 32`, where `e` is unknown byte errors and
  `r` is erasures. With interleaving, `r` equals the number of lost frames, so a
  packet survives up to **32 lost frames** (or 16 unknown errors per block, or a
  mix).
- A frame whose CRC fails is not inserted into the packet; its index becomes an
  erasure.

### Packet 0 capacity

Packet 0 starts with the 32-byte file header:

```text
payload_0 = 2453 − 32 = 2421 bytes
payload_n = 2453 bytes for n > 0
max_payload = 2421 + 15 × 2453 = 39,216 bytes
```

The 4-bit packet id caps a transfer at **16 packets**. This is a protocol
property, not a configuration knob. `build_file` raises `E_PROTOCOL` if a
payload needs more.

### Reassembly

1. Packet 0 must be present (it carries the header).
2. All packet ids `0…total_packets−1` must be present.
3. Concatenate chunks in order, truncate to `payload_len`.
4. Verify CRC-32 against the header.
5. If `flags & 1`, decompress with `OTL1`; compare the result with the original
   length and bytes.

Any failure raises `ReconstructionError` (`E_RECONSTRUCT`) with context.

## 5. Reed–Solomon details

- Field: GF(256), primitive polynomial **0x11D**.
- Code: systematic **RS(255, 223)**, `nsym = 32` parity bytes.
- Generator roots: α⁰, α¹, …, α^(nsym−1).
- Decoder: syndromes → erasure locator → Berlekamp–Massey (errors) →
  Chien search → Forney magnitudes; a linear solver handles mixed
  error/erasure cases. Over-capacity input raises `E_ECC`.
- The implementation is clean-room Python; no third-party RS source was copied.
  See `docs/LICENCES.md`.

## 6. Temporal blink layer

A blink word is **26 chips**:

```text
sync (13) + id (13)
```

- Sync: Barker-13 `1111100110101`. Aperiodic autocorrelation sidelobes are ±1.
- IDs: three 13-chip sequences selected by `search_codebook()` with
  - autocorrelation sidelobe ≤ 2,
  - pairwise/sync cross-correlation ≤ 5,
  - deterministic tie-break by imbalance.
- Chips are whole-screen polarity changes. The decoder searches both polarities
  (normal and inverted) with Pearson normalised cross-correlation.

### Rolling-shutter timing

For a camera with `height` rows, row time `t_row` and display symbol period
`T_sym`:

```text
visible symbols per capture = height × t_row / T_sym
readout time                = height × t_row
symbol period               = 1 / display_fps
```

A 26-chip word needs `readout ≥ 26·T_sym`. In addition, the exposure must be no
longer than one symbol period; otherwise each row integrates several chips.
At 60 Hz, `T_sym = 16.7 ms`, so a 27 ms readout sees ~1.62 symbols and the word
does not fit. At 1000 Hz, `T_sym = 1 ms`, a 27 ms readout sees ~27 symbols.

## 7. Compression container `OTL1`

```text
magic  b"OTL1"   (4 bytes)
ver    0x01      (1 byte)
olen   uint32    uncompressed length (big-endian)
ops    sequence of operations
```

| Opcode | Name | Encoding | Meaning |
| ---: | --- | --- | --- |
| 0x00 | LIT | `n:u8`, `n` bytes | literal run |
| 0x01 | REP | `value:u8`, `count:u8` | repeat one byte |
| 0x02 | CPY | `dist:u16`, `n:u8` | copy from `output[-dist:]` |
| 0x03 | INV | `dist:u16`, `n:u8` | copy the bitwise NOT of `output[-dist:]` |
| 0x04 | SEQ | `start:u8`, `step:i8`, `count:u8` | arithmetic sequence mod 256 |

The encoder is a deterministic greedy matcher with a 64 KiB window and a minimum
match of 4. It chooses the operation with the best length/cost ratio. `INV`
exists because the optical layer may transmit inverted copies and structured
payloads often contain inverted repeats. The decoder validates the magic,
version, output length and every operand.

## 8. Inversion

`FrameRenderer.render(cells, invert=True)` and `ImageOps.invert` produce the
photometric inverse of a frame. The decoder's `reference_levels()` combines
fiducial and data-area extrema, so an inverted frame still yields a valid
black/white reference. Inversion is a codec/renderer capability; it is not a
separate packet mode in this version.

## 9. Reference levels and classification

The four fiducials are black (the top-left has a white orientation hole), and
the gaps between cells are white. `reference_levels()` samples:

- 10th/90th percentiles of each fiducial patch;
- 1st/99th percentiles of the whole data area.

It takes `min(lows)` and `max(highs)`, so the reference survives all-black and
all-white payload frames and inverted frames. Classification uses a global
threshold from those levels, with a per-cell local threshold when the cell has
enough contrast. A frame with insufficient contrast raises `E_DETECT`.

## 10. Error codes

| Code | Raised by | Typical cause |
| --- | --- | --- |
| `E_CONFIG` | config/geometry | invalid parameter, cell too small |
| `E_PROTOCOL` | header/packet | bad magic/version, name too long, too many packets |
| `E_FRAME_FORMAT` | frame | wrong cell/byte count, value > 15 |
| `E_CRC` | CRC helpers | explicit CRC check |
| `E_DETECT` | detector | fiducials not found, low contrast |
| `E_SYNC` | temporal | flat chip sequence, no sync |
| `E_DECODE` | decoder | invalid decode state |
| `E_ECC` | Reed–Solomon | over-capacity codeword |
| `E_COMPRESSION` | OTL1 | bad magic/version/operand |
| `E_CHANNEL` | channel | non-grayscale image, missing OpenCV |
| `E_RECONSTRUCT` | packet | missing packet/block, CRC-32 mismatch |
| `E_MEASUREMENT` | metrics | mismatched BER lengths |
| `E_UNSUPPORTED` | feature gates | unavailable optional feature |

## 11. Worked capacity example

For 10,000 bytes of incompressible data:

```text
packet 0: 2421 bytes
packet 1: 2453
packet 2: 2453
packet 3: 2453
packet 4:  220   (10000 − 2421 − 3×2453)
total packets = 5
frames = 5 × 255 = 1275
screen time at 60 fps = 1275 / 60 = 21.25 s
net payload rate = 10000 × 8 / 21.25 = 3764.7 bps
```

The net rate is below the 4617 bps RS goodput because of the 32-byte header and
the partial last packet; the exact value is computed by `otl.metrics.Throughput`
and reported by E01/E09.
