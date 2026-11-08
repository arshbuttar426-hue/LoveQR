# M11 handoff and LoveQR product plan

**Written:** 2026-11-08
**State at handoff:** M11 implementation, tests and five of six physical arms are
complete. A4 (`A4_always_on`) has no physical session. The lab is **not a git
repository yet**. This document is the ordered finish plan, the exact A4
procedure, the commit strategy, and the architecture for a separate product
repository called **LoveQR**.

> **Do not rewrite frozen evidence.** M9/M10 sessions, locks, run directories and
> claim rows are immutable. M11 additions are additive. A failed M11 capture is
> retained and reported, not deleted.

---

## 0. What is already done

| Item | State |
| --- | --- |
| `otl/protocol/m11.py` | Compact 15-byte header, capacity-aware `nsym`, `OTB1` bundle, v2 encode/decode/reassemble |
| `otl/compress/adaptive.py` | Raw vs `OTL1` selection |
| `experiments/m11_payloads.py` | Six deterministic arms and frame builders |
| `scripts/m11_prepare.py` | Renders frames + frozen M9 player + `m11_manifest.json` |
| `scripts/m11_capture_arm.py` | Create → attach → capture → ingest → validate → finalize one arm |
| `experiments/e13_packet_utilisation.py` | Software validation, physical `m11-*` analysis, exact loss identity, capacity table |
| `tests/test_m11_packet_utilisation.py` | 14 tests; full suite 183 passing |
| Physical arms | A0, A1, A2, A3, A5 captured, locked and SHA-verified |
| Failed attempt | `m11-a1-fill-adaptive-20261108T122602Z` retained (6/255 frames) |
| Report | `docs/M11_PACKET_UTILISATION.md` |
| Canonical E13 run | `experiments/E13_packet_utilisation/runs/20261108T125654Z-e5001c/` |

The only missing physical arm is A4, the always-on control. Everything else in
this plan is verification, documentation, commit and product bootstrap.

---

## 1. Ordered TODO for the next session

### Phase 1 — preflight (5 min)

- [ ] Confirm you are in `/Users/arshbuttar/OPTICAL_TRANSMISSION_LAB`.
- [ ] Confirm no M9/M10 file changed since the M11 work began:

  ```bash
  find datasets/physical/m9-* datasets/physical/m10-* \
    -newermt '2026-11-08 17:45:00' -type f | wc -l
  ```

  Expected `0`.
- [ ] Confirm the five successful M11 sessions still lock:

  ```bash
  python3 -m otl session list datasets/physical | grep m11
  python3 -m pytest tests/test_m11_packet_utilisation.py -q
  ```

- [ ] Regenerate the staging tree if it is missing (it is regenerable, about
  57 MB on disk):

  ```bash
  for arm in A0_reference A1_fill_adaptive A2_bundle \
             A3_dictionary A4_always_on A5_rs24; do
    python3 scripts/m11_prepare.py --arm "$arm" \
      --out "datasets/physical/m11-staging/$arm" --fps 10
  done
  ```

### Phase 2 — A4 physical capture (about 10 min)

- [ ] Set display brightness back to the M10/M11 fraction:

  ```bash
  python3 scripts/display_brightness.py --set 0.354058
  python3 scripts/display_brightness.py --get
  ```

- [ ] Get the existing Safari window id:

  ```bash
  osascript -e 'tell application "Safari" to get id of every window'
  ```

- [ ] Aim the iPhone at the Safari player. The working geometry is
  `{250, 120, 700, 700}` points; the whole frame and all four fiducials must be
  inside the camera image. Centre Stage is already disabled
  (`centerStageControlMode = user`, `isCenterStageEnabled = false`); framing is
  physical and hand-held.

