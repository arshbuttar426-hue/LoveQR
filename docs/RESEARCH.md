# Research background and hypotheses

This document records the literature that motivates the project, the specific
architecture under test, and which parts of it have been tested. It is a
research note, not a claim of state-of-the-art performance.

## 1. The link in one paragraph

A screen is a dense, controllable light emitter; a smartphone camera is a
spatially resolving light sensor. A screen-to-camera link therefore has two
independent degrees of freedom:

- **space** — how many bits are encoded in one displayed image (cells, colours,
  shapes, luminance levels);
- **time** — how many images the camera can recover per second (display refresh,
  camera frame rate, exposure, rolling shutter).

The proposed architecture uses both: a 30-cell spatial frame carrying 120 bits,
and a temporal blink word carrying a sync pattern plus a small ID. A shared
instruction dictionary reduces the bytes that must cross the link, and a
Reed–Solomon packet layer absorbs lost frames.

## 2. Prior work

### 2.1 Screen–camera communication

- **COBRA** (Hao, Zhou & Xing, MobiSys 2012) streams 2D colour barcodes between
  smartphone screens and cameras. It adapts block size to blur and uses colour
  corner trackers. It establishes the core practical problems: blur, perspective,
  rolling shutter, auto-exposure and limited phone computation.
- **Strata** (Hu et al., MobiCom 2014) applies layered/hierarchical coding so a
  receiver can decode a coarse layer at low resolution and finer layers at higher
  resolution. This is the direct ancestor of “graceful degradation” designs.
- **LightSync** (Hu, Gu & Pu, MobiCom 2013) addresses unsynchronised
  screen–camera links, where the camera does not know the display timeline.
- **HiLight** (Li et al., MobiSys 2015) hides bits in pixel translucency so the
  screen can show ordinary content while transmitting. It demonstrates that
  unobtrusiveness and throughput trade against each other.
- **InFrame++** (Wang et al., MobiSys 2015) multiplexes a human-visible image and
  a hidden data channel in the same frame.
- **ChromaCode** (Zhang et al., MobiCom 2018) uses perceptually uniform colour
  changes and a concatenated code to reach high raw throughput with low
  perceptibility.

These systems show that screen–camera links are feasible on unmodified phones,
but their code designs are optimised for particular content, colour spaces or
hardware. They do not settle the specific question here: how far a **binary,
four-triangle cell alphabet** with a **fixed 120-bit frame** and a **temporal ID
layer** can be pushed with an open, reproducible implementation.

### 2.2 Rolling shutter as a receiver

- **Danakis et al.** (IEEE GLOBECOM Workshops 2012) showed that a rolling-shutter
  camera can recover an OOK data stream from an LED at a rate far above the
  camera frame rate, because different rows expose different time slices.
- **Luxapose** (Kuo et al., MobiCom 2014) uses the same effect for visible-light
  positioning: each luminaire transmits an identifier, and a single frame yields
  both the identifier and the angle of arrival.
- **VRCodes** (Woo, Lippman & Raskar, ISMAR 2012) exploit rolling shutter for
  unobtrusive active visual codes.

The important consequence for this project is a hard timing inequality:

```text
visible display symbols per capture = camera_height × row_time / symbol_period
```

The camera frame rate does **not** multiply the display refresh rate. A 26-chip
word therefore needs a readout at least 26 symbol periods long. At a 60 Hz
display (16.7 ms per symbol) and a 27 ms readout, only ~1.6 symbols fit; the word
cannot be captured in one frame. This is why E08 treats 60 Hz blink IDs as a
rejected hypothesis rather than a software bug.

### 2.3 Standards and coding

- **IEEE 802.15.7** is the optical wireless communication standard family for
  visible light; **ITU-T G.9991** covers high-speed indoor visible-light
  communication. They provide vocabulary and regulatory context, not the
  specific 30-cell frame used here.
- **Reed–Solomon** (Reed & Solomon, 1960) is the natural choice for a packet
  layer that sees burst frame loss: byte interleaving turns a lost frame into one
  erasure per codeword.
- **Barker-13** (Barker, 1953) gives a 13-chip sync with aperiodic
  autocorrelation sidelobes of ±1. The three IDs in this project were selected by
  a deterministic search (`search_codebook`) under a sidelobe/cross-correlation
  criterion; no third-party sequence table is copied.
