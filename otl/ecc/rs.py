"""Clean-room Reed-Solomon over GF(256), primitive polynomial 0x11D.

The implementation is systematic: the message bytes are followed by ``nsym``
parity bytes.  It supports errors and erasures, which is what the packet layer
needs when whole frames are lost and their byte positions are known.

Only standard mathematics is used; no third-party source code was copied.
The algorithm follows the classical syndrome / Berlekamp-Massey / Chien /
Forney construction (Reed & Solomon 1960; Berlekamp 1968; Massey 1969).
"""

from __future__ import annotations

from ..errors import ECCError

GF_ORDER = 255
PRIMITIVE = 0x11D

GF_EXP = [0] * 512
GF_LOG = [0] * 256
_x = 1
for _i in range(GF_ORDER):
    GF_EXP[_i] = _x
    GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= PRIMITIVE
for _i in range(GF_ORDER, 512):
    GF_EXP[_i] = GF_EXP[_i - GF_ORDER]


def gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return GF_EXP[GF_LOG[a] + GF_LOG[b]]


def gf_div(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("GF(256) division by zero")
    if a == 0:
        return 0
    return GF_EXP[(GF_LOG[a] - GF_LOG[b]) % GF_ORDER]


def gf_pow(a: int, n: int) -> int:
    if a == 0:
        return 0
    return GF_EXP[(GF_LOG[a] * n) % GF_ORDER]


def gf_inv(a: int) -> int:
    if a == 0:
        raise ZeroDivisionError("GF(256) inverse of zero")
    return GF_EXP[GF_ORDER - GF_LOG[a]]


def gf_sub(a: int, b: int) -> int:
    return a ^ b


def poly_scale(p: list[int], x: int) -> list[int]:
    return [gf_mul(c, x) for c in p]


def poly_add(p: list[int], q: list[int]) -> list[int]:
    r = [0] * max(len(p), len(q))
    for i, c in enumerate(p):
        r[i + len(r) - len(p)] ^= c
    for i, c in enumerate(q):
        r[i + len(r) - len(q)] ^= c
    return r


def poly_mul(p: list[int], q: list[int]) -> list[int]:
    r = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        if a == 0:
            continue
        for j, b in enumerate(q):
            if b:
                r[i + j] ^= gf_mul(a, b)
    return r


def poly_eval(p: list[int], x: int) -> int:
    y = 0
    for c in p:
        y = gf_mul(y, x) ^ c
    return y


def poly_div(dividend: list[int], divisor: list[int]) -> tuple[list[int], list[int]]:
    """Polynomial division, highest-degree first.  Returns (quotient, remainder)."""
    msg_out = list(dividend)
    for i in range(len(dividend) - (len(divisor) - 1)):
        coef = msg_out[i]
        if coef != 0:
            for j in range(1, len(divisor)):
                if divisor[j] != 0:
                    msg_out[i + j] ^= gf_mul(divisor[j], coef)
    separator = -(len(divisor) - 1)
    return msg_out[:separator], msg_out[separator:]


def generator_poly(nsym: int) -> list[int]:
    g = [1]
    for i in range(nsym):
        g = poly_mul(g, [1, GF_EXP[i]])
    return g


def encode(msg: bytes, nsym: int) -> bytes:
    """Systematic RS encode.  Returns ``msg + parity`` of length len(msg)+nsym."""
    if not 0 < nsym < 255:
        raise ECCError("nsym must be in 1..254", component="ecc", operation="encode")
    if len(msg) + nsym > 255:
        raise ECCError(
            "message too long for GF(256) block",
            component="ecc",
            operation="encode",
            msg_len=len(msg),
            nsym=nsym,
        )
    gen = generator_poly(nsym)
    padded = list(msg) + [0] * nsym
    _, remainder = poly_div(padded, gen)
    if len(remainder) < nsym:
        remainder = [0] * (nsym - len(remainder)) + remainder
    return bytes(msg) + bytes(remainder[-nsym:])


def _syndromes(msg: list[int], nsym: int) -> list[int]:
    return [0] + [poly_eval(msg, GF_EXP[i]) for i in range(nsym)]


def _errata_locator(coef_pos: list[int]) -> list[int]:
    loc = [1]
    for pos in coef_pos:
        loc = poly_mul(loc, poly_add([1], [GF_EXP[pos], 0]))
    return loc


def _error_evaluator(synd: list[int], err_loc: list[int], nsym: int) -> list[int]:
    _, remainder = poly_div(poly_mul(synd, err_loc), [1] + [0] * (nsym + 1))
    return remainder


def _find_error_locator(
    synd: list[int],
    nsym: int,
    erase_loc: list[int] | None = None,
    erase_count: int = 0,
) -> list[int]:
    if erase_loc is not None:
        err_loc = list(erase_loc)
        old_loc = list(erase_loc)
    else:
        err_loc = [1]
        old_loc = [1]
    synd_shift = max(0, len(synd) - nsym)
    for i in range(nsym - erase_count):
        k = erase_count + i + synd_shift
        delta = synd[k]
        for j in range(1, len(err_loc)):
            delta ^= gf_mul(err_loc[-(j + 1)], synd[k - j])
        old_loc = old_loc + [0]
        if delta != 0:
            if len(old_loc) > len(err_loc):
                new_loc = poly_scale(old_loc, delta)
                old_loc = poly_scale(err_loc, gf_inv(delta))
                err_loc = new_loc
            err_loc = poly_add(err_loc, poly_scale(old_loc, delta))
    while len(err_loc) > 1 and err_loc[0] == 0:
        err_loc.pop(0)
    while len(err_loc) > 1 and err_loc[-1] == 0:
        err_loc.pop()
    return err_loc


def _find_errors(err_loc: list[int], nmess: int) -> list[int]:
    errs = len(err_loc) - 1
    positions: list[int] = []
    for i in range(nmess):
        if poly_eval(err_loc, GF_EXP[i]) == 0:
            positions.append(nmess - 1 - i)
    if len(positions) != errs:
        raise ECCError(
            "Chien search found the wrong number of roots",
            component="ecc",
            operation="decode",
            expected=errs,
            found=len(positions),
        )
    return positions


def _forney_syndromes(synd: list[int], pos: list[int], nmess: int) -> list[int]:
    erase_pos_reversed = [nmess - 1 - p for p in pos]
    fsynd = list(synd[1:])
    for i in range(len(pos)):
        x = GF_EXP[erase_pos_reversed[i]]
        for j in range(len(fsynd) - 1):
            fsynd[j] = gf_mul(fsynd[j], x) ^ fsynd[j + 1]
    return fsynd


def _correct_errata(msg: list[int], synd: list[int], err_pos: list[int]) -> list[int]:
    coef_pos = [len(msg) - 1 - p for p in err_pos]
    err_loc = _errata_locator(coef_pos)
    err_eval = _error_evaluator(synd[::-1], err_loc, len(err_loc) - 1)[::-1]
    x_values: list[int] = []
    for pos in coef_pos:
        x_values.append(gf_pow(2, -(GF_ORDER - pos)))
    e = [0] * len(msg)
    for i, xi in enumerate(x_values):
        xi_inv = gf_inv(xi)
        prime = 1
        for j, xj in enumerate(x_values):
            if j != i:
                prime = gf_mul(prime, gf_sub(1, gf_mul(xi_inv, xj)))
        if prime == 0:
            raise ECCError(
                "degenerate error locator",
                component="ecc",
                operation="decode",
            )
        y = poly_eval(err_eval[::-1], xi_inv)
        y = gf_mul(gf_pow(xi, 1), y)
        e[err_pos[i]] = gf_div(y, prime)
    return poly_add(msg, e)


def _solve_magnitudes(
    received: list[int],
    positions: list[int],
    synd: list[int],
    nsym: int,
) -> list[int]:
    """Solve the Vandermonde system for error magnitudes.

    ``synd`` is the output of :func:`_syndromes` (leading zero included).
    Using a linear solve avoids the coefficient-ordering pitfalls of a
    hand-rolled Forney implementation while remaining O(m^3) for m <= 32.
    """
    m = len(positions)
    if m == 0:
        return list(received)
    if m > nsym:
        raise ECCError(
            "too many error positions for magnitude solve",
            component="ecc",
            operation="decode",
            positions=m,
            nsym=nsym,
        )
    # X_j = alpha^(n-1-p_j), n=255.  With this module's syndrome convention
    # synd[k] = r(alpha^(k-1)) for k >= 1, so s_j = sum_j e_j * X_j**j and row
    # i (using s_i) carries exponent i.
    xs = [GF_EXP[(254 - p) % GF_ORDER] for p in positions]
    a: list[list[int]] = []
    b: list[int] = []
    for i in range(m):
        a.append([gf_pow(x, i) for x in xs])
        b.append(synd[i + 1])

    # Gaussian elimination over GF(256), augmented matrix.
    for col in range(m):
        pivot = next((r for r in range(col, m) if a[r][col] != 0), None)
        if pivot is None:
            raise ECCError(
                "singular error magnitude system",
                component="ecc",
                operation="decode",
            )
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            b[col], b[pivot] = b[pivot], b[col]
        inv = gf_inv(a[col][col])
        a[col] = [gf_mul(v, inv) for v in a[col]]
        b[col] = gf_mul(b[col], inv)
        for r in range(m):
            if r == col or a[r][col] == 0:
                continue
            factor = a[r][col]
            a[r] = [gf_sub(a[r][c], gf_mul(factor, a[col][c])) for c in range(m)]
            b[r] = gf_sub(b[r], gf_mul(factor, b[col]))

    corrected = list(received)
    for p, magnitude in zip(positions, b):
        corrected[p] ^= magnitude
    return corrected


def _pmul_asc(p: list[int], q: list[int]) -> list[int]:
    """Multiply polynomials given lowest-degree-first."""
    r = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        if a == 0:
            continue
        for j, b in enumerate(q):
            if b:
                r[i + j] ^= gf_mul(a, b)
    return r


def _solve_linear(rows: list[list[int]], rhs: list[int], ncols: int) -> list[int] | None:
    """Solve an over-determined GF(256) system, or return ``None``.

    ``rows`` is a list of coefficient rows; a unique consistent solution is
    returned.  A rank-deficient or inconsistent system yields ``None`` so the
    caller can try a different assumed number of errors.
    """
    m = len(rows)
    a = [list(rows[i]) + [rhs[i]] for i in range(m)]
    pivots: list[int] = []
    r = 0
    for c in range(ncols):
        p = next((i for i in range(r, m) if a[i][c] != 0), None)
        if p is None:
            continue
        a[r], a[p] = a[p], a[r]
        inv = gf_inv(a[r][c])
        a[r] = [gf_mul(v, inv) for v in a[r]]
        for i in range(m):
            if i != r and a[i][c] != 0:
                f = a[i][c]
                a[i] = [a[i][k] ^ gf_mul(f, a[r][k]) for k in range(ncols + 1)]
        pivots.append(c)
        r += 1
        if r == m:
            break
    for i in range(r, m):
        if a[i][ncols] != 0 and all(a[i][c] == 0 for c in range(ncols)):
            return None
    if len(pivots) != ncols:
        return None
    solution = [0] * ncols
    for i, c in enumerate(pivots):
        solution[c] = a[i][ncols]
    return solution


def _positions_from_locator(locator: list[int]) -> list[int]:
    """Find byte positions from an ascending locator ``1 + l1 x + ...``.

    The syndrome convention used here is ``s_k = sum_j e_j X_j**k`` with
    ``X_j = alpha**(254 - p_j)``.  An error locator ``prod(1 - X_j x)`` has a
    root at ``x = X_j**-1``, so each candidate position is tested directly.
    """
    positions: list[int] = []
    for p in range(255):
        x_inv = gf_inv(GF_EXP[(254 - p) % GF_ORDER])
        value = 1
        power = 1
        for coefficient in locator:
            power = gf_mul(power, x_inv)
            value ^= gf_mul(coefficient, power)
        if value == 0:
            positions.append(p)
    return positions


def _correct_with_erasures(
    msg: list[int],
    synd: list[int],
    nsym: int,
    erase_pos: list[int],
) -> tuple[bytes, int] | None:
    """Correct a block when some positions are known erasures.

    The erasure locator ``Gamma`` is known, so the modified syndrome
    ``M = Gamma * S mod x**nsym`` satisfies a shorter recurrence belonging to
    the *unknown* errors only.  We try every admissible number ``t`` of extra
    errors, solve the key equation for its locator, and accept the first
    candidate whose corrected codeword has all-zero syndromes.  This keeps the
    erasure capacity exactly at ``nsym`` and the mixed capacity at
    ``2*errors + erasures <= nsym``.
    """
    e = len(erase_pos)
    gamma = [1]
    for p in erase_pos:
        x_p = GF_EXP[(254 - p) % GF_ORDER]
        gamma = _pmul_asc(gamma, [1, x_p])
    modified = _pmul_asc(gamma, synd[1:])[:nsym]

    for t in range((nsym - e) // 2 + 1):
        rows: list[list[int]] = []
        rhs: list[int] = []
        for n in range(e + t, nsym):
            rows.append([modified[n - i] for i in range(1, t + 1)])
            rhs.append(modified[n])
        if t == 0:
            locator: list[int] = []
        else:
            locator = _solve_linear(rows, rhs, t)  # type: ignore[assignment]
            if locator is None:
                continue
        roots = _positions_from_locator(locator)
        if len(roots) != t or set(roots) & set(erase_pos):
            continue
        positions = sorted(set(erase_pos) | set(roots))
        try:
            corrected = _solve_magnitudes(msg, positions, synd, nsym)
        except ECCError:
            continue
        if max(_syndromes(corrected, nsym)) == 0:
            return bytes(corrected), len(positions)
    return None


def decode(codeword: bytes, nsym: int, erasures: list[int] | None = None) -> tuple[bytes, int]:
    """Correct a codeword.

    Returns ``(corrected_codeword, n_corrected_positions)``.  ``erasures`` are
    zero-based byte positions known to be unreliable (for example a frame that
    never arrived).  Raises :class:`ECCError` if the block is uncorrectable.
    """
    if len(codeword) != 255:
        raise ECCError(
            "this implementation requires a 255-byte codeword",
            component="ecc",
            operation="decode",
            length=len(codeword),
        )
    msg = list(codeword)
    erase_pos = sorted(set(erasures or []))
    if any(p < 0 or p >= 255 for p in erase_pos):
        raise ECCError("erasure position out of range", component="ecc")
    if len(erase_pos) > nsym:
        raise ECCError(
            "too many erasures",
            component="ecc",
            operation="decode",
            erasures=len(erase_pos),
            nsym=nsym,
        )
    synd = _syndromes(msg, nsym)
    if max(synd) == 0:
        return bytes(msg), 0

    if erase_pos:
        result = _correct_with_erasures(msg, synd, nsym, erase_pos)
        if result is None:
            raise ECCError(
                "uncorrectable block (erasures)",
                component="ecc",
                operation="decode",
                erasures=len(erase_pos),
            )
        return result

    fsynd = _forney_syndromes(synd, [], len(msg))
    err_loc = _find_error_locator(fsynd, nsym, None, 0)
    positions = _find_errors(err_loc[::-1], len(msg))
    if len(positions) > nsym // 2:
        raise ECCError(
            "too many error positions",
            component="ecc",
            operation="decode",
            positions=len(positions),
            nsym=nsym,
        )
    corrected = _solve_magnitudes(msg, positions, synd, nsym)
    if max(_syndromes(corrected, nsym)) != 0:
        raise ECCError(
            "uncorrectable block (syndromes remain)",
            component="ecc",
            operation="decode",
        )
    return bytes(corrected), len(positions)


def max_errors(nsym: int) -> int:
    return nsym // 2


def max_erasures(nsym: int) -> int:
    return nsym