- [ ] Run a 2 s probe. Proceed when at least five CRC-valid frames decode:

  ```bash
  rm -f /tmp/lqr_a4_probe.mp4
  python3 - <<'PY'
  import subprocess, sys, cv2
  from otl.config import ExperimentConfig
  from otl.decoder.spatial import decode_image
  from otl.errors import OTLError
  cfg = ExperimentConfig(); layout = cfg.layout()
  out = "/tmp/lqr_a4_probe.mp4"
  subprocess.run([sys.executable, "-m", "otl", "capture", "video", "1",
                  "--out", out, "--duration", "2", "--fps", "30",
                  "--size", "1920x1440"], check=True, capture_output=True)
  cap = cv2.VideoCapture(out); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
  ok = crc = 0
  for _ in range(n):
      ret, img = cap.read()
      if not ret: break
      try:
          d = decode_image(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),
                           layout, cfg.receiver, cfg.protocol)
          ok += 1
          crc += int(d.crc_ok)
      except OTLError:
          pass
  print("probe", n, ok, crc)
  raise SystemExit(0 if crc >= 5 else 1)
  PY
  ```

- [ ] Capture A4. 510 frames at 10 fps is 51 s; 57 s gives margin:

  ```bash
  python3 scripts/m11_capture_arm.py --arm A4_always_on \
    --duration 57 --window-id <WINDOW_ID>
  ```

  Expected session name: `m11-a4-always-on-<UTC>`.

- [ ] If the probe or capture loses the display, **keep the locked session**
  and retry with a new timestamped session. Both stay on disk; E13 will report
  the failed one separately.

**A4 acceptance criteria**

- `status == "final"` and `session.lock.json` exists.
- `session.transmitter.m11.arm_id == "A4_always_on"`.
- `total_packets == 2`; both packets reassemble.
- Reconstructed payload SHA-256 equals the arm manifest.
- E13 marks the session `status: ok` and includes it in measured throughput.
- Application throughput should land near the software value **379.76 bps**
  (2,421 bytes over two packets at ~10 fps); physical delivery may reduce it.
- A1/A4 physical ratio should be about **2.0×** (one packet vs two). Report the
  measured ratio, not the projection, and state the delivery rates.

### Phase 3 — final analysis and verification (15 min)

- [ ] Run E13 with **no session filter** so it discovers every locked
  `m11-*` session, including A4:

  ```bash
  python3 -m experiments.run_all --only E13_packet_utilisation
  ```

- [ ] Inspect the new run:

  ```bash
  python3 - <<'PY'
  import glob, json, os
  run = sorted(glob.glob("experiments/E13_packet_utilisation/runs/*"),
               key=os.path.getmtime)[-1]
  d = json.load(open(run + "/processed/summary.json"))
  print(run)
  print(d["summary"]["evidence_source"])
  for row in d["summary"]["physical_sessions"]:
      print(row["arm_id"], row["session_id"], row["status"])
  print(d["conclusion"])
  PY
  ```

- [ ] Update `docs/M11_PACKET_UTILISATION.md`:
  - replace the canonical run id with the new one;
  - add the A4 session row and measured throughput;
  - change "five of six" to "six of six" **only if A4 succeeded**;
  - update C31 from `OBSERVED (SOFTWARE) only` to physical if it succeeded;
  - keep A4 as software-only if it failed, with the failed row named.
- [ ] Update `docs/STATUS.md`, `docs/MILESTONES.md`, `docs/EXPERIMENTS.md` and
  `docs/REPRODUCE.md` to point at the new canonical run. Let `run_all` refresh
  `results/index.json`, `results/SUMMARY.md` and `results/runs.jsonl`; do not
  hand-edit derived results.
- [ ] Run the full verification:

  ```bash
  python3 -m pytest
  python3 -m compileall -q otl experiments scripts tests
  python3 scripts/checksums.py --write
  python3 scripts/checksums.py --verify
  ```

- [ ] Confirm the E13 manifest is physical, not software:

  ```bash
  python3 - <<'PY'
  import glob, json, os
  run = sorted(glob.glob("experiments/E13_packet_utilisation/runs/*"),
               key=os.path.getmtime)[-1]
  m = json.load(open(run + "/manifest.json"))
  print(run)
  print(m["evidence_source"], m["simulation_only"], m["classification"])
  PY
  ```

  Expected: `PHYSICAL / CAMERA CAPTURE  False  PHYSICAL (camera capture) + SOFTWARE (packet/RS validation)`.