- **CRC-16/CCITT-FALSE** and **CRC-32** provide fast frame/file integrity checks.
- **LZ77-style dictionary coding** (Ziv & Lempel, 1977) motivates the `OTL1`
  container. `OTL1` is deliberately simpler and deterministic; zlib/zstd are used
  only as reference points in E07, not in the protocol.

### 2.4 Human factors

Flicker is a first-order constraint for any visible temporal code. The literature
on flicker fusion and the phantom-array effect (e.g. Roberts & Wilkins, 2013)
shows that perceptible flicker can persist above 1 kHz under eye movement. This
project does not run a human-subject study; it treats flicker as an open risk and
keeps the temporal layer optional and separate from the spatial frame.

## 3. The architecture under test

| Component | Proposal | Tested here |
| --- | --- | --- |
| Cell | Four independent black/white triangles | Yes, 16 patterns (E02) |
| Frame | 6 × 5 cells × 4 bits = 120 bits | Yes (E01, E03, E04) |
| Header | 4-bit packet id + 12-bit frame index | Yes (frame tests) |
| Integrity | CRC-16 per frame, CRC-32 per file | Yes (unit/integration) |
| Packet | 255 frames, 11× RS(255,223), interleaved | Yes (E05, E06) |
| Temporal ID | 13-chip Barker sync + 13-chip ID | Yes (E08) |
| Inversion | Normal/inverted frame pairs | Codec support; not a separate experiment |
| Compression | Shared dictionary REPEAT/COPY/INVERT/SEQUENCE | Yes (E07) |
| Rolling shutter | Recover multiple symbols per capture | Yes, simulated (E08) |
| Physical link | Real phone at real distance/angle | **Not yet** |

## 4. Hypotheses and status

| ID | Hypothesis | Status | Evidence |
| --- | --- | --- | --- |
| H1 | Four binary triangles give 16 visually separable patterns. | `OBSERVED (SIMULATED)` | E02: perfect at clean/mild/harsh/extreme; degrades only in the deliberately brutal channel. Minimum Hamming distance is 1. |
| H2 | 30 cells × 4 bits = 120 raw bits, 11 payload bytes/frame. | `THEORETICAL` | E01 arithmetic and frame tests. |
| H3 | A 26-chip blink word can be read at 60 Hz display refresh. | **`REJECTED`** | E08: readout sees ~1.62 symbols at 60 Hz; word does not fit. |
| H4 | Rolling-shutter capture recovers the word when readout spans ≥ 26 symbol periods and exposure ≤ 1 symbol. | `OBSERVED (SIMULATED)` + `THEORETICAL` | E08: 39/39 correct when the temporal budget is satisfied; 0 when it is not. |
| H5 | Byte interleaving + RS(255,223) tolerates 32 lost frames per packet. | `OBSERVED (SOFTWARE)` | E05: success through 32, first failure at 33, random and burst identical. |
| H6 | The RS layer corrects `2·errors + erasures ≤ nsym` and rejects beyond. | `OBSERVED (SOFTWARE)` | E06: boundary at 32, failures above it. |
| H7 | `OTL1` reduces screen time for structured payloads without corrupting data. | `OBSERVED (SOFTWARE)` | E07: strong ratios on repetitive/text data, ~1.0 on random, exact roundtrip. |
| H8 | The spatial decoder tolerates realistic blur/noise/JPEG/perspective. | `OBSERVED (SIMULATED)` | E03/E04: brightness and perspective boundaries measured; no failure inside the tested blur σ 16, noise σ 90 or vignette 0.9 range. |
| H9 | Simulated results predict a real phone link. | `OBSERVED (PHYSICAL / CAMERA CAPTURE)` for one link; broader prediction open | E11: an iPhone14,2 decoded 255/255 frames and a SHA-verified payload; normalized rates matched E01 exactly. Distance/angle/illuminance boundaries are still untested. |

## 5. What is novel here

This is not a new modulation scheme. The contribution is:

1. an **open, typed, deterministic** implementation of the proposed architecture,
   including a clean-room RS codec and a dependency-free instruction container;
2. an **append-only experiment harness** that retains raw trials, failures and
   environment metadata;
3. an **evidence policy** that separates simulated observations from physical
   verification, and explicitly rejects claims the data do not support;
4. a **measured timing constraint** for the temporal layer that is often omitted
   in informal descriptions of screen–camera links.

## 6. Open questions

- How much does a real phone's auto-exposure and demosaicing change the spatial
  error rate compared with the synthetic channel?
