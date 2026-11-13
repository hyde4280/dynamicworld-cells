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
from cellgen import AtlasPainter
from gen_basic_cells import Cave

# cell014 atlas layout (user-approved experiment 2026-11-13): the equal
# 3x2 split is only a generator convention — the loader reads whatever
# UVs the OBJ carries. Rock covers most of the visible surface, so it
# gets the whole left half (256x512, ~3x the pixels of the equal
# split); the five accent materials share the right half.
REGIONS_HALF = {
    "rock": (0.0, 0.0, 0.5, 1.0),
    "floor": (0.5, 0.5, 0.75, 1.0),
    "path": (0.75, 0.5, 1.0, 1.0),
    "wood": (0.5, 0.0, 0.75, 0.5),
    "crystal": (0.75, 0.25, 1.0, 0.5),
    "glow": (0.75, 0.0, 1.0, 0.25),
}


def _mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def rock_texture(p):
    """Rock face without the polka-dot look (user feedback 2026-11-13:
    the old `blobs` ellipses read as 水玉模様, not rock relief).

    Layers: multi-scale smooth noise for large uneven shading,
    irregular polygon facets with a darker lower edge (chiselled rock),
    wavy strata lines and random-walk cracks, then fine grain."""
    import math
    from PIL import Image, ImageDraw, ImageFilter
    rng = p.rng
    x0, y0, x1, y1 = (int(v) for v in p.px("rock"))
    w, h = x1 - x0, y1 - y0
    base = (76, 64, 51)
    dark = (40, 34, 27)
    light = (122, 106, 86)

    # --- multi-scale noise field -------------------------------------
    fields = []
    for cells_x, weight in ((5, 0.50), (11, 0.30), (23, 0.20)):
        cells_y = max(2, int(cells_x * h / w))
        small = Image.new("L", (cells_x, cells_y))
        sp = small.load()
        for yy in range(cells_y):
            for xx in range(cells_x):
                sp[xx, yy] = rng.randint(0, 255)
        layer = small.resize((w, h), Image.BICUBIC).filter(
            ImageFilter.GaussianBlur(1.2))
        fields.append((layer.load(), weight))
    tile = Image.new("RGB", (w, h))
    tp = tile.load()
    for yy in range(h):
        for xx in range(w):
            v = sum(f[xx, yy] * weight for f, weight in fields) / 255.0
            shade = (v - 0.5) * 2.0
            c = _mix(base, light, shade * 0.75) if shade > 0 else \
                _mix(base, dark, -shade * 0.85)
            jitter = rng.randint(-6, 6)
            tp[xx, yy] = tuple(max(0, min(255, ch + jitter)) for ch in c)
    p.img.paste(tile, (x0, y0))
    p.d = ImageDraw.Draw(p.img)
    d = p.d

    # --- facets: irregular polygons, darker lower edge ---------------
    palette = [(90, 78, 62), (63, 54, 44), (99, 86, 68), (56, 47, 39)]
    for _ in range(46):
        cx = rng.uniform(x0, x1)
        cy = rng.uniform(y0, y1)
        r = rng.uniform(10, 34)
        nv = rng.randint(5, 8)
        pts = []
        for k in range(nv):
            ang = 2 * 3.14159265 * k / nv + rng.uniform(-0.3, 0.3)
            rr = r * rng.uniform(0.55, 1.15)
            pts.append((cx + rr * math.cos(ang),
                        cy + rr * math.sin(ang) * 0.78))
        fill = _mix(rng.choice(palette), base, 0.35)
        d.polygon(pts, fill=fill)
        # shadow along the lower edge, highlight along the upper edge
        low = max(range(nv), key=lambda k: pts[k][1])
        up = min(range(nv), key=lambda k: pts[k][1])
        for a, b, col, wd in ((low, (low + 1) % nv, dark, 2),
                              (up, (up + 1) % nv, light, 1)):
            d.line([pts[a], pts[b]], fill=_mix(col, fill, 0.3), width=wd)

    # --- strata: wavy near-horizontal dark bands ----------------------
    for _ in range(7):
        yy = rng.uniform(y0 + 8, y1 - 8)
        pts = []
        xx = x0
        while xx <= x1:
            pts.append((xx, yy + rng.uniform(-2.5, 2.5)))
            xx += rng.uniform(14, 30)
        d.line(pts, fill=_mix(dark, base, 0.25), width=rng.randint(1, 3))

    # --- cracks: random-walk polylines --------------------------------
    for _ in range(16):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        pts = [(x, y)]
        for _ in range(rng.randint(4, 9)):
            x += rng.uniform(-9, 9)
            y += rng.uniform(4, 13)
            pts.append((x, y))
        d.line(pts, fill=_mix(dark, base, 0.1), width=1)

    # --- fine grain -----------------------------------------------------
    for _ in range(900):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        r = rng.uniform(0.6, 1.7)
        delta = rng.randint(-13, 13)  # luminance only: no colour confetti
        c = tuple(max(0, min(255, ch + delta)) for ch in base)
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)