- [ ] Update `CHECKSUMS.sha256` after **all** documentation edits. It covers
  source only (97 files before M11 additions; it will grow).

### Phase 4 — commit the lab (20 min)

The repository is 37 GB on disk, almost all of it raw camera frames and MP4s.
**Do not commit raw captures to plain git.** Git LFS is not installed. The
source, docs, locks, manifests, hashes and experiment runs are small and are the
reproducible record; the raw files stay on disk and are fingerprinted.

- [ ] Create `.gitignore` at the repository root:

  ```gitignore
  # Python
  __pycache__/
  *.py[cod]
  .pytest_cache/
  .mypy_cache/
  .ruff_cache/
  .venv/
  venv/
  *.egg-info/
  build/
  dist/

  # OS / editor
  .DS_Store
  .idea/
  .vscode/

  # M11 staging is regenerable
  datasets/physical/m11-staging/

  # Raw physical evidence is retained on disk, not in plain git.
  # Hashes are in each session's captures/index.jsonl and session.lock.json.
  datasets/physical/*/captures/frames/
  datasets/physical/*/captures/originals/
  datasets/physical/*/display/*.png
  datasets/physical/attempts/**/originals/
  datasets/physical/attempts/**/frames/

  # Large media anywhere else in the evidence tree
  datasets/physical/**/*.mp4
  datasets/physical/**/*.mov
  ```

- [ ] Initialise and inspect before committing:

  ```bash
  git init -b main
  git add -A
  git status --short | head -50
  git ls-files -z | xargs -0 du -k | sort -rn | head -20
  ```

  No single file should be near 100 MB. If one is, add its directory to
  `.gitignore` rather than committing it.

- [ ] Commit with a message that states the milestone and the evidence state:

  ```bash
  git commit -m "M11: packet-utilisation optimisation, five physical arms

  - add additive M11 codec: 15-byte header, capacity-aware nsym, OTB1 bundle
  - add adaptive raw/OTL1 selection
  - add deterministic arms, prepare and capture tooling
  - add E13 analysis with exact loss identity and capacity table
  - measure A0/A1/A2/A3/A5 physically; A4 remains software-only
  - retain failed A1 capture and report it
  - 183 tests passing"
  ```

- [ ] Tag the exact codec state the product will pin:

  ```bash
  git tag -a lab-m11 -m "M11 codec and evidence state for LoveQR"
  git rev-parse HEAD
  ```

  Record the full SHA; it becomes `OTL_COMMIT` for LoveQR.

- [ ] Archive the raw evidence separately (external drive or object store) and
  record the archive hash in `docs/EVIDENCE_ARCHIVE.md` (new file, commit it):

  ```bash
  tar -cf /Volumes/<archive>/otl-physical-20261108.tar datasets/physical
  shasum -a 256 /Volumes/<archive>/otl-physical-20261108.tar
  ```

  This is the only copy of multi-GB raw data. Do not leave it on one disk.

### Phase 5 — create the LoveQR repository (30 min)

Do this **after** the lab commit and tag, so LoveQR can pin a real revision.

- [ ] Create the repository next to the lab, not inside it:

  ```bash
  mkdir -p /Users/arshbuttar/LoveQR
  cd /Users/arshbuttar/LoveQR
  git init -b main
  ```

- [ ] Bootstrap the layout from §3 below.
- [ ] Pin the lab revision in `pyproject.toml`:

  ```toml
  dependencies = [
    "optical-transmission-lab @ git+file:///Users/arshbuttar/OPTICAL_TRANSMISSION_LAB@<OTL_COMMIT>",
  ]
  ```

  For a public release, replace the file URL with the public git URL and a tag.
- [ ] Copy protocol test vectors from the lab (payloads, frame hashes, expected
  packet bytes, bundle hashes) into `tests/vectors/`. The product test suite must
  fail if the pinned codec changes a vector.
- [ ] First product commit: `LQ0: bootstrap LoveQR on pinned M11 codec`.

### Phase 6 — close the handoff

