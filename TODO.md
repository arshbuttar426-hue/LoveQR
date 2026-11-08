# TODO — finish M11, commit, and start LoveQR

**State:** M11 is implemented and tested (183 tests). Five of six arms are
captured, locked and SHA-verified. A4 (`A4_always_on`, two packets) is the only
missing physical arm. The lab is not yet a git repository, and LoveQR does not
exist yet.

**Full detail:** [`docs/M11_HANDOFF_AND_LOVEQR.md`](docs/M11_HANDOFF_AND_LOVEQR.md)

## P0 — capture A4 (blocking)

- [ ] Set brightness `0.354058`; get the Safari window id.
- [ ] Aim the iPhone so the whole frame and all four fiducials are visible.
- [ ] Run the 2 s probe; require at least 5 CRC-valid frames.
- [ ] Capture:
  ```bash
  python3 scripts/m11_capture_arm.py --arm A4_always_on \
    --duration 57 --window-id <WINDOW_ID>
  ```
- [ ] Acceptance: final lock, `arm_id == A4_always_on`, 2/2 packets, payload
  SHA-256 matches, E13 `status: ok`, measured rate near 379.76 bps.
- [ ] If it fails, keep the locked session and retry under a new timestamp.

## P1 — final analysis and docs

- [ ] `python3 -m experiments.run_all --only E13_packet_utilisation` (no
      session filter, so A4 is discovered).
- [ ] Add A4 to `docs/M11_PACKET_UTILISATION.md`; update the canonical run id.
- [ ] Update `docs/STATUS.md` C31, `docs/MILESTONES.md`,
      `docs/EXPERIMENTS.md` and `docs/REPRODUCE.md`.
- [ ] Write `docs/M11_CLOSEOUT.md` with the final claim table, A4 outcome,
      canonical run, commit SHA and remaining unmeasured items.

## P2 — verify

- [ ] `python3 -m pytest`
- [ ] `python3 -m compileall -q otl experiments scripts tests`
- [ ] `python3 scripts/checksums.py --write`
- [ ] `python3 scripts/checksums.py --verify`
- [ ] Confirm the E13 manifest says `PHYSICAL / CAMERA CAPTURE`,
      `simulation_only: false`.

## P3 — commit the lab

- [ ] Add `.gitignore` (raw captures, staging, caches, venvs; see handoff §1
      Phase 4).
- [ ] `git init -b main`, `git add -A`, check no file is near 100 MB.
- [ ] Commit M11 with the evidence state in the message.
- [ ] Tag `lab-m11`; record `git rev-parse HEAD` as `OTL_COMMIT`.
- [ ] Archive the 37 GB raw evidence off-machine and record the archive SHA-256.

## P4 — create LoveQR

- [ ] `mkdir /Users/arshbuttar/LoveQR && git init -b main`.
- [ ] Bootstrap `src/loveqr/` (CLI, codec wrapper, envelope, tx, rx), tests,
      vectors and docs from the handoff §3.4.
- [ ] Pin `optical-transmission-lab @ git+file:///...@<OTL_COMMIT>`.
- [ ] Copy codec vectors from all six lab arms; add a test that fails if a
      vector changes.
- [ ] First commit: `LQ0: bootstrap LoveQR on pinned M11 codec`.

## P5 — product milestones

- [ ] LQ1 sender CLI + offline player.
- [ ] LQ2 receiver CLI, one 2,421-byte file SHA-verified.
- [ ] LQ3 `OTB1` bundle + resume.
- [ ] LQ4 PWA sender.
- [ ] LQ5 native iOS receiver against lab vectors.
- [ ] LQ6 encryption/signing + UX.
- [ ] LQ7 public beta.

## Definition of done for M11

- [ ] A4 is either physically measured or explicitly recorded as deferred.
- [ ] Every successful arm matches its manifest SHA-256.
- [ ] The failed A1 capture is still present and reported.
- [ ] Full test suite and compileall are clean.
- [ ] `CHECKSUMS.sha256` verifies.
- [ ] Lab commit and `lab-m11` tag exist.
- [ ] LoveQR repository exists and pins the tag.
- [ ] The user has the measured gains, A4 outcome and both commit hashes.
