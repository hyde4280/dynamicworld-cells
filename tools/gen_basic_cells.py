#!/usr/bin/env python3
"""Basic connection-pattern cells, cave-dungeon style (2026-11-08).

cell006 cross (N/E/S/W), cell007 T (N/E/S), cell008 I (N/S),
cell009 L (S/E), cell010 stair room (S + U,stair).

Design: the 10m square is mostly solid rock; walkable space is a 3m-wide
corridor carved through it (door openings stay 2m wide x 3m high at face
centres, per the door spec). Doors are declared in the manifest with
`# door:` lines (one per face). Geometry/colliders stay inside the
16-collider pool: rock masses and stair steps carry colliders, perimeter
walls follow the existing cells' convention (host slot guards the rim).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cellgen import CellBuilder, AtlasPainter, grid_regions

REGIONS = grid_regions(["rock", "floor", "path", "wood", "crystal", "glow"], 3, 2)
CW = 1.5  # corridor half width


def make_atlas(path, seed):
    p = AtlasPainter(512, REGIONS, seed=seed)
    p.blobs("rock", (52, 54, 66), (68, 70, 84), n=300, rmin=6, rmax=22)
    p.tile_grid("floor", (74, 72, 82), (48, 46, 56))
    p.speckle("path", (116, 106, 90), n=1600, amp=14)
    p.planks("wood", (96, 66, 40), (66, 44, 26))
    p.gradient("crystal", (140, 225, 240), (36, 100, 140), speckle_n=200)
    p.gradient("glow", (255, 196, 96), (196, 108, 36), speckle_n=200)
    p.save(path)


class Cave:
    def __init__(self):
        self.b = CellBuilder(REGIONS)
        self.colliders = []
        self.portals = []   # (face, x, y, z): interact floor points for stacked cells

    # -- pieces ---------------------------------------------------------
    def rock_block(self, x0, x1, z0, z1, h=4.0, collider=True):
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        self.b.box((cx, h / 2, cz), (x1 - x0, h, z1 - z0), "rock")
        if collider:
            self.colliders.append((cx, h / 2, cz, x1 - x0, h, z1 - z0))

    def wall(self, cx, cz, sx, sz, h=4.0):
        self.b.box((cx, h / 2, cz), (sx, h, sz), "rock")

    def corridor(self, x0, x1, z0, z1, ceil_y=4.0):
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        self.b.box((cx, 0.011, cz), (x1 - x0, 0.022, z1 - z0), "path")
        self.b.box((cx, ceil_y + 0.15, cz), (x1 - x0, 0.3, z1 - z0), "rock")

    def door(self, face):
        """2m x 3m opening dressing at a face centre: rock side segments
        (collider), wooden posts and lintel. Corridor width is 3m, so the
        segments fill from the door edge (1m) to the corridor edge (1.5m)."""
        b = self.b
        if face in ("N", "S"):
            z = 4.83 if face == "N" else -4.83
            zp = 4.8 if face == "N" else -4.8
            for s in (-1, 1):
                cx = s * 1.25
                b.box((cx, 1.5, z), (0.5, 3.0, 0.3), "rock")
                self.colliders.append((cx, 1.5, z, 0.5, 3.0, 0.3))
                b.box((s * 1.3, 1.5, zp), (0.22, 3.0, 0.3), "wood")
            b.box((0, 3.3, z), (3.0, 0.6, 0.3), "wood")
            b.box((0, 3.85, z), (3.0, 0.3, 0.3), "rock")
        else:
            x = 4.83 if face == "E" else -4.83
            xp = 4.8 if face == "E" else -4.8
            for s in (-1, 1):
                cz = s * 1.25
                b.box((x, 1.5, cz), (0.3, 3.0, 0.5), "rock")
                self.colliders.append((x, 1.5, cz, 0.3, 3.0, 0.5))
                b.box((xp, 1.5, s * 1.3), (0.3, 3.0, 0.22), "wood")
            b.box((x, 3.3, 0), (0.3, 0.6, 3.0), "wood")
            b.box((x, 3.85, 0), (0.3, 0.3, 3.0), "rock")

    def stalactites(self, pts, ceil_y=4.0):
        for x, z in pts:
            self.b.cylinder((x, ceil_y - 0.5, z), 0.03, 0.30, 1.0, 6, "rock")

    def stalagmites(self, pts):
        for x, z in pts:
            self.b.cylinder((x, 0.4, z), 0.30, 0.03, 0.8, 6, "rock")

    def crystals(self, x, z, n=3, collider=False):
        for i in range(n):
            dx, dz = (i - (n - 1) / 2) * 0.35, ((i % 2) - 0.5) * 0.3
            self.b.cylinder((x + dx, 0.55, z + dz), 0.16, 0.02, 1.1, 5, "crystal",
                            rot=(8 * (i - 1), 0, 6 * (1 - i)))
        if collider:
            self.colliders.append((x, 0.55, z, 0.9, 1.1, 0.7))

    def rubble(self, pts):
        import random
        rng = random.Random(99)
        for x, z in pts:
            self.b.sphere((x, 0.10, z), rng.uniform(0.16, 0.30), 7, 5, "rock",
                          squash=(1, 0.6, 1), jitter=0.3, rng=rng)

    def floor_slab(self):
        self.b.box((0, -0.05, 0), (10, 0.1, 10), "floor")

    def manifest(self, name, ambient, keylight, doors):
        lines = [
            f"# cell.name: {name}",
            "# cell.version: 0",
            f"# cell.ambient: {ambient}",
            f"# cell.lightvolume: {ambient}",
            f"# cell.keylight: {keylight}",
        ]
        lines += [f"# door: {d}" for d in doors]
        lines += [f"# portal: {p[0]}, {p[1]},{p[2]},{p[3]}" for p in self.portals]
        for c in self.colliders:
            line = f"# collider: {c[0]},{c[1]},{c[2]}, {c[3]},{c[4]},{c[5]}"
            if len(c) >= 9:   # optional Euler rotation (slopes)
                line += f", {c[6]},{c[7]},{c[8]}"
            lines.append(line)
        return lines


# -- the five cells ------------------------------------------------------

def cell006():
    c = Cave()
    c.floor_slab()
    for sx in (-1, 1):
        for sz in (-1, 1):
            c.rock_block(sx * CW if sx > 0 else -5, sx * 5 if sx > 0 else -CW,
                         sz * CW if sz > 0 else -5, sz * 5 if sz > 0 else -CW)
    c.corridor(-CW, CW, -5, 5)
    c.corridor(-5, 5, -CW, CW)
    for f in "NESW":
        c.door(f)
    c.stalactites([(0.9, 0.9), (-0.9, -0.9), (0, 3.4), (3.4, 0), (-3.4, 0), (0, -3.4)])
    c.stalagmites([(1.15, 1.15), (-1.15, -1.15)])
    c.crystals(-1.05, 1.05)
    c.rubble([(1.3, -2.6), (-1.3, 2.2), (2.8, -1.25)])
    return c, c.manifest("jujiro-doukutsu", "0.55,0.62,0.78,0.5",
                         "1.0,0.72,0.42,1.7 ; 0,3.4,0", ["N", "E", "S", "W"])


def cell007():
    c = Cave()
    c.floor_slab()
    c.rock_block(-5, -CW, -5, 5)          # west mass (no W door)
    c.rock_block(CW, 5, -5, -CW)          # south-east corner
    c.rock_block(CW, 5, CW, 5)            # north-east corner
    c.corridor(-CW, CW, -5, 5)
    c.corridor(CW, 5, -CW, CW)
    for f in ("N", "E", "S"):
        c.door(f)
    c.stalactites([(0.9, -0.9), (0, 3.2), (3.2, 0.9), (-0.9, 2.4)])
    c.crystals(1.05, -1.05)
    c.rubble([(-1.25, -3.0), (2.4, 1.25)])
    return c, c.manifest("teijiro-doukutsu", "0.55,0.62,0.78,0.5",
                         "1.0,0.72,0.42,1.7 ; 0,3.4,0", ["N", "E", "S"])


def cell008():
    c = Cave()
    c.floor_slab()
    c.rock_block(-5, -CW, -5, 5)
    c.rock_block(CW, 5, -5, 5)
    c.corridor(-CW, CW, -5, 5)
    for f in ("N", "S"):
        c.door(f)
    c.stalactites([(0.8, -1.8), (-0.8, 0.6), (0.7, 2.8)])
    c.crystals(1.15, 0.4)
    c.stalagmites([(-1.15, -3.2)])
    c.rubble([(1.25, -2.8), (-1.25, 3.6)])
    return c, c.manifest("ipponmichi-doukutsu", "0.5,0.58,0.75,0.5",
                         "1.0,0.72,0.42,1.6 ; 0,3.4,-1", ["N", "S"])


def cell009():
    c = Cave()
    c.floor_slab()
    c.rock_block(-5, -CW, CW, 5)          # north-west
    c.rock_block(-5, -CW, -5, -CW)        # south-west
    c.rock_block(CW, 5, -5, -CW)          # south-east
    c.rock_block(CW, 5, CW, 5)            # north-east
    c.rock_block(-CW, CW, CW, 5)          # north centre (no N door)
    c.corridor(-CW, CW, -5, CW)
    c.corridor(-CW, 5, -CW, CW)
    for f in ("S", "E"):
        c.door(f)
    c.stalactites([(0.9, -0.9), (0, -3.2), (3.0, 0.9)])
    c.crystals(1.05, 1.05)
    c.rubble([(-1.25, -1.8), (1.8, -1.25)])
    return c, c.manifest("magarimichi-doukutsu", "0.55,0.6,0.78,0.5",
                         "1.0,0.72,0.42,1.7 ; 0,3.4,-1", ["S", "E"])


def ramp_collider(x, z0, y0, z1, y1, width, thick=0.3):
    """Sloped box whose top surface runs from (z0,y0) to (z1,y1) along the lane
    at x (walkable surface for a stair that is visual-only). Returns the 9-value
    collider tuple (center, size, euler) used by `# collider:` lines."""
    import math
    dz, dy = z1 - z0, y1 - y0
    length = math.hypot(dz, dy)
    theta = math.degrees(math.atan2(abs(dy), abs(dz)))   # slope angle, 0..90
    # Unity: a negative X rotation lifts the +z end, a positive one the -z end.
    # Keep |rx| < 90 so the box is never flipped (its up vector stays upward).
    rx = -theta if dz > 0 else theta
    a = math.radians(rx)
    up = (0.0, math.cos(a), math.sin(a))       # rotated local up (surface normal)
    mx, my, mz = x, (y0 + y1) / 2, (z0 + z1) / 2
    cx, cy, cz = mx - up[0] * thick / 2, my - up[1] * thick / 2, mz - up[2] * thick / 2
    return (round(cx, 4), round(cy, 4), round(cz, 4),
            width, thick, round(length, 4), round(rx, 3), 0, 0)


def cell010():
    """Stair tower for a 9 m vertical pitch (3 layers x 3 m).

    Three cave ramps (visually 24 fine steps of 0.125 m rise x 0.2 m tread,
    2.4 m wide, so they read as a slope), each lifting 3 m, with a landing
    between them:
      F1 west lane  z -3.3 -> +1.5   y 0 -> 3   (north)
      landing A     z +1.5 -> +4.8   y 3
      F2 east lane  z +1.5 -> -3.3   y 3 -> 6   (south)
      landing B     z -3.3 -> -4.8   y 6
      F3 centre     z -3.3 -> +1.5   y 6 -> 9   (north, through the 3x3 hole)
    Walkable surfaces are tilted boxes (one per ramp); there are no step colliders.
    The ceiling (y 8.5-8.8) has a 3x3 hole at the cell centre; the upper cell's
    floor (world y 9) has the matching hole and F3 ends flush with it."""
    c = Cave()
    b = c.b
    c.floor_slab()
    H = 9.0
    TREAD, RISE, N = 0.2, 0.125, 24
    # perimeter walls (visual; the host slot guards the rim)
    c.wall(0, 4.9, 10, 0.2, h=H)                # north
    c.wall(4.9, 0, 0.2, 10, h=H)                # east
    c.wall(-4.9, 0, 0.2, 10, h=H)               # west
    c.wall(-3.25, -4.9, 3.5, 0.2, h=H)          # south, west of the door
    c.wall(3.25, -4.9, 3.5, 0.2, h=H)           # south, east of the door
    b.box((0, 6.5, -4.9), (3.0, 5.0, 0.2), "rock")   # south, above the door lintel
    c.door("S")
    # worn path: entry strip under landing B
    b.box((0, 0.011, -4.05), (9.6, 0.022, 1.5), "path")

    def flight(xc, z_start, direction, y_base):
        """Solid fine steps from the floor; direction +1 north / -1 south."""
        for i in range(N):
            top = y_base + (i + 1) * RISE
            zc = z_start + direction * (i + 0.5) * TREAD
            b.box((xc, top / 2, zc), (2.4, top, TREAD), "floor")

    flight(-3.6, -3.3, +1, 0.0)    # F1
    flight(3.6, 1.5, -1, 3.0)      # F2
    flight(0.0, -3.3, +1, 6.0)     # F3
    # landing A (y=3) over a solid rock fill; landing B (y=6) over the entry strip
    b.box((0, 1.3, 3.15), (9.6, 2.6, 3.3), "rock")
    b.box((0, 2.8, 3.15), (9.6, 0.4, 3.3), "floor")
    b.box((0, 5.8, -4.05), (9.6, 0.4, 1.5), "floor")
    # ceiling slab (y 8.5-8.8) with a 3x3 hole at the centre
    b.box((0, 8.65, 3.15), (9.6, 0.3, 3.3), "rock")
    b.box((0, 8.65, -3.15), (9.6, 0.3, 3.3), "rock")
    b.box((-3.15, 8.65, 0), (3.3, 0.3, 3.0), "rock")
    b.box((3.15, 8.65, 0), (3.3, 0.3, 3.0), "rock")
    for sx, sz, w, d in ((0, 1.6, 3.2, 0.2), (0, -1.6, 3.2, 0.2),
                         (1.6, 0, 0.2, 3.0), (-1.6, 0, 0.2, 3.0)):
        b.box((sx, 8.45, sz), (w, 0.3, d), "wood")  # frame around the hole
    b.box((0, 8.3, 3.5), (0.5, 0.04, 0.5), "glow")

    # walkable surfaces: one slope per flight, plus landings and flight sides
    lip = 0.03   # surface line through the tread centres, a hair above
    c.colliders.append(ramp_collider(-3.6, -3.3, 0.0 + lip, 1.5, 3.0 + lip, 2.4))   # F1
    c.colliders.append(ramp_collider(3.6, 1.5, 3.0 + lip, -3.3, 6.0 + lip, 2.4))    # F2
    c.colliders.append(ramp_collider(0.0, -3.3, 6.0 + lip, 1.5, 9.0 + lip, 2.4))    # F3
    c.colliders.append((0, 2.8, 3.15, 9.6, 0.4, 3.3))                          # landing A
    c.colliders.append((0, 5.8, -4.05, 9.6, 0.4, 1.5))                         # landing B
    c.colliders.append((0, 1.3, 3.15, 9.6, 2.6, 3.3))                          # rock fill under A
    c.colliders.append((-2.4, 1.5, -0.9, 0.2, 3.0, 4.8))                       # F1 east side
    c.colliders.append((2.4, 3.0, -0.9, 0.2, 6.0, 4.8))                        # F2 west side
    c.colliders.append((-1.2, 4.5, -0.9, 0.2, 9.0, 4.8))                       # F3 west side
    c.colliders.append((1.2, 4.5, -0.9, 0.2, 9.0, 4.8))                        # F3 east side

    c.portals.append(("U", 0.0, 8.09, 0.0))    # interact point on F3 (kept below pitch-0.3 so G stays in this cell)
    c.stalactites([(-2.0, -3.9), (2.0, -3.9)], ceil_y=5.6)
    c.crystals(-1.9, -2.0)
    c.crystals(1.9, -2.0)
    c.rubble([(-0.6, -4.1), (0.8, -3.9)])
    return c, c.manifest("kaidan-no-doukutsu", "0.6,0.66,0.8,0.55",
                         "0.85,0.92,1.0,1.9 ; 0,7.0,-1", ["S", "U, stair"])


def cell011():
    """Upper landing room for the 9 m stair tower (cell010).

    Floor with a 3x3 hole at the centre (the D opening: the top of cell010's
    third ramp ends flush with this floor, y=0), a wooden rim around the hole,
    and N/S doors. Floor colliders are provided by the host slot, which swaps
    its full floor box for four boxes around the hole when the cell declares
    a D door."""
    c = Cave()
    b = c.b
    H = 4.0
    # floor around the hole (visual)
    b.box((0, -0.05, 3.25), (10, 0.1, 3.5), "floor")
    b.box((0, -0.05, -3.25), (10, 0.1, 3.5), "floor")
    b.box((3.25, -0.05, 0), (3.5, 0.1, 3.0), "floor")
    b.box((-3.25, -0.05, 0), (3.5, 0.1, 3.0), "floor")
    for sx, sz, w, d in ((0, 1.6, 3.2, 0.2), (0, -1.6, 3.2, 0.2),
                         (1.6, 0, 0.2, 3.0), (-1.6, 0, 0.2, 3.0)):
        b.box((sx, 0.15, sz), (w, 0.3, d), "wood")   # rim around the hole
    b.box((0, -0.12, 0), (0.5, 0.04, 0.5), "glow")      # faint glow in the hole
    # perimeter walls with N/S door gaps; ceiling
    c.wall(4.9, 0, 0.2, 10, h=H)
    c.wall(-4.9, 0, 0.2, 10, h=H)
    for z in (4.9, -4.9):
        c.wall(-3.25, z, 3.5, 0.2, h=H)
        c.wall(3.25, z, 3.5, 0.2, h=H)
    c.door("N")
    c.door("S")
    b.box((0, H + 0.15, 0), (10, 0.3, 10), "rock")
    b.box((0, 0.011, 4.0), (3.0, 0.022, 2.0), "path")
    b.box((0, 0.011, -4.0), (3.0, 0.022, 2.0), "path")
    c.portals.append(("D", 0.0, 0.0, 2.4))     # arrival / interact point beside the hole
    c.stalactites([(-3.2, 2.8), (3.2, -2.8), (-3.0, -3.0)], ceil_y=H)
    c.crystals(-3.4, 0.0)
    c.rubble([(3.4, 2.4), (-2.6, -2.2)])
    return c, c.manifest("kaidan-no-ue", "0.6,0.66,0.8,0.55",
                         "0.85,0.92,1.0,1.7 ; 0,3.2,0", ["N", "S", "D, stair"])


CELLS = [
    (6, cell006), (7, cell007), (8, cell008), (9, cell009), (10, cell010), (11, cell011),
]

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "cells")
    for num, fn in CELLS:
        cave, manifest = fn()
        tris = cave.b.write_obj(
            os.path.join(out, f"cell{num:03d}.obj"), manifest,
            f"# CELL{num} basic pattern cave - see MULTI_CELL_DESIGN.md (dynamicworld)")
        make_atlas(os.path.join(out, f"cell{num:03d}.png"), seed=600 + num)
        print(f"cell{num:03d}: tris={tris} colliders={len(cave.colliders)}")
