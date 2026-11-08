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
        lines += [f"# collider: {c[0]},{c[1]},{c[2]}, {c[3]},{c[4]},{c[5]}"
                  for c in self.colliders]
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


def cell010():
    c = Cave()
    b = c.b
    c.floor_slab()
    H = 6.0
    # rock masses (ground plan; flight and platforms carve the east/north)
    c.rock_block(-5, -1.6, -0.5, 5, h=H)       # north-west mass
    c.rock_block(-5, -1.5, -5, -0.5, h=H)      # south-west mass
    c.rock_block(2.4, 5, 3.4, 5, h=H)          # north-east mass
    # perimeter walls where masses do not reach the rim
    c.wall(0.4, 4.9, 4.0, 0.2, h=H)            # north, over the lower pocket
    c.wall(4.9, 2.6, 0.2, 1.6, h=H)            # east, beside the landing
    c.wall(3.25, -4.9, 3.5, 0.2, h=H)          # south, east of the door
    # worn path: entry corridor and the pocket under the platform
    c.b.box((0, 0.011, -2.75), (3.0, 0.022, 4.5), "path")
    c.b.box((0.4, 0.011, 3.2), (4.0, 0.022, 3.4), "path")
    # stair flight along the east wall: 8 solid steps, y0 -> y3, S -> N
    for i in range(8):
        top = (i + 1) * 0.375
        zc = -4.2 + (i + 0.5) * 0.75
        b.box((3.6, top / 2, zc), (2.4, top, 0.75), "floor")
        c.colliders.append((3.6, top / 2, zc, 2.4, top, 0.75))
    # landing (north) + bridge + centre platform under the hatch, all y3
    b.box((1.9, 2.8, 2.6), (5.8, 0.4, 1.6), "floor")
    c.colliders.append((1.9, 2.8, 2.6, 5.8, 0.4, 1.6))
    b.box((0, 2.8, 0.05), (3.4, 0.4, 3.5), "floor")
    c.colliders.append((0, 2.8, 0.05, 3.4, 0.4, 3.5))
    b.box((0, 1.3, -1.2), (0.8, 2.6, 0.8), "rock")   # platform pillar
    c.colliders.append((0, 1.3, -1.2, 0.8, 2.6, 0.8))
    b.box((-1.3, 1.3, 2.9), (0.6, 2.6, 0.6), "rock")  # landing pillar (visual only)
    # ceiling at y6 with a 2m x 2m hatch over the centre platform
    b.box((0, H + 0.15, 3.0), (10, 0.3, 4.0), "rock")
    b.box((0, H + 0.15, -3.0), (10, 0.3, 4.0), "rock")
    b.box((3.0, H + 0.15, 0), (4.0, 0.3, 2.0), "rock")
    b.box((-3.0, H + 0.15, 0), (4.0, 0.3, 2.0), "rock")
    for sx, sz, w, d in ((0, 1.1, 2.4, 0.25), (0, -1.1, 2.4, 0.25),
                         (1.1, 0, 0.25, 2.4), (-1.1, 0, 0.25, 2.4)):
        b.box((sx, H - 0.12, sz), (w, 0.25, d), "wood")
    b.box((0, H - 0.02, 0), (0.5, 0.04, 0.5), "glow")
    c.door("S")
    c.stalactites([(2.8, -2.8), (-2.8, 2.0), (1.8, 4.2), (-0.9, -3.4)], ceil_y=H)
    c.crystals(0.6, 4.3)
    c.crystals(-1.15, -1.15)
    c.rubble([(-1.2, -4.2), (1.3, 2.2)])
    return c, c.manifest("kaidan-no-doukutsu", "0.6,0.66,0.8,0.55",
                         "0.85,0.92,1.0,1.9 ; 0,5.4,0", ["S", "U, stair"])


CELLS = [
    (6, cell006), (7, cell007), (8, cell008), (9, cell009), (10, cell010),
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