- [ ] Write a one-page `docs/M11_CLOSEOUT.md` with:
  - final claim table (C26–C33),
  - A4 outcome,
  - canonical E13 run,
  - lab commit SHA and tag,
  - LoveQR commit SHA,
  - what remains unmeasured.
- [ ] Regenerate `CHECKSUMS.sha256` once more and verify.
- [ ] Report to the user: measured gains, A4 result, commit hashes, product repo
  path, and the exact next product milestone.

---

## 2. A4 in one block

```bash
cd /Users/arshbuttar/OPTICAL_TRANSMISSION_LAB
python3 scripts/display_brightness.py --set 0.354058
osascript -e 'tell application "Safari" to get id of every window'
# aim the iPhone; run the probe from Phase 2 until crc >= 5
python3 scripts/m11_capture_arm.py --arm A4_always_on \
  --duration 57 --window-id <WINDOW_ID>
python3 -m experiments.run_all --only E13_packet_utilisation
```

Expected A4 arm facts: 2,421 application bytes, 2,450 wire bytes, 2 packets,
510 frames, 255,231 RS code, `nsym=32`, 32-byte M9 header. Software rate
379.76 bps at 10 fps. Physical rate is whatever the capture delivers; do not
substitute the software number.

---

## 3. LoveQR architecture

### 3.1 Product thesis

**LoveQR sends files from one screen to one camera with no network, no pairing,
no account and no server.** The sender displays an animated LoveQR; the receiver
watches it. The payload is verified byte-for-byte with SHA-256 before it is
offered to the user.

The name is the promise: a deliberate, personal transfer. The product is not a
faster Wi-Fi replacement and must not pretend to be. It is for the cases where a
network is unavailable, untrusted or forbidden: air-gapped machines, offline
events, field work, kiosks, cross-ecosystem one-off handoffs and small secrets.

### 3.2 Principles

1. **Offline by default.** No network calls, no telemetry, no cloud.
2. **Exact or nothing.** A payload is shown only after SHA-256 verification.
3. **Small, visible, interruptible.** Show progress in frames and seconds; the
   receiver can stop and resume.
4. **One protocol, two transports.** The same M11 packet format works for a
   desktop player, a browser tab and a native phone app.
5. **No silent degradation.** If the channel drops, the UI says so; it never
   claims success from a partial decode.
6. **Evidence-backed claims only.** Product copy quotes measured rates with the
   device, fps and payload size attached.

### 3.3 What ships first

| Release | Surface | Scope |
| --- | --- | --- |
| `0.1` developer preview | Python CLI + static sender page | Send/receive one file up to one packet (2,421 B) on macOS with a camera |
| `0.2` | CLI + bundle | Multi-entry `OTB1`, four small files in one packet, resume |
| `0.3` | PWA sender | Drag-and-drop, offline install, fps slider, frame preloading |
| `0.4` | Native receiver | iOS app using the same geometry and protocol vectors |
| `1.0` | Product | Signed/encrypted envelopes, multi-packet, polished errors, installers |

### 3.4 Repository layout

```
LoveQR/
├── README.md
├── LICENSE
├── pyproject.toml
├── src/
│   └── loveqr/
│       ├── __init__.py
│       ├── cli.py              # send / receive / probe / selftest
│       ├── codec.py            # thin wrapper over otl.protocol.m11
│       ├── envelope.py         # .lqr metadata, flags, manifest, signatures
│       ├── plan.py             # payload → packet/bundle plan, size limits
│       ├── verify.py           # SHA-256, per-entry CRC, resume state
│       ├── tx/
│       │   ├── frames.py       # arm → frame PNGs / canvas frames
│       │   ├── player.py       # offline HTML player (60/30/10 fps)
│       │   └── assets/
│       ├── rx/
│       │   ├── capture.py      # platform camera adapters
│       │   ├── decode.py       # geometry + M11 packet decode
│       │   └── progress.py     # frame/erasure/packet progress model
│       ├── web/
│       │   ├── sender/         # static PWA sender
│       │   └── scanner/        # milestone LQ5 only
│       └── telemetry.py        # local counters, off by default
├── tests/
│   ├── vectors/                # copied from the lab and hashed
│   ├── test_codec_vectors.py
│   ├── test_envelope.py
│   ├── test_roundtrip.py
│   └── test_cli.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PROTOCOL.md
│   ├── SECURITY.md
│   ├── ROADMAP.md
│   └── DEMO.md
├── scripts/
│   ├── make_vectors.py
│   └── build_player.py
└── examples/
    ├── hello.txt
    └── four-files/
```

