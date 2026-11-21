#!/usr/bin/env python3
"""Mine-tunnel kit for the corridor cells (2026-11-16).

The earlier cave cells were boxes of rock with a flat ceiling. This kit builds the
same floor plans (same doors, same colliders) as a worked mine:

- rough-hewn rock: the walls are sheets set back 0.25 m behind the collider plane and
  pushed further into the rock by noise (never toward the walkway, so the box
  colliders of the plan stay exact); the ceiling is a noisy sheet above 3.4 m;
- timber sets (two posts and a cap, with knee braces) standing in that 0.25 m strip,
  lagging boards resting on the caps;
- lanterns hanging from the caps, door frames of heavy timber, rail remnants, carts,
  crates, barrels, rubble.

Atlas: 1024 x 1024, rock on the left half (photo, shader-tiled), eight 256 px
materials on the right. Beams map a length-proportional strip of the timber region,
so the grain runs along every beam and the texel density is the same everywhere.

Lighting lines written to the manifest (dynamicworld MULTI_CELL_SPEC section 2):
`# cell.baselight:` (unlit base brightness), `# cell.fog:` (sight distance) and
`# cell.glow:` (the lantern glass region stays lit), plus the `# cell.lights:` of the
lanterns.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

from cellgen import CellBuilder, AtlasPainter
from atlas_common import rock_photo
from gen_variation_cells import collider_rects

REGIONS = {
    "rock": (0.0, 0.0, 0.5, 1.0),
    "dirt": (0.5, 0.75, 0.75, 1.0),
    "gravel": (0.75, 0.75, 1.0, 1.0),
    "timber": (0.5, 0.5, 0.75, 0.75),
    "board": (0.75, 0.5, 1.0, 0.75),
    "iron": (0.5, 0.25, 0.75, 0.5),
    "ore": (0.75, 0.25, 1.0, 0.5),
    "glow": (0.5, 0.0, 0.75, 0.25),
    "soot": (0.75, 0.0, 1.0, 0.25),
}
ATLAS = 1024
CEIL = 3.4          # nominal tunnel ceiling
OFF = 0.25          # wall sheets stand this far behind the collider plane
WALL_TOP = 4.0      # wall sheets run up into the ceiling noise
LANTERN_RGB = (1.0, 0.70, 0.40)


def _n(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


# ---------------------------------------------------------------------------
# noise
# ---------------------------------------------------------------------------
def _hash3(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 362437) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def noise3(x, y, z, seed=0):
    """Smooth value noise in 0..1."""
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    sx, sy, sz = (f * f * (3 - 2 * f) for f in (fx, fy, fz))
    v = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((sx if dx else 1 - sx) * (sy if dy else 1 - sy) * (sz if dz else 1 - sz))
                v += w * _hash3(ix + dx, iy + dy, iz + dz, seed)
    return v


def fbm(x, y, z, seed=0):
    return (0.6 * noise3(x, y, z, seed) + 0.3 * noise3(x * 2.1, y * 2.1, z * 2.1, seed + 7)
            + 0.1 * noise3(x * 4.3, y * 4.3, z * 4.3, seed + 13))


def _pp(t):
    """Ping-pong 0..1 (mirrored repeat: no seam where a tile ends)."""
    t = t % 2.0
    return t if t <= 1.0 else 2.0 - t


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b, s=1.0):
    return (a[0] + b[0] * s, a[1] + b[1] * s, a[2] + b[2] * s)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    ln = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    return (a[0] / ln, a[1] / ln, a[2] / ln) if ln > 1e-9 else (0.0, 1.0, 0.0)


class Mine:
    def __init__(self, rects, seed):
        """rects: walkable rects (x0, x1, z0, z1) = the collider plan."""
        self.b = CellBuilder(REGIONS)
        self.rects = list(rects)
        self.seed = seed
        self.rng = random.Random(seed)
        self.colliders = []
        self.lights = []
        self.flames = []    # (kind, x, y, z): '# prop:' at the flame's base
        self.extra = []

    # -- helpers --------------------------------------------------------
    def _is_open(self, x, z):
        return any(x0 < x < x1 and z0 < z < z1 for (x0, x1, z0, z1) in self.rects)

    def _flat_tri(self, p1, p2, p3, uv1, uv2, uv3, toward=None):
        n = _unit(_cross(_sub(p2, p1), _sub(p3, p1)))
        if toward is not None and (n[0] * toward[0] + n[1] * toward[1] + n[2] * toward[2]) < 0:
            p2, p3, uv2, uv3 = p3, p2, uv3, uv2
            n = (-n[0], -n[1], -n[2])
        self.b.tri(p1, p2, p3, n, n, n, uv1, uv2, uv3)

    def _region_uv(self, region, s, t):
        """s, t in 0..1 inside the region, kept 2 px off the border (mip bleed)."""
        u0, v0, u1, v1 = REGIONS[region]
        m = 2.0 / ATLAS
        return (u0 + m + (u1 - u0 - 2 * m) * s, v0 + m + (v1 - v0 - 2 * m) * t)

    def beam(self, p0, p1, w, h, region="timber", up=(0, 1, 0), ends=True):
        """Box from p0 to p1; w across (side), h along `up`. UVs take a strip of the
        region proportional to the length, so the grain follows the beam."""
        ax = _unit(_sub(p1, p0))
        side = _unit(_cross(up, ax))
        upv = _cross(ax, side)
        ln = math.sqrt(sum(c * c for c in _sub(p1, p0)))
        us = min(1.0, ln / 2.0)
        ua = self.rng.uniform(0, 1 - us)

        def corner(end, sx, sy):
            base = p1 if end else p0
            return _add(_add(base, side, sx * w / 2), upv, sy * h / 2)

        for (sa, sb, n, span) in (((1, -1), (1, 1), side, h), ((-1, 1), (-1, -1), (-side[0], -side[1], -side[2]), h),
                                  ((1, 1), (-1, 1), upv, w), ((-1, -1), (1, -1), (-upv[0], -upv[1], -upv[2]), w)):
            vs = min(1.0, span / 2.0)
            va = self.rng.uniform(0, 1 - vs)
            pts = [corner(0, *sa), corner(1, *sa), corner(1, *sb), corner(0, *sb)]
            uvs = [self._region_uv(region, ua, va), self._region_uv(region, ua + us, va),
                   self._region_uv(region, ua + us, va + vs), self._region_uv(region, ua, va + vs)]
            self._flat_tri(pts[0], pts[1], pts[2], uvs[0], uvs[1], uvs[2], toward=n)
            self._flat_tri(pts[0], pts[2], pts[3], uvs[0], uvs[2], uvs[3], toward=n)
        if ends:
            for end, n in ((0, (-ax[0], -ax[1], -ax[2])), (1, ax)):
                pts = [corner(end, -1, -1), corner(end, 1, -1), corner(end, 1, 1), corner(end, -1, 1)]
                e = 0.06
                uvs = [self._region_uv(region, 0.0, 0.0), self._region_uv(region, e, 0.0),
                       self._region_uv(region, e, e), self._region_uv(region, 0.0, e)]
                self._flat_tri(pts[0], pts[1], pts[2], uvs[0], uvs[1], uvs[2], toward=n)
                self._flat_tri(pts[0], pts[2], pts[3], uvs[0], uvs[2], uvs[3], toward=n)

    def tiled_floor(self, x0, x1, z0, z1, y, region, tile=2.0):
        """Up-facing quads, the region mirrored every `tile` metres."""
        # grid lines on multiples of `tile`: the mirrored UV turns exactly on a vertex
        def cuts(a, b):
            k0 = int(math.floor(a / tile)) + 1
            mid = [tile * k for k in range(k0, int(math.ceil(b / tile))) if a + 1e-6 < tile * k < b - 1e-6]
            return [a] + mid + [b]
        xs, zs = cuts(x0, x1), cuts(z0, z1)
        for i in range(len(xs) - 1):
            for j in range(len(zs) - 1):
                pts = [(xs[i], y, zs[j + 1]), (xs[i + 1], y, zs[j + 1]),
                       (xs[i + 1], y, zs[j]), (xs[i], y, zs[j])]
                uvs = [self._region_uv(region, _pp(p[0] / tile), _pp(p[2] / tile)) for p in pts]
                self._flat_tri(pts[0], pts[1], pts[2], uvs[0], uvs[1], uvs[2], toward=(0, 1, 0))
                self._flat_tri(pts[0], pts[2], pts[3], uvs[0], uvs[2], uvs[3], toward=(0, 1, 0))

    # -- rock -----------------------------------------------------------
    def _wall_segments(self):
        """Maximal straight wall runs of the plan: (axis, c, r0, r1, sign) where the
        wall lies on axis=c ('x' or 'z'), runs r0..r1 on the other axis, and the open
        side is at c - sign * eps. End flags say how each end meets the next wall."""
        xs = sorted({-5.0, 5.0} | {r[0] for r in self.rects} | {r[1] for r in self.rects})
        zs = sorted({-5.0, 5.0} | {r[2] for r in self.rects} | {r[3] for r in self.rects})
        nx, nz = len(xs) - 1, len(zs) - 1

        def op(i, j):
            if i < 0 or j < 0 or i >= nx or j >= nz:
                return None
            return self._is_open((xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2)

        runs = {}
        for i in range(nx):
            for j in range(nz):
                if not op(i, j):
                    continue
                for (di, dj, axis, c, sign, r0, r1) in (
                        (1, 0, "x", xs[i + 1], 1, zs[j], zs[j + 1]), (-1, 0, "x", xs[i], -1, zs[j], zs[j + 1]),
                        (0, 1, "z", zs[j + 1], 1, xs[i], xs[i + 1]), (0, -1, "z", zs[j], -1, xs[i], xs[i + 1])):
                    if op(i + di, j + dj) is False:
                        runs.setdefault((axis, c, sign), []).append((r0, r1))
        segs = []
        for (axis, c, sign), ivs in runs.items():
            ivs.sort()
            cur = list(ivs[0])
            merged = []
            for a, b in ivs[1:]:
                if abs(a - cur[1]) < 1e-9:
                    cur[1] = b
                else:
                    merged.append(tuple(cur)); cur = [a, b]
            merged.append(tuple(cur))
            for r0, r1 in merged:
                ends = []
                for r, step in ((r0, -1), (r1, 1)):
                    if abs(abs(r) - 5.0) < 1e-9:
                        ends.append("rim")
                        continue
                    # the point just past the end, on the open side of the wall line
                    q = r + step * 0.01
                    px, pz = (c - sign * 0.01, q) if axis == "x" else (q, c - sign * 0.01)
                    ends.append("convex" if self._is_open(px, pz) else "concave")
                segs.append((axis, c, r0, r1, sign, ends[0], ends[1]))
        return segs

    def rock(self, amp=0.38, step=0.5):
        heights = [0.0, 0.5, 1.05, 1.65, 2.25, 2.85, CEIL, WALL_TOP]
        for (axis, c, r0, r1, sign, e0, e1) in self._wall_segments():
            a = r0 - OFF if e0 == "concave" else (r0 + OFF if e0 == "convex" else r0)
            b = r1 + OFF if e1 == "concave" else (r1 - OFF if e1 == "convex" else r1)
            if b - a < 0.05:
                continue
            n = max(1, int(math.ceil((b - a) / step)))
            grid = []
            for k in range(n + 1):
                s = a + (b - a) * k / n
                env = max(0.0, min(1.0, min(s - a, b - s) / 0.5))
                col = []
                for hi, y in enumerate(heights):
                    js = jy = 0.0
                    if 0 < k < n:
                        js = (noise3(s * 3.1, y * 2.7, c * 1.3, self.seed + 31) - 0.5) * 0.16
                    if 0 < hi < len(heights) - 1:
                        jy = (noise3(s * 2.3, y * 3.3, c * 1.7, self.seed + 57) - 0.5) * 0.14
                    ss, yy = s + js, y + jy
                    px, pz = (c, ss) if axis == "x" else (ss, c)
                    d = OFF + amp * env * fbm(px * 0.9, yy * 0.9, pz * 0.9, self.seed)
                    # undercut a little near the floor, lean in near the top
                    d += 0.06 * env * (1.0 - min(1.0, yy / 0.6))
                    pos = (c + sign * d, yy, ss) if axis == "x" else (ss, yy, c + sign * d)
                    uv = self._region_uv("rock", _pp(ss / 2.0), _pp(yy / 2.0))
                    col.append((pos, uv))
                grid.append(col)
            toward = (-sign, 0, 0) if axis == "x" else (0, 0, -sign)
            for k in range(n):
                for hi in range(len(heights) - 1):
                    p00, p10, p11, p01 = grid[k][hi], grid[k + 1][hi], grid[k + 1][hi + 1], grid[k][hi + 1]
                    if (k + hi) % 2:
                        tris = ((p00, p10, p11), (p00, p11, p01))
                    else:
                        tris = ((p00, p10, p01), (p10, p11, p01))
                    for t in tris:
                        self._flat_tri(t[0][0], t[1][0], t[2][0], t[0][1], t[1][1], t[2][1], toward=toward)
        # ceiling: one noisy sheet over the whole cell (the walls run up into it)
        m = 10
        pts = [[None] * (m + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            for j in range(m + 1):
                x, z = -5.0 + i, -5.0 + j
                if 0 < i < m:
                    x += (noise3(x * 1.7, 0.3, z * 1.9, self.seed + 3) - 0.5) * 0.5
                if 0 < j < m:
                    z += (noise3(x * 1.9, 0.7, z * 1.7, self.seed + 5) - 0.5) * 0.5
                y = CEIL + 0.04 + 0.42 * fbm(x * 0.8, 5.0, z * 0.8, self.seed + 11)
                pts[i][j] = ((x, y, z), self._region_uv("rock", _pp(x / 2.0), _pp(z / 2.0)))
        for i in range(m):
            for j in range(m):
                cx, cz = -4.5 + i, -4.5 + j
                # skip ceiling far inside solid rock (nothing below it is open)
                if not any(self._is_open(cx + dx, cz + dz) for dx in (-1.2, 0, 1.2) for dz in (-1.2, 0, 1.2)):
                    continue
                q = (pts[i][j], pts[i + 1][j], pts[i + 1][j + 1], pts[i][j + 1])
                tris = ((q[0], q[1], q[2]), (q[0], q[2], q[3])) if (i + j) % 2 else ((q[0], q[1], q[3]), (q[1], q[2], q[3]))
                for t in tris:
                    self._flat_tri(t[0][0], t[1][0], t[2][0], t[0][1], t[1][1], t[2][1], toward=(0, -1, 0))
        # wall colliders: the plan itself
        for (x0, x1, z0, z1) in collider_rects(self.rects):
            self.colliders.append(((x0 + x1) / 2, 2.0, (z0 + z1) / 2, x1 - x0, 4.0, z1 - z0))

    def pillar(self, x0, x1, z0, z1):
        """Flat-faced rock block on the collider planes. Needed where the plan leaves
        rock thinner than about 1.2 m: the wall sheets of its two sides are set back
        past each other there and would open a hole."""
        self.b.box(((x0 + x1) / 2, WALL_TOP / 2, (z0 + z1) / 2), (x1 - x0, WALL_TOP, z1 - z0), "rock",
                   skip=("bottom", "top"))

    def floor(self):
        self.tiled_floor(-5, 5, -5, 5, 0.0, "dirt")

    def worn(self, x0, x1, z0, z1):
        """Gravel strip on the dirt (the walked line)."""
        self.tiled_floor(x0, x1, z0, z1, 0.012, "gravel")

    # -- timbering ------------------------------------------------------
    def _lat(self, axis, pos, a):
        """Point at running coordinate pos, lateral coordinate a (corridor along axis)."""
        return (a, pos) if axis == "z" else (pos, a)

    def timber_set(self, axis, pos, a0, a1, braces=True, left=True, right=True):
        """Posts and cap across a corridor that runs along `axis` ('z' or 'x') at
        running coordinate pos; a0 < a1 are the collider planes of its two walls."""
        r = self.rng
        cap_y = 3.16
        for side, a, on in ((-1, a0, left), (1, a1, right)):
            if not on:
                continue
            ap = a + side * 0.115
            x, z = self._lat(axis, pos, ap)
            assert not self._is_open(x, z), f"post in the walkway at {(x, z)}"
            lean = r.uniform(-0.03, 0.03)
            tx, tz = self._lat(axis, pos + lean, ap)
            self.beam((x, 0.0, z), (tx, 3.06, tz), 0.2, 0.2, up=(1, 0, 0) if axis == "z" else (0, 0, 1))
            if braces:
                bx0, bz0 = self._lat(axis, pos, a - side * 0.0)
                bx1, bz1 = self._lat(axis, pos, a - side * 0.52)
                self.beam((bx0, 2.52, bz0), (bx1, 3.06, bz1), 0.1, 0.1,
                          up=(0, 0, 1) if axis == "z" else (1, 0, 0))
        e0 = a0 - (0.36 if left else 0.0)
        e1 = a1 + (0.36 if right else 0.0)
        x0, z0 = self._lat(axis, pos, e0)
        x1, z1 = self._lat(axis, pos, e1)
        tilt = r.uniform(-0.02, 0.02)
        self.beam((x0, cap_y + tilt, z0), (x1, cap_y - tilt, z1), 0.24, 0.22)

    def lagging(self, axis, p0, p1, a0, a1, keep=0.75):
        """Boards on top of the caps between two sets, across a0..a1."""
        r = self.rng
        a = a0 - 0.2
        while a < a1 + 0.2:
            w = r.uniform(0.2, 0.3)
            if r.random() < keep:
                c = a + w / 2
                y = 3.295 + r.uniform(0.0, 0.03)
                x0, z0 = self._lat(axis, p0 - 0.14 - r.uniform(0, 0.1), c)
                x1, z1 = self._lat(axis, p1 + 0.14 + r.uniform(0, 0.1), c + r.uniform(-0.03, 0.03))
                self.beam((x0, y, z0), (x1, y + r.uniform(-0.015, 0.015), z1), w, 0.04, region="board")
            a += w + r.uniform(0.04, 0.12)

    def flame(self, kind, base, light, rgb, intensity, flicker):
        """Register a flame: a `# prop:` at the flame's base (the host pool draws
        the flame, ADR 0015), plus the analytic light derived from it (the
        cells-side rule: a flame is a point light at the fixture's glow centre)."""
        self.flames.append((kind, base[0], base[1], base[2]))
        self.lights.append((light[0], light[1], light[2], rgb[0], rgb[1], rgb[2], intensity, flicker))

    def lantern(self, x, z, top=3.05, intensity=2.0, flicker=0.35):
        """Lantern on a chain; `top` is where the chain is fixed (cap underside or the
        ceiling). The body hangs at 2.4..2.7 m, above head height. The cage is
        open (posts, cap, base plate) so the prop flame shows through; with an
        old loader the empty cage is what shows."""
        b = self.b
        self.beam((x, top + 0.02, z), (x, 2.72, z), 0.022, 0.022, region="iron", up=(1, 0, 0), ends=False)
        b.box((x, 2.70, z), (0.2, 0.035, 0.2), "iron")
        b.cylinder((x, 2.75, z), 0.1, 0.03, 0.07, 6, "iron", cap=False)
        for px in (-0.07, 0.07):
            for pz in (-0.07, 0.07):
                b.box((x + px, 2.56, z + pz), (0.022, 0.26, 0.022), "iron")
        b.box((x, 2.42, z), (0.17, 0.03, 0.17), "iron")
        self.flame("lantern", (x, 2.435, z), (x, 2.56, z), LANTERN_RGB, intensity, flicker)

    def door(self, face):
        """Heavy timber frame around the 2 m x 3 m opening at a face centre, with the
        rock that closes the arm around it. Everything stays 2 cm inside the rim."""
        b = self.b
        s = 1 if face in ("N", "E") else -1
        d = 4.83 * s

        def P(lat, y, depth=0.0):
            return (lat, y, d + depth) if face in ("N", "S") else (d + depth, y, lat)

        def box(lat, y, wl, hy, region, depth=0.3, skip=()):
            size = (wl, hy, depth) if face in ("N", "S") else (depth, hy, wl)
            b.box(P(lat, y), size, region, skip=skip)

        for sd in (-1, 1):
            self.beam(P(sd * 1.15, 0.0), P(sd * 1.15, 3.02), 0.3, 0.3,
                      up=(1, 0, 0) if face in ("N", "S") else (0, 0, 1))
            box(sd * 1.54, 2.0, 0.48, 4.0, "rock", skip=("bottom", "top"))
            c = P(sd * 1.25, 1.5)
            size = (0.5, 3.0, 0.3) if face in ("N", "S") else (0.3, 3.0, 0.5)
            self.colliders.append((c[0], c[1], c[2], size[0], size[1], size[2]))
        self.beam(P(-1.5, 3.19), P(1.5, 3.19), 0.34, 0.36)
        box(0, 3.69, 2.6, 0.64, "rock", skip=("top",))
        # threshold board
        self.beam(P(-1.0, 0.02), P(1.0, 0.02), 0.26, 0.05, region="board")

    # -- props ----------------------------------------------------------
    def rails(self, axis, c, r0, r1, gauge=0.6, missing=()):
        """Rail remnant along `axis` centred on lateral c, from r0 to r1."""
        k = 0
        p = r0 + 0.2
        while p < r1 - 0.1:
            if k not in missing:
                x0, z0 = self._lat(axis, p + self.rng.uniform(-0.04, 0.04), c - 0.52)
                x1, z1 = self._lat(axis, p + self.rng.uniform(-0.04, 0.04), c + 0.52)
                self.beam((x0, 0.035, z0), (x1, 0.035, z1), 0.16, 0.07)
            p += 0.66
            k += 1
        for sd in (-1, 1):
            x0, z0 = self._lat(axis, r0, c + sd * gauge / 2)
            x1, z1 = self._lat(axis, r1, c + sd * gauge / 2)
            self.beam((x0, 0.105, z0), (x1, 0.105, z1), 0.05, 0.07, region="iron")

    def cart(self, x, z, ry=0.0, load=True):
        """Ore cart (body 0.8 x 0.55 x 1.2) standing on the rails."""
        b = self.b
        rot = (0, ry, 0)
        b.box((x, 0.58, z), (0.8, 0.5, 1.2), "iron", rot=rot)
        b.box((x, 0.84, z), (0.86, 0.05, 1.26), "iron", rot=rot)
        b.box((x, 0.30, z), (0.5, 0.08, 1.0), "timber", rot=rot)
        a = math.radians(ry)
        for dz in (-0.38, 0.38):
            for dx in (-0.3, 0.3):
                wx = x + dx * math.cos(a) + dz * math.sin(a)
                wz = z - dx * math.sin(a) + dz * math.cos(a)
                b.cylinder((wx, 0.2, wz), 0.14, 0.14, 0.06, 8, "iron", rot=(0, ry, 90))
        if load:
            r = random.Random(self.seed + int(x * 10) + int(z * 7))
            for _ in range(5):
                b.sphere((x + r.uniform(-0.22, 0.22), 0.9 + r.uniform(0, 0.08), z + r.uniform(-0.4, 0.4)),
                         r.uniform(0.13, 0.2), 6, 4, "ore" if r.random() < 0.5 else "rock",
                         squash=(1, 0.7, 1), jitter=0.25, rng=r)
        w, d = (0.86, 1.26) if abs(math.cos(a)) > 0.7 else (1.26, 0.86)
        self.colliders.append((x, 0.45, z, w, 0.9, d))

    def crate(self, x, z, s=0.6, ry=0.0, y=0.0, collider=True):
        self.b.box((x, y + s / 2, z), (s, s, s), "board", rot=(0, ry, 0),
                   skip=("bottom",) if y == 0 else ())
        for dy in (0.08, s - 0.08):
            self.b.box((x, y + dy, z), (s + 0.04, 0.07, s + 0.04), "timber", rot=(0, ry, 0))
        if collider:
            e = s * (1.0 + 0.35 * abs(math.sin(math.radians(2 * ry))))
            self.colliders.append((x, y + s / 2, z, e, s, e))

    def barrel(self, x, z, collider=True):
        b = self.b
        b.cylinder((x, 0.42, z), 0.26, 0.26, 0.84, 10, "board")
        b.cylinder((x, 0.42, z), 0.3, 0.3, 0.36, 10, "board", cap=False)
        for y in (0.16, 0.68):
            b.cylinder((x, y, z), 0.285, 0.285, 0.05, 10, "iron", cap=False)
        if collider:
            self.colliders.append((x, 0.42, z, 0.56, 0.84, 0.56))

    def rubble(self, pts, ore=0.25, rmin=0.12, rmax=0.3):
        r = random.Random(self.seed + 99)
        for x, z in pts:
            rad = r.uniform(rmin, rmax)
            self.b.sphere((x, rad * 0.45, z), rad, 7, 5, "ore" if r.random() < ore else "rock",
                          squash=(1, 0.65, 1), jitter=0.3, rng=r)

    def heap(self, x, z, n=7, spread=0.5):
        r = random.Random(self.seed + int(x * 13) + int(z * 17))
        self.rubble([(x + r.uniform(-spread, spread), z + r.uniform(-spread, spread)) for _ in range(n)],
                    ore=0.35, rmin=0.14, rmax=0.34)

    def pickaxe(self, x, z, dx, dz):
        """Leaning against a wall: (x, z) is the foot, (dx, dz) points at the wall."""
        top = (x + dx * 0.32, 0.86, z + dz * 0.32)
        self.beam((x, 0.0, z), top, 0.04, 0.04)
        px, pz = -dz, dx
        self.beam((top[0] - px * 0.26, 0.84, top[2] - pz * 0.26), (top[0] + px * 0.26, 0.84, top[2] + pz * 0.26),
                  0.05, 0.06, region="iron")

    def planks(self, x, z, axis="z", n=4, length=2.0):
        for k in range(n):
            y = 0.03 + 0.055 * k
            o = self.rng.uniform(-0.08, 0.08)
            x0, z0 = self._lat(axis, -length / 2, o)
            x1, z1 = self._lat(axis, length / 2, o + self.rng.uniform(-0.05, 0.05))
            self.beam((x + x0, y, z + z0), (x + x1, y, z + z1), 0.24, 0.05, region="board")

    # -- output ---------------------------------------------------------
    def manifest(self, name, doors, base=0.12, fog=(3.0, 10.0)):
        assert len(self.lights) <= 4, "the shader takes at most 4 lights"
        lx, ly, lz = self.lights[0][:3]
        props = [f"# prop: {k}, {_n(x)},{_n(y)},{_n(z)}" for (k, x, y, z) in self.flames]
        lines = [
            f"# cell.name: {name}",
            "# cell.version: 0",
            "# cell.ambient: 0.62,0.55,0.46,0.5",
            "# cell.lightvolume: 0.55,0.45,0.34,0.3",
            f"# cell.keylight: 1,0.7,0.4,2 ; {_n(lx)},{_n(ly)},{_n(lz)}",
            f"# cell.baselight: {_n(base)}",
            f"# cell.fog: {_n(fog[0])}, {_n(fog[1])}",
            "# cell.lights: " + " ; ".join(
                f"{_n(x)},{_n(y)},{_n(z)}, {_n(r)},{_n(g)},{_n(bb)},{_n(i)},{_n(f)}"
                for (x, y, z, r, g, bb, i, f) in self.lights),
            *props,
            "# cell.tiling: rock, 2, 0,0,0.5,1",
            "# cell.glow: " + ",".join(_n(v) for v in REGIONS["glow"]) + ", 1.3",
            f"# cell.tris: {len(self.b.faces)}",
        ]
        lines += [f"# door: {d}" for d in doors]
        lines += self.extra
        lines += ["# collider: " + ",".join(_n(v) for v in c[:3]) + ", " + ",".join(_n(v) for v in c[3:6])
                  + ("" if len(c) < 9 else ", " + ",".join(_n(v) for v in c[6:9]))
                  for c in self.colliders]
        return lines


# ---------------------------------------------------------------------------
# atlas
# ---------------------------------------------------------------------------
def _field(rng, w, h, cx, cy, blur=0.0):
    small = Image.new("L", (max(1, cx), max(1, cy)))
    small.putdata([rng.randint(0, 255) for _ in range(max(1, cx) * max(1, cy))])
    img = small.resize((w, h), Image.BICUBIC)
    return img.filter(ImageFilter.GaussianBlur(blur)) if blur else img


def _shade(base, fields, lo=0.55, hi=1.25):
    """base colour modulated by the weighted sum of L fields."""
    w, h = fields[0][0].size
    out = Image.new("RGB", (w, h))
    px = out.load()
    fl = [(f.load(), wt) for f, wt in fields]
    tot = sum(wt for _, wt in fl)
    for y in range(h):
        for x in range(w):
            v = sum(f[x, y] * wt for f, wt in fl) / (255.0 * tot)
            k = lo + (hi - lo) * v
            px[x, y] = tuple(max(0, min(255, int(c * k))) for c in base)
    return out


def _paste(p, name, tile):
    x0, y0, x1, y1 = (int(round(v)) for v in p.px(name))
    p.img.paste(tile.resize((x1 - x0, y1 - y0)), (x0, y0))


def make_atlas(path, seed):
    rng = random.Random(seed)
    p = AtlasPainter(ATLAS, REGIONS, seed=seed)
    rock_photo(p)
    S = 256

    # dirt: packed earth with pebbles
    t = _shade((92, 74, 54), [(_field(rng, S, S, 6, 6), 0.5), (_field(rng, S, S, 24, 24), 0.3),
                              (_field(rng, S, S, 96, 96), 0.2)], 0.6, 1.2)
    d = ImageDraw.Draw(t)
    for _ in range(260):
        x, y, r = rng.uniform(0, S), rng.uniform(0, S), rng.uniform(0.8, 3.2)
        g = rng.randint(-26, 30)
        d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=(98 + g, 84 + g, 68 + g))
    _paste(p, "dirt", t)

    # gravel: crushed stone
    t = _shade((98, 84, 66), [(_field(rng, S, S, 8, 8), 0.5), (_field(rng, S, S, 48, 48), 0.5)], 0.65, 1.15)
    d = ImageDraw.Draw(t)
    for _ in range(900):
        x, y, r = rng.uniform(0, S), rng.uniform(0, S), rng.uniform(1.5, 5.5)
        g = rng.randint(-26, 26)
        col = (106 + g, 94 + g, 78 + g)
        d.ellipse([x - r, y - r * 0.75, x + r, y + r * 0.75], fill=col)
        d.arc([x - r, y - r * 0.75, x + r, y + r * 0.75], 20, 160, fill=tuple(max(0, c - 40) for c in col))
    _paste(p, "gravel", t)

    def wood(base, lo, hi, knots, cracks, plank_lines=0):
        t = _shade(base, [(_field(rng, S, S, 3, 64, 0.6), 0.45), (_field(rng, S, S, 6, 128), 0.35),
                          (_field(rng, S, S, 40, 40), 0.2)], lo, hi)
        d = ImageDraw.Draw(t)
        for _ in range(cracks):
            y, x = rng.uniform(0, S), rng.uniform(0, S)
            ln = rng.uniform(20, 110)
            d.line([x, y, x + ln, y + rng.uniform(-2, 2)], fill=tuple(int(c * 0.45) for c in base), width=1)
        for _ in range(knots):
            x, y, r = rng.uniform(0, S), rng.uniform(0, S), rng.uniform(3, 7)
            d.ellipse([x - r * 1.6, y - r, x + r * 1.6, y + r], fill=tuple(int(c * 0.55) for c in base))
            d.ellipse([x - r * 0.8, y - r * 0.5, x + r * 0.8, y + r * 0.5], fill=tuple(int(c * 0.38) for c in base))
        for k in range(1, plank_lines):
            y = S * k / plank_lines + rng.uniform(-2, 2)
            d.line([0, y, S, y], fill=tuple(int(c * 0.3) for c in base), width=2)
        return t

    _paste(p, "timber", wood((88, 60, 38), 0.6, 1.2, 5, 26))
    _paste(p, "board", wood((112, 92, 68), 0.62, 1.15, 7, 34, plank_lines=4))

    # iron: dark, pitted, rusty
    t = _shade((60, 54, 50), [(_field(rng, S, S, 10, 10), 0.6), (_field(rng, S, S, 64, 64), 0.4)], 0.65, 1.2)
    rust = _field(rng, S, S, 9, 9, 1.0).load()
    px = t.load()
    for y in range(S):
        for x in range(S):
            k = 0.55 * max(0.0, min(1.0, (rust[x, y] - 150) / 80.0))
            if k > 0:
                c = px[x, y]
                px[x, y] = (int(c[0] + (104 - c[0]) * k), int(c[1] + (64 - c[1]) * k), int(c[2] + (42 - c[2]) * k))
    _paste(p, "iron", t)

    # ore: dark stone with dull metallic flecks
    t = _shade((66, 60, 56), [(_field(rng, S, S, 7, 7), 0.5), (_field(rng, S, S, 40, 40), 0.5)], 0.6, 1.25)
    d = ImageDraw.Draw(t)
    for _ in range(170):
        x, y, r = rng.uniform(0, S), rng.uniform(0, S), rng.uniform(1.0, 3.6)
        d.polygon([(x - r, y), (x, y - r * 0.7), (x + r, y + r * 0.2), (x, y + r * 0.8)],
                  fill=rng.choice([(176, 142, 74), (150, 120, 66), (198, 168, 96)]))
    _paste(p, "ore", t)

    # glow: lantern glass
    t = Image.new("RGB", (S, S))
    px = t.load()
    for y in range(S):
        for x in range(S):
            r = math.hypot(x - S / 2, y - S / 2) / (S * 0.72)
            k = max(0.0, 1.0 - r)
            px[x, y] = (255, int(150 + 95 * k), int(40 + 150 * k * k))
    _paste(p, "glow", t)

    _paste(p, "soot", _shade((30, 27, 25), [(_field(rng, S, S, 12, 12), 1.0)], 0.6, 1.3))
    p.save(path)
