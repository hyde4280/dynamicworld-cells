#!/usr/bin/env python3
"""Variation pattern cells, cave-dungeon style (2026-11-13).

cell014 offset cross (N/E/S/W): same door layout as cell006 (doors at
face centres, 2m x 3m openings, 3m-wide corridors), but the internal
corridor path jogs sideways, so opposite doors are NOT visible from
each other:

- The N-S path runs down the north arm (centred), crosses an east-side
  plaza, descends in a band at x in [1.5, 4.0], and returns to the
  centred south arm. At z = -1 the only corridor is that band
  (x >= 1.5), so every N-door -> S-door sight line crosses rock.
- The E-W path leaves the west face centred, jogs north around the
  plaza, and reaches the east arm via the plaza / band. At x = -0.25
  the only corridor is the north arm (z >= 1), so every E-door ->
  W-door sight line crosses rock.

Rock is the exact complement of the corridor union: the plane is
subdivided on every corridor-rect edge, rock cells are merged
greedily, so no two rock boxes overlap and no face is duplicated
(the cell006-009 Z-fight rules still hold). Only rock boxes that
touch the corridor get colliders.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atlas_common import REGIONS_HALF, make_atlas_rock
from gen_basic_cells import Cave


# corridor rects (x0, x1, z0, z1), file coords: N = +Z
CORRIDORS = [
    (-1.5, 1.5, 1.0, 5.0),    # N arm (centred at the face)
    (0.0, 4.0, 0.0, 2.0),     # north plaza (east-shifted)
    (1.5, 4.0, -3.0, 0.5),    # descent band (east side)
    (0.0, 4.0, -4.0, -2.5),   # south plaza (east-shifted)
    (-1.5, 1.5, -5.0, -2.5),  # S arm (centred at the face)
    (1.3, 5.0, -1.5, 1.5),    # E arm (centred at the face)
    (-5.0, -3.0, -1.5, 1.5),  # W arm, face part (centred)
    (-3.5, -0.5, 0.0, 3.0),   # W arm, jog part (north)
]


def _inside(rects, x, z):
    return any(x0 - 1e-9 <= x <= x1 + 1e-9 and z0 - 1e-9 <= z <= z1 + 1e-9
               for (x0, x1, z0, z1) in rects)


def rock_complement(corridors):
    """Tile [-5,5]^2 minus the corridor union into merged rock rects.
    Returns (rect, touches_corridor) pairs."""
    xs = sorted({-5.0, 5.0} | {r[0] for r in corridors} | {r[1] for r in corridors})
    zs = sorted({-5.0, 5.0} | {r[2] for r in corridors} | {r[3] for r in corridors})
    rock = {}   # (i, j) -> True for elementary rock cells
    touch = {}
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            cx = (xs[i] + xs[i + 1]) / 2
            cz = (zs[j] + zs[j + 1]) / 2
            if not _inside(corridors, cx, cz):
                rock[(i, j)] = True
    # an elementary rock cell touches the corridor iff a sample point
    # just outside one of its four edges lands inside the corridor union
    for (i, j) in rock:
        cx = (xs[i] + xs[i + 1]) / 2
        cz = (zs[j] + zs[j + 1]) / 2
        eps = 0.01
        touch[(i, j)] = any(_inside(corridors, px, pz) for px, pz in
                            ((cx - (xs[i + 1] - xs[i]) / 2 - eps, cz),
                             (cx + (xs[i + 1] - xs[i]) / 2 + eps, cz),
                             (cx, cz - (zs[j + 1] - zs[j]) / 2 - eps),
                             (cx, cz + (zs[j + 1] - zs[j]) / 2 + eps)))
    # merge horizontally within each z-strip
    merged = []
    used = set()
    for j in range(len(zs) - 1):
        i = 0
        while i < len(xs) - 1:
            if (i, j) in rock:
                i1 = i
                t = touch[(i, j)]
                while i1 + 1 < len(xs) - 1 and (i1 + 1, j) in rock:
                    i1 += 1
                    t = t or touch[(i1, j)]
                merged.append([xs[i], xs[i1 + 1], zs[j], zs[j + 1], t,
                               {(k, j) for k in range(i, i1 + 1)}])
                used |= {(k, j) for k in range(i, i1 + 1)}
                i = i1 + 1
            else:
                i += 1
    # merge vertically: same x-range in adjacent z-strips
    changed = True
    while changed:
        changed = False
        for a in range(len(merged)):
            for b in range(len(merged)):
                if a == b:
                    continue
                ra, rb = merged[a], merged[b]
                if ra[0] == rb[0] and ra[1] == rb[1] and abs(ra[3] - rb[2]) < 1e-9:
                    ra[3] = rb[3]
                    ra[4] = ra[4] or rb[4]
                    ra[5] |= rb[5]
                    merged.pop(b)
                    changed = True
                    break
            if changed:
                break
    return [(r[0], r[1], r[2], r[3], r[4]) for r in merged]


def collider_rects(corridors):
    """Greedy maximal rectangles over wall-adjacent rock cells (rock
    cells next to the corridor). Rectangles may extend over rock that
    does not touch the corridor (it is inside solid rock anyway), but
    never into the corridor. Keeps the count inside the 16 pool."""
    xs = sorted({-5.0, 5.0} | {r[0] for r in corridors} | {r[1] for r in corridors})
    zs = sorted({-5.0, 5.0} | {r[2] for r in corridors} | {r[3] for r in corridors})
    nx, nz = len(xs) - 1, len(zs) - 1

    def is_rock(i, j):
        return not _inside(corridors, (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2)

    def is_wall(i, j):
        if not is_rock(i, j):
            return False
        eps = 0.01
        cx, cz = (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
        return any(_inside(corridors, px, pz) for px, pz in
                   ((xs[i] - eps, cz), (xs[i + 1] + eps, cz),
                    (cx, zs[j] - eps), (cx, zs[j + 1] + eps)))

    def greedy(i_order, j_order, x_first):
        covered = [[False] * nz for _ in range(nx)]
        rects = []
        for j in j_order:
            for i in i_order:
                if not is_wall(i, j) or covered[i][j]:
                    continue
                i0 = i1 = i
                j0 = j1 = j

                def grow_x():
                    nonlocal i0, i1
                    while i1 + 1 < nx and all(is_rock(i1 + 1, b) for b in range(j0, j1 + 1)):
                        i1 += 1
                    while i0 - 1 >= 0 and all(is_rock(i0 - 1, b) for b in range(j0, j1 + 1)):
                        i0 -= 1

                def grow_z():
                    nonlocal j0, j1
                    while j1 + 1 < nz and all(is_rock(a, j1 + 1) for a in range(i0, i1 + 1)):
                        j1 += 1
                    while j0 - 1 >= 0 and all(is_rock(a, j0 - 1) for a in range(i0, i1 + 1)):
                        j0 -= 1

                if x_first:
                    grow_x(); grow_z(); grow_x()
                else:
                    grow_z(); grow_x(); grow_z()
                for a in range(i0, i1 + 1):
                    for b in range(j0, j1 + 1):
                        covered[a][b] = True
                rects.append((xs[i0], xs[i1 + 1], zs[j0], zs[j1 + 1]))
        return rects

    best = None
    for i_order in (list(range(nx)), list(reversed(range(nx)))):
        for j_order in (list(range(nz)), list(reversed(range(nz)))):
            for x_first in (True, False):
                r = greedy(i_order, j_order, x_first)
                if best is None or len(r) < len(best):
                    best = r
    return best


def cell014():
    c = Cave(REGIONS_HALF)
    c.floor_slab()
    for (x0, x1, z0, z1, touches) in rock_complement(CORRIDORS):
        c.rock_block(x0, x1, z0, z1, collider=False)
    for (x0, x1, z0, z1) in collider_rects(CORRIDORS):
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        c.colliders.append((cx, 2.0, cz, x1 - x0, 4.0, z1 - z0))
    for (x0, x1, z0, z1) in CORRIDORS:
        c.corridor(x0, x1, z0, z1)
    for f in "NESW":
        c.door(f)
    c.lantern(2.6, 2.0, 0, -1)    # north wall of the north plaza
    c.lantern(2.6, -4.0, 0, 1)    # south wall of the south plaza
    c.tiling = ("rock", 2.0, REGIONS_HALF["rock"])
    c.stalactites([(0, 3.5), (2.6, 0.9), (2.6, -2.2), (-4.0, 0.7), (0, -3.6)])
    c.stalagmites([(-1.2, 3.6), (3.75, -1.6), (1.2, -4.3)])
    c.crystals(3.55, 1.55)
    c.rubble([(1.35, 4.4), (-2.9, 2.6), (3.7, -3.7)])
    return c, c.manifest("kuichigai-jujiro-doukutsu", "0.66,0.60,0.50,0.5",
                         "1.0,0.72,0.42,2.0 ; 2.6,2.16,1.22", ["N", "E", "S", "W"])


# ---------------------------------------------------------------------------
# cell015: organic ("gunyagunya") I-corridor. The corridor is a tube whose
# cross-section morphs from a noise-carved arch (middle) to the standard
# 3m x 3m rectangle at both faces, so door dressing, gates and colliders
# stay standard. Carving only ever recedes INTO the rock (the corridor
# never gets narrower than the nominal 3m), so per-segment box colliders
# derived from the sampled profile stay exact.
# ---------------------------------------------------------------------------
import math

_ARCH = [(-1.5, 0.0), (-1.5, 1.0), (-1.5, 2.0), (-1.44, 2.7), (-1.08, 3.25),
         (-0.55, 3.52), (0.0, 3.62), (0.55, 3.52), (1.08, 3.25), (1.44, 2.7),
         (1.5, 2.0), (1.5, 1.0), (1.5, 0.0)]
_RECT = [(-1.5, 0.0), (-1.5, 1.0), (-1.5, 2.0), (-1.5, 2.55), (-1.5, 3.0),
         (-0.75, 3.0), (0.0, 3.0), (0.75, 3.0), (1.5, 3.0), (1.5, 2.55),
         (1.5, 2.0), (1.5, 1.0), (1.5, 0.0)]


def _noise(a, b):
    return (math.sin(a) * 0.55 + math.sin(a * 2.33 + b * 1.31) * 0.30
            + math.sin(a * 4.71 - b * 2.17) * 0.15)


def _carve_wall(z, y, phase):
    return 0.55 * (0.5 + 0.5 * _noise(z * 0.85 + phase, y * 0.75))


def _carve_ceil(z, x):
    return 0.35 * (0.5 + 0.5 * _noise(z * 0.8 + 7.3, x * 0.9))


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _ring(z):
    """Cross-section profile (13 pts, west floor -> east floor) at z."""
    m = _smooth((abs(z) - 3.8) / 1.2)
    pts = []
    for i, (ax, ay) in enumerate(_ARCH):
        cx, cy = ax, ay
        if abs(ax) >= 1.08 and ay <= 2.7:            # walls / shoulders
            phase = 0.0 if ax < 0 else 3.9
            c = _carve_wall(z, ay, phase) * (1 - m)
            cx += math.copysign(c * (1.0 if ay <= 2.0 else 0.75), ax)
            if ay > 2.0:
                cy += _carve_ceil(z, ax) * (1 - m) * 0.5
        elif ay >= 3.25:                              # ceiling
            cy += _carve_ceil(z, ax) * (1 - m)
        rx, ry = _RECT[i]
        pts.append((cx + (rx - cx) * m, cy + (ry - cy) * m))
    return pts


def _wall_x(z, y, side):
    """Wall surface x at height y on the given side (-1 west, +1 east),
    interpolated from the ring profile (wall band only)."""
    pts = _ring(z)
    chain = [(px, py) for (px, py) in pts if px * side > 0 or px == 0]
    chain = [(px, py) for (px, py) in pts if (px < 0) == (side < 0)]
    chain.sort(key=lambda p: p[1])
    for (x0, y0), (x1, y1) in zip(chain, chain[1:]):
        if y0 <= y <= y1 and y1 > y0:
            return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    return chain[-1][0]


def _emit_tri(b, p1, p2, p3, n1, n2, n3, uv1, uv2, uv3):
    ux, uy, uz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
    vx, vy, vz = p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]
    gx, gy, gz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    mx, my, mz = (n1[0] + n2[0] + n3[0]), (n1[1] + n2[1] + n3[1]), (n1[2] + n2[2] + n3[2])
    if gx * mx + gy * my + gz * mz < 0:
        p2, p3, n2, n3, uv2, uv3 = p3, p2, n3, n2, uv3, uv2
    b.tri(p1, p2, p3, n1, n2, n3, uv1, uv2, uv3)


def cell015():
    c = Cave(REGIONS_HALF)
    b = c.b
    c.floor_slab()
    b.box((0, 0.011, 0), (3.0, 0.022, 10), "path",
          skip=("bottom", "px", "nx", "pz", "nz"))

    # --- the tube ------------------------------------------------------
    zs = [(-20 + i) * 0.25 for i in range(41)]
    grid = [[(x, y, z) for (x, y) in _ring(z)] for z in zs]
    npts = len(_ARCH)
    # vertex normals from central differences, oriented toward the axis
    normals = []
    for r in range(len(zs)):
        row = []
        for i in range(npts):
            p = grid[r][i]
            pa = grid[max(r - 1, 0)][i]
            pb = grid[min(r + 1, len(zs) - 1)][i]
            dz = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2])
            qa = grid[r][max(i - 1, 0)]
            qb = grid[r][min(i + 1, npts - 1)]
            di = (qb[0] - qa[0], qb[1] - qa[1], qb[2] - qa[2])
            nx = dz[1] * di[2] - dz[2] * di[1]
            ny = dz[2] * di[0] - dz[0] * di[2]
            nz = dz[0] * di[1] - dz[1] * di[0]
            L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nx, ny, nz = nx / L, ny / L, nz / L
            if nx * (0 - p[0]) + ny * (1.5 - p[1]) + nz * 0 < 0:
                nx, ny, nz = -nx, -ny, -nz
            row.append((nx, ny, nz))
        normals.append(row)
    u0, v0, u1, v1 = REGIONS_HALF["rock"]

    def _pingpong(s, period=2.0):
        p = (s / period) % 2.0
        return p if p <= 1.0 else 2.0 - p

    # UVs tile the rock photo at ~2m in both directions (ping-pong, so
    # there are no wrap seams): u along the corridor, v along the
    # profile's arc length. Without this the single photo stretches
    # over the whole 10m tube and the rock grain disappears.
    vertex_uv = {}
    for r in range(len(zs)):
        cum = [0.0]
        for i in range(1, npts):
            ax, ay = grid[r][i - 1][0], grid[r][i - 1][1]
            bx, by = grid[r][i][0], grid[r][i][1]
            cum.append(cum[-1] + math.hypot(bx - ax, by - ay))
        for i in range(npts):
            vertex_uv[(r, i)] = (u0 + (u1 - u0) * _pingpong(zs[r] + 5),
                                 v0 + (v1 - v0) * _pingpong(cum[i]))
    for r in range(len(zs) - 1):
        for i in range(npts - 1):
            quad = [(r, i), (r, i + 1), (r + 1, i + 1), (r + 1, i)]
            uv = {q: vertex_uv[q] for q in quad}
            P = [grid[rr][ii] for (rr, ii) in quad]
            N = [normals[rr][ii] for (rr, ii) in quad]
            U = [uv[q] for q in quad]
            _emit_tri(b, P[0], P[1], P[2], N[0], N[1], N[2], U[0], U[1], U[2])
            _emit_tri(b, P[0], P[2], P[3], N[0], N[2], N[3], U[0], U[2], U[3])

    # --- end walls (beside the mouth) and outer shell ------------------
    for s, zn in ((1, 5.0), (-1, -5.0)):
        n = [(0, 0, -s)] * 4
        # The sheet is set 4 cm inside the rim: at exactly +-5 it was coplanar with the
        # neighbouring cell's outer face and Z-fought it (cross-cell check, 2026-11-15).
        zq = zn - s * 0.04
        if s == 1:   # winding normal must be -z (into the cell)
            left = [(-1.5, 0, zq), (-5, 0, zq), (-5, 4, zq), (-1.5, 4, zq)]
            right = [(5, 0, zq), (1.5, 0, zq), (1.5, 4, zq), (5, 4, zq)]
        else:        # winding normal +z
            left = [(-5, 0, zq), (-1.5, 0, zq), (-1.5, 4, zq), (-5, 4, zq)]
            right = [(1.5, 0, zq), (5, 0, zq), (5, 4, zq), (1.5, 4, zq)]
        b.quad(left, n, "rock")
        b.quad(right, n, "rock")
        c.colliders.append((-3.25, 2.0, zn, 3.5, 4.0, 0.6))
        c.colliders.append((3.25, 2.0, zn, 3.5, 4.0, 0.6))
        c.colliders.append((0, 3.5, zn, 3.0, 1.0, 0.6))
    b.box((0, 4.05, 0), (10, 0.1, 10), "rock", skip=("bottom",))  # roof cap
    b.box((-5.05, 2.0, 0), (0.1, 4.0, 10), "rock", skip=("px", "bottom"))
    b.box((5.05, 2.0, 0), (0.1, 4.0, 10), "rock", skip=("nx", "bottom"))

    # --- per-segment wall colliders from the sampled profile -----------
    for k in range(10):
        z0, z1 = -5 + k, -4 + k
        for side in (-1, 1):
            mn = 9.9
            r = 0
            while r <= 4:
                z = z0 + r * 0.25
                for (px, py) in _ring(z):
                    if (px < 0) == (side < 0) and 0.2 <= py <= 2.6:
                        mn = min(mn, abs(px))
                r += 1
            inner = mn - 0.03
            cx = side * (5 + inner) / 2
            c.colliders.append((cx, 2.0, (z0 + z1) / 2, 5 - inner, 4.0, 1.0))

    # --- standard dressing / decor -------------------------------------
    for f in ("N", "S"):
        c.door(f)
    wx_w = _wall_x(1.9, 2.24, -1)
    c.lantern(wx_w - 0.02, 1.9, 1, 0)
    wx_e = _wall_x(-1.9, 2.24, 1)
    c.lantern(wx_e + 0.02, -1.9, -1, 0)
    c.tiling = ("rock", 2.0, REGIONS_HALF["rock"])
    for (sx, sz) in [(0.6, -2.6), (-0.7, 0.8), (0.2, 3.1)]:
        top = max(y for (x, y) in _ring(sz) if abs(x) <= 0.6)
        c.stalactites([(sx, sz)], ceil_y=top + 0.12)
    c.stalagmites([(_wall_x(-1.4, 0.4, -1) + 0.28, -1.4),
                   (_wall_x(2.3, 0.4, 1) - 0.28, 2.3)])
    c.crystals(_wall_x(0.9, 0.3, 1) - 0.38, 0.9)
    c.rubble([(_wall_x(-3.4, 0.3, -1) + 0.22, -3.4),
              (_wall_x(3.8, 0.3, 1) - 0.22, 3.8)])
    g = c.lights[0]
    keylight = f"1.0,0.72,0.42,2.0 ; {g[0]:.2f},{g[1]:.2f},{g[2]:.2f}"
    return c, c.manifest("gunyagunya-doukutsu", "0.64,0.59,0.50,0.5",
                         keylight, ["N", "S"])


CELLS = [(14, cell014), (15, cell015)]
HEADERS = {14: "# CELL14 variation pattern cave (offset cross) - see MULTI_CELL_DESIGN.md (dynamicworld)",
           15: "# CELL15 variation pattern cave (organic I corridor) - see MULTI_CELL_DESIGN.md (dynamicworld)"}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "cells")
    import sys as _sys
    only = int(_sys.argv[1]) if len(_sys.argv) > 1 else None
    for num, fn in CELLS:
        if only is not None and num != only:
            continue
        cave, manifest = fn()
        tris = cave.b.write_obj(
            os.path.join(out, f"cell{num:03d}.obj"), manifest, HEADERS[num])
        make_atlas_rock(os.path.join(out, f"cell{num:03d}.png"), seed=600 + num)
        print(f"cell{num:03d}: tris={tris} colliders={len(cave.colliders)}")