### 3.5 Core API

```python
from loveqr import Sender, Receiver, Envelope

# sender
env = Envelope.from_path("notes.txt")          # entries, sizes, hashes
frames = Sender(env, fps=10, nsym=32).frames() # 255-frame packet plan
Sender(env).write_player("out/", fps=10)       # offline player + manifest

# receiver
rx = Receiver(camera=1, fps=30)
result = rx.capture(seconds=35)                # decode + reassemble
result.verify()                                # SHA-256 per entry
result.export("received/")                     # only after verification
```

The public API never exposes raw RS blocks. `codec.py` may, for tests and
advanced users.

### 3.6 Data flow

```
file(s)
  → Envelope (names, sizes, CRC-32, SHA-256, flags)
  → plan (raw vs OTL1, nsym, header, bundle, packet count)
  → M11 packet bytes
  → 255 frames × 11 bytes → 30 cells/frame
  → renderer → player (10/30/60 fps)
  → screen
  → camera video
  → detect → rectify → sample → classify → CRC
  → unique frames → RS erasure/error correction
  → packet reassembly
  → bundle unpack → per-entry CRC/SHA
  → verified export
```

### 3.7 Protocol boundaries

- **Frame:** frozen 30-cell FULL16, 11 payload bytes/frame, CRC-16.
- **Packet:** 255 frames, 11 interleaved RS blocks, `nsym` configurable but
  `32` reference and `24` capacity mode.
- **Header:** M11 15-byte compact header for new payloads; M9 32-byte header
  remains readable for compatibility.
- **Bundle:** `OTB1` with per-entry CRC-32 and optional SHA-256.
- **Hard cap:** the 4-bit packet id allows at most 16 packets. LoveQR v1 must
  either stay under 39,216 bytes or declare a "multi-transfer" UX where the user
  displays a second session. Do **not** silently truncate. A LoveQR v2 frame
  with a larger packet id is a separate protocol version, not a config flag.

### 3.8 Performance envelope (measured basis)

| Payload | Path | Measured | Notes |
| --- | --- | --- | --- |
| 317 B | frozen M9 | 99.44 bps | 255 frames |
| 2,421 B | A1 adaptive raw | 759.45 bps | 255 frames, at 10 fps |
| 2,526 B | A5 `nsym=24` | 792.39 bps | 255 frames, at 10 fps |
| 2,280 B bundle | A2 | 715.22 bps | four entries |
| 145,745 B | A3 dictionary | 45,705.64 bps pre-compression | compression, not wire rate |

At 10 fps a full packet takes 25.5 s. A 2,421-byte file therefore transfers in
about 25–35 s including capture margin. At 60 fps the arithmetic projection is
4,557 bps for a full packet, but **60 fps is not measured**; product copy must
label it a projection.

### 3.9 Receiver platforms

- **0.1:** macOS + AVFoundation/Continuity Camera, using the lab capture path.
- **0.2:** Linux V4L2 and Windows MediaFoundation adapters.
- **0.4:** iOS native receiver. The Swift detector must reproduce the Python
  geometry and pass the same frame vectors. Do not ship a Swift decoder that has
  not decoded the lab's recorded sessions.
- **Later:** browser scanner via WASM/OpenCV. This is the highest-risk item;
  keep it out of the first release.

### 3.10 Security and privacy

- The optical channel is a **broadcast**: anyone in line of sight can record the
  frames. Do not claim confidentiality by default.
- Optional envelope encryption: AES-256-GCM with Argon2id-derived key. The
  header carries the KDF parameters and nonce; the payload is authenticated.
- Optional signing: Ed25519 over the manifest. A signature proves origin, not
  secrecy.