def rock_photo(p):
    """Rock face from a CC0 photo texture (user suggestion 2026-11-13:
    real rock imagery beats procedural generation for the wall region).

    Source: Poly Haven "Rock Boulder Cracked" diffuse 1K
    (https://polyhaven.com/a/rock_boulder_cracked), CC0, photography
    Dimitrios Savva / processing Dario Barresi. The raw scan is very
    orange (iron-rich rock), so it is graded toward muddy brown-grey
    and darkened before pasting. Falls back to rock_texture() when the
    asset file is missing."""
    import os
    from PIL import Image
    asset = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "assets", "rock_boulder_cracked_diff_1k.jpg")
    if not os.path.exists(asset):
        rock_texture(p)
        return
    x0, y0, x1, y1 = (int(v) for v in p.px("rock"))
    w, h = x1 - x0, y1 - y0
    src = Image.open(asset).convert("RGB")
    crop_w = int(src.height * w / h)
    left = (src.width - crop_w) // 2
    tile = src.crop((left, 0, left + crop_w, src.height)).resize((w, h))
    tp = tile.load()
    for yy in range(h):
        for xx in range(w):
            r, g, b = tp[xx, yy]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            # pull toward a muddy brown-grey, then darken for cave use
            t = 0.48
            r = (r * (1 - t) + lum * 1.03 * t) * 0.84
            g = (g * (1 - t) + lum * 0.93 * t) * 0.84
            b = (b * (1 - t) + lum * 0.79 * t) * 0.84
            tp[xx, yy] = (max(0, min(255, int(r))), max(0, min(255, int(g))),
                          max(0, min(255, int(b))))
    p.img.paste(tile, (x0, y0))
    from PIL import ImageDraw
    p.d = ImageDraw.Draw(p.img)


def make_atlas_rock(path, seed):
    """Muddy, rocky palette (user feedback 2026-11-13: the basic cells'
    blue-grey rock read as purple; use warm brown-grey rock and mud)."""
    p = AtlasPainter(512, REGIONS_HALF, seed=seed)
    rock_photo(p)
    p.tile_grid("floor", (82, 74, 62), (54, 47, 39))
    p.speckle("path", (122, 102, 76), n=1700, amp=16)
    p.planks("wood", (104, 72, 42), (70, 47, 27))
    p.gradient("crystal", (132, 198, 188), (42, 96, 90), speckle_n=200)
    p.gradient("glow", (255, 196, 96), (196, 108, 36), speckle_n=200)
    p.save(path)

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
                    ra[2] = rb[2]
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
    c = Cave()
    c.b.regions = REGIONS_HALF  # UV layout matching make_atlas_rock
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
    c.stalactites([(0, 3.5), (2.6, 0.9), (2.6, -2.2), (-4.0, 0.7), (0, -3.6)])
    c.stalagmites([(-1.2, 3.6), (3.75, -1.6), (1.2, -4.3)])
    c.crystals(3.55, 1.55)
    c.rubble([(1.35, 4.4), (-2.9, 2.6), (3.7, -3.7)])
    return c, c.manifest("kuichigai-jujiro-doukutsu", "0.66,0.60,0.50,0.5",
                         "1.0,0.72,0.42,1.7 ; 0,3.4,0", ["N", "E", "S", "W"])


CELLS = [(14, cell014)]

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "cells")
    for num, fn in CELLS:
        cave, manifest = fn()
        tris = cave.b.write_obj(
            os.path.join(out, f"cell{num:03d}.obj"), manifest,
            f"# CELL{num} variation pattern cave (offset cross) - see MULTI_CELL_DESIGN.md (dynamicworld)")
        make_atlas_rock(os.path.join(out, f"cell{num:03d}.png"), seed=600 + num)
        print(f"cell{num:03d}: tris={tris} colliders={len(cave.colliders)}")
