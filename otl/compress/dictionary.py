"""Shared instruction dictionary: REPEAT, COPY, INVERT, SEQUENCE.

Container (big-endian)::

    magic  4 bytes  b"OTL1"
    ver    1 byte   0x01
    olen   4 bytes  uncompressed length
    ops    sequence of operations

Operations::

    0x00 LIT  u8 n, n literal bytes
    0x01 REP  u8 value, u8 count          -> value repeated count times
    0x02 CPY  u16 distance, u8 n          -> n bytes from output[-distance]
    0x03 INV  u16 distance, u8 n          -> n bytes of NOT output[-distance]
    0x04 SEQ  u8 start, i8 step, u8 count -> start + k*step (mod 256)

The dictionary is "shared" in the protocol sense: transmitter and receiver use
the same versioned opcode table.  ``INV`` is included because the optical layer
deliberately transmits inverted copies of frames; structured payloads often
contain inverted repeats.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from ..config import CompressionConfig
from ..errors import CompressionError

MAGIC = b"OTL1"
VERSION = 1
HEADER = struct.Struct(">4sBI")
LIT, REP, CPY, INV, SEQ = 0x00, 0x01, 0x02, 0x03, 0x04
OP_NAMES = {LIT: "LIT", REP: "REPEAT", CPY: "COPY", INV: "INVERT", SEQ: "SEQUENCE"}


@dataclass(frozen=True)
class CompressionStats:
    original: int
    compressed: int
    ops: dict[str, int]
    ratio: float

    def to_dict(self) -> dict[str, object]:
        return {
            "original": self.original,
            "compressed": self.compressed,
            "ratio": self.ratio,
            "ops": self.ops,
        }


def _hash4(data: bytes, i: int) -> int:
    return int.from_bytes(data[i : i + 4], "big")


def _match_len(data: bytes, i: int, j: int, limit: int) -> int:
    n = 0
    while n < limit and data[i + n] == data[j + n]:
        n += 1
    return n


def _inv_match_len(data: bytes, i: int, j: int, limit: int) -> int:
    n = 0
    while n < limit and data[i + n] == (data[j + n] ^ 0xFF):
        n += 1
    return n


def _push(table: dict[int, list[int]], key: int, pos: int, keep: int = 16) -> None:
    bucket = table.get(key)
    if bucket is None:
        table[key] = [pos]
    else:
        bucket.append(pos)
        if len(bucket) > keep:
            del bucket[0]


def compress(data: bytes, cfg: CompressionConfig | None = None) -> tuple[bytes, CompressionStats]:
    cfg = cfg or CompressionConfig()
    if not data:
        out = HEADER.pack(MAGIC, VERSION, 0)
        return out, CompressionStats(0, len(out), {k: 0 for k in OP_NAMES.values()}, 1.0)

    n = len(data)
    out = bytearray(HEADER.pack(MAGIC, VERSION, n))
    literal = bytearray()
    ops = {name: 0 for name in OP_NAMES.values()}
    fwd: dict[int, list[int]] = {}
    inv: dict[int, list[int]] = {}
    inserted = 0

    def flush_literal() -> None:
        nonlocal literal
        while literal:
            chunk = literal[: cfg.max_literal]
            del literal[: len(chunk)]
            out.append(LIT)
            out.append(len(chunk))
            out.extend(chunk)
            ops["LIT"] += 1

    i = 0
    while i < n:
        # Make history [0, i) available to the matchers.
        while inserted < i:
            if inserted + 4 <= n:
                _push(fwd, _hash4(data, inserted), inserted)
                inv_key = int.from_bytes(
                    bytes(b ^ 0xFF for b in data[inserted : inserted + 4]), "big"
                )
                _push(inv, inv_key, inserted)
            inserted += 1

        best_len = 0
        best_cost = 0
        best_op: tuple[int, int, int] | None = None  # (opcode, arg1, arg2)

        # REPEAT
        run = 1
        while run < min(255, n - i) and data[i + run] == data[i]:
            run += 1
        if run >= 4 and run - 3 > best_len - best_cost:
            best_len, best_cost, best_op = run, 3, (REP, data[i], run)

        # SEQUENCE (arithmetic, non-zero step)
        if i + 1 < n:
            step = data[i + 1] - data[i]
            if step != 0:
                run = 2
                while run < min(255, n - i) and ((data[i] + run * step) & 0xFF) == data[i + run]:
                    run += 1
                if run >= 5 and run - 4 > best_len - best_cost:
                    best_len, best_cost, best_op = run, 4, (SEQ, data[i], (step & 0xFF))

        # COPY
        if i + 4 <= n:
            key = _hash4(data, i)
            for pos in reversed(fwd.get(key, [])[-8:]):
                dist = i - pos
                if not 1 <= dist <= cfg.window:
                    continue
                length = _match_len(data, i, pos, min(255, n - i))
                if length >= cfg.min_match and length - 4 > best_len - best_cost:
                    best_len, best_cost, best_op = length, 4, (CPY, dist, length)

        # INVERT
        if cfg.use_invert_op and i + 4 <= n:
            key = _hash4(data, i)
            for pos in reversed(inv.get(key, [])[-8:]):
                dist = i - pos
                if not 1 <= dist <= cfg.window:
                    continue
                length = _inv_match_len(data, i, pos, min(255, n - i))
                if length >= cfg.min_match and length - 4 > best_len - best_cost:
                    best_len, best_cost, best_op = length, 4, (INV, dist, length)

        if best_op is None or best_len <= best_cost:
            literal.append(data[i])
            i += 1
            if len(literal) >= cfg.max_literal:
                flush_literal()
            continue

        flush_literal()
        opcode, a1, a2 = best_op
        if opcode == REP:
            out.extend((REP, a1, a2))
            ops["REPEAT"] += 1
        elif opcode == SEQ:
            out.extend((SEQ, a1, a2 & 0xFF, best_len))
            ops["SEQUENCE"] += 1
        elif opcode == CPY:
            out.extend((CPY, (a1 >> 8) & 0xFF, a1 & 0xFF, a2))
            ops["COPY"] += 1
        elif opcode == INV:
            out.extend((INV, (a1 >> 8) & 0xFF, a1 & 0xFF, a2))
            ops["INVERT"] += 1
        i += best_len

    flush_literal()
    compressed = bytes(out)
    ratio = n / len(compressed) if compressed else 0.0
    return compressed, CompressionStats(n, len(compressed), ops, ratio)


def decompress(blob: bytes) -> bytes:
    if len(blob) < HEADER.size:
        raise CompressionError("compressed blob shorter than header", component="compress")
    magic, version, olen = HEADER.unpack(blob[: HEADER.size])
    if magic != MAGIC:
        raise CompressionError(
            "bad compression magic",
            component="compress",
            operation="decompress",
            magic=magic.hex(),
        )
    if version != VERSION:
        raise CompressionError(
            "unsupported compression version",
            component="compress",
            operation="decompress",
            version=version,
        )
    out = bytearray()
    i = HEADER.size
    n = len(blob)
    while i < n and len(out) < olen:
        opcode = blob[i]
        i += 1
        if opcode == LIT:
            if i >= n:
                raise CompressionError("truncated LIT", component="compress")
            count = blob[i]
            i += 1
            if count == 0 or i + count > n:
                raise CompressionError("bad LIT length", component="compress")
            out.extend(blob[i : i + count])
            i += count
        elif opcode == REP:
            if i + 2 > n:
                raise CompressionError("truncated REP", component="compress")
            value, count = blob[i], blob[i + 1]
            i += 2
            if count == 0:
                raise CompressionError("zero REP count", component="compress")
            out.extend(bytes([value]) * count)
        elif opcode in (CPY, INV):
            if i + 3 > n:
                raise CompressionError("truncated COPY/INVERT", component="compress")
            dist = (blob[i] << 8) | blob[i + 1]
            count = blob[i + 2]
            i += 3
            if dist == 0 or dist > len(out) or count == 0:
                raise CompressionError(
                    "invalid COPY/INVERT distance or length",
                    component="compress",
                    distance=dist,
                    count=count,
                    out_len=len(out),
                )
            for _ in range(count):
                src = out[-dist]
                out.append(src if opcode == CPY else (src ^ 0xFF))
        elif opcode == SEQ:
            if i + 3 > n:
                raise CompressionError("truncated SEQ", component="compress")
            start, step, count = blob[i], blob[i + 1], blob[i + 2]
            i += 3
            if count == 0:
                raise CompressionError("zero SEQ count", component="compress")
            signed_step = step - 256 if step > 127 else step
            for k in range(count):
                out.append((start + k * signed_step) & 0xFF)
        else:
            raise CompressionError(
                "unknown opcode",
                component="compress",
                operation="decompress",
                opcode=opcode,
                offset=i - 1,
            )
        if len(out) > olen:
            raise CompressionError(
                "decoder overran declared length",
                component="compress",
                operation="decompress",
                declared=olen,
                produced=len(out),
            )
    if len(out) != olen:
        raise CompressionError(
            "decompressed length mismatch",
            component="compress",
            operation="decompress",
            declared=olen,
            produced=len(out),
        )
    return bytes(out)


def manifest() -> dict[str, object]:
    return {
        "magic": MAGIC.decode(),
        "version": VERSION,
        "header_bytes": HEADER.size,
        "opcodes": {f"0x{k:02x}": v for k, v in OP_NAMES.items()},
        "notes": "Shared by transmitter and receiver; version mismatch is a hard error.",
    }