- Replay: include a random 128-bit session id and a timestamp in the signed
  manifest.
- No network telemetry. Crash reports are opt-in and must never include payload
  bytes.
- Threat model to document explicitly: shoulder surfing, camera in the room,
  malicious sender, replay, and metadata leakage from filenames.

### 3.11 UX rules

- Sender shows: file name(s), total bytes, packet count, fps, estimated seconds,
  and a large "Start" button.
- Receiver shows: live detection state, frames seen / 255, packets received /
  expected, erasures, and a single progress bar.
- On failure: say which stage failed (no frame, CRC, RS, packet, hash) and offer
  a concrete fix (move closer, fill the frame, raise brightness, lower fps).
- Never show a "100%" bar before SHA-256 passes.

### 3.12 Testing strategy

1. **Codec vectors** copied from the lab: exact bytes for A0/A1/A2/A5.
2. **Round-trip** every envelope through the pinned `otl.protocol.m11`.
3. **CLI contract** tests with a fixture session (no camera).
4. **Physical smoke test** on one device pair, one file, SHA-verified.
5. **Cross-implementation** test: Swift/iOS decoder against Python vectors.
6. **Failure tests:** truncated capture, wrong camera, moving frame, bad hash.
7. **No-network test:** run with sockets blocked; the app must still work.

### 3.13 LoveQR milestones

| ID | Milestone | Exit criterion |
| --- | --- | --- |
| LQ0 | Bootstrap | Repo, licence, pinned lab commit, vectors, `pytest` green |
| LQ1 | Sender CLI + player | `loveqr send` writes frames + offline player + manifest |
| LQ2 | Receiver CLI | One 2,421-byte file decoded from a camera with SHA-256 match |
| LQ3 | Bundle + resume | Four entries in one packet; interrupted capture resumes |
| LQ4 | PWA sender | Offline page sends a file at stable 10 fps in Safari/Chrome |
| LQ5 | Native iOS receiver | iPhone decodes the same file in under 60 s |
| LQ6 | Security + polish | Encrypted/signed envelope, clear errors, installers |
| LQ7 | Public beta | Docs, demo video, measured claims, issue tracker |

### 3.14 Non-goals for v1

- Streaming audio/video.
- Files larger than 39,216 bytes in one session (use multi-transfer UX).
- General-purpose compression claims.
- 60 fps performance claims until measured.
- Anonymous/deniable messaging.
- Replacing AirDrop, Nearby Share or Wi-Fi.

### 3.15 Naming and packaging

- Product: **LoveQR**
- Python distribution: `loveqr`
- CLI: `loveqr`
- Envelope extension: `.lqr`
- Lab dependency: `optical-transmission-lab` pinned by commit/tag
- Licence: MIT for the code; the lab's evidence keeps its own provenance.

---

## 4. What stays in the lab

The lab remains the evidence archive and the protocol reference:

- every M9/M10/M11 session and lock;
- every E01–E13 run;
- the physical reports and claim table;
- the exact decoder, renderer and packet implementation;
- the reproduction commands.

LoveQR consumes the codec and copies test vectors. It does **not** copy the lab's
evidence tree, and it must not edit lab files. If LoveQR needs a protocol change,
that change is proposed in the lab first, measured there, and then pinned.

---

## 5. Final checklist

- [ ] A4 captured, locked and analysed (or explicitly deferred with a failed-row
      record).
- [ ] E13 rerun with no session filter; manifest says physical.
- [ ] M11 report and status updated with A4 outcome.
- [ ] `python3 -m pytest` green.
- [ ] `python3 -m compileall -q otl experiments scripts tests` clean.
- [ ] `python3 scripts/checksums.py --write && python3 scripts/checksums.py --verify`.
- [ ] Lab `.gitignore`, commit and `lab-m11` tag.
- [ ] Raw evidence archived off-machine with a recorded hash.
- [ ] LoveQR repo created, pinned to `OTL_COMMIT`, first commit made.
- [ ] `docs/M11_CLOSEOUT.md` written.
- [ ] User report includes measured gains, A4 result, commit hashes and the next
      LoveQR milestone.