- What is the true per-frame latency of a phone camera pipeline at 1080p, and
  does it permit 30–60 fps decoding?
- Can the temporal layer be made flicker-free at the symbol rates required for a
  26-chip word, or must it use a rolling-shutter-only mode at high display
  refresh?
- Does the 4-bit packet-id ceiling justify a second header extension for larger
  files, or is 39 KiB the intended design point?
- How do display gamma, colour temperature and screen protectors affect the
  black/white reference levels used by `reference_levels`?

## 7. References

1. T. Hao, R. Zhou, G. Xing. “COBRA: Color Barcode Streaming for Smartphone
   Systems.” *MobiSys 2012*, pp. 85–98. DOI: 10.1145/2307636.2307645.
2. W. Hu, J. Mao, Z. Huang, Y. Xue, J. She, K. Bian, G. Shen. “Strata: Layered
   Coding for Scalable Visual Communication.” *MobiCom 2014*, pp. 79–90.
   DOI: 10.1145/2639108.2639132.
3. W. Hu, H. Gu, Q. Pu. “LightSync: Unsynchronized Visual Communication over
   Screen–Camera Links.” *MobiCom 2013*, pp. 15–26.
4. T. Li, C. An, X. Xiao, A. T. Campbell, X. Zhou. “Real-Time Screen–Camera
   Communication Behind Any Scene.” *MobiSys 2015*, pp. 197–211.
   DOI: 10.1145/2742647.2742667.
5. A. Wang, S. Ma, C. Hu, J. Huai, C. Peng, G. Shen. “Enhancing Reliability to
   Boost the Throughput over Screen–Camera Links.” *MobiCom 2014*.
6. A. Wang et al. “InFrame++: Achieve Simultaneous Screen–Human Viewing and
   Hidden Screen–Camera Communication.” *MobiSys 2015*.
   DOI: 10.1145/2742647.2742652.
7. K. Zhang, C. Wu, C. Yang, Y. Zhao, K. Huang, C. Peng, Y. Liu, Z. Yang.
   “ChromaCode: A Fully Imperceptible Screen–Camera Communication System.”
   *MobiCom 2018*, pp. 575–590. DOI: 10.1145/3241539.3241543.
8. C. Danakis, M. Afgani, G. Povey, I. Underwood, H. Haas. “Using LED Based
   Lighting for Visible Light Communication with a Rolling Shutter Camera.”
   *IEEE GLOBECOM Workshops 2012*.
9. Y.-S. Kuo, P. Pannuto, K.-J. Hsiao, P. Dutta. “Luxapose: Indoor Positioning
   with Mobile Phones and Visible Light.” *MobiCom 2014*.
   DOI: 10.1145/2639108.2639109.
10. G. Woo, A. Lippman, R. Raskar. “VRCodes: Unobtrusive and Active Visual Codes
    for Interaction by Exploiting Rolling Shutter.” *ISMAR 2012*.
11. IEEE 802.15.7-2018, *IEEE Standard for Local and Metropolitan Area Networks —
    Part 15.7: Short-Range Optical Wireless Communications*.
12. ITU-T Recommendation G.9991 (2019), *High-speed indoor visible light
    communication transceiver system*.
13. I. S. Reed, G. Solomon. “Polynomial Codes over Certain Finite Fields.”
    *SIAM Journal on Applied Mathematics*, 8(2):300–304, 1960.
14. R. H. Barker. “Group Synchronizing of Binary Digital Systems.” In
    *Communication Theory*, Butterworth, 1953.
15. S. B. Wicker, V. K. Bhargava (eds.). *Reed–Solomon Codes and Their
    Applications*. IEEE Press, 1994.
16. F. J. MacWilliams, N. J. A. Sloane. *The Theory of Error-Correcting Codes*.
    North-Holland, 1977.
17. J. Ziv, A. Lempel. “A Universal Algorithm for Sequential Data Compression.”
    *IEEE Transactions on Information Theory*, 23(3):337–343, 1977.
18. J. Roberts, A. Wilkins. “Flicker Can Be Perceived During Saccades at
    Frequencies in Excess of 1 kHz.” *Lighting Research and Technology*,
    45(1):124–132, 2013.
19. P. Deutsch, J.-L. Gailly. RFC 1950/1951/1952 (zlib), 1996.
20. Y. Collet, M. Kucherawy. RFC 8878 (Zstandard Compression), 2021.
