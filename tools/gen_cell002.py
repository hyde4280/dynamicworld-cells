#!/usr/bin/env python3
"""cell002 'niwa' - evening garden, measurement tier ~5k tris (spec section 7)."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cellgen import CellBuilder, AtlasPainter, grid_regions

REGIONS = grid_regions(["stone", "plaster", "wood", "grass", "water", "foliage"], 3, 2)


def make_atlas(path):
    p = AtlasPainter(1024, REGIONS, seed=7)
    p.tile_grid("stone", (105, 108, 115), (70, 72, 78))
    p.speckle("plaster", (214, 205, 188))
    p.planks("wood", (110, 78, 50), (80, 55, 34))
    p.blobs("grass", (74, 110, 52), (88, 128, 60), n=420, rmin=4, rmax=12)
    p.gradient("water", (70, 130, 170), (35, 80, 120), speckle_n=350)
    p.blobs("foliage", (46, 84, 44), (60, 104, 54), n=320, rmin=8, rmax=24)
    p.save(path)


def build():
    b = CellBuilder(REGIONS)
    rng = random.Random(202)
    b.room_shell("plaster", "stone", wall_h=4.0, beams=(-3, 0, 3), beam_region="wood")
    # grass carpet patches (leave the stone path along z and the pond area)
    b.box((-2.9, 0.006, 0.6), (3.9, 0.012, 8.6), "grass")
    b.box((3.4, 0.006, -2.6), (2.9, 0.012, 4.4), "grass")
    b.box((0.4, 0.006, 3.6), (9.0, 0.012, 2.6), "grass")
    # stepping-stone path, entrance -> back
    for z in (-3.4, -1.8, -0.2, 1.4, 3.0):
        b.box((rng.uniform(-0.15, 0.15), 0.03, z), (1.1, 0.06, 0.9), "stone")
    # pond: water disc + stone rim
    b.cylinder((2.9, 0.02, 1.9), 1.55, 1.55, 0.04, 20, "water")
    for k in range(12):
        a = 2 * 3.14159 * k / 12
        x, z = 2.9 + 1.75 * __import__("math").sin(a), 1.9 + 1.75 * __import__("math").cos(a)
        b.sphere((x, 0.10, z), rng.uniform(0.16, 0.30), 8, 6, "stone",
                 squash=(1, 0.62, 1), jitter=0.25, rng=rng)
    # pine tree (north-west)
    b.cylinder((-3.1, 1.0, 3.1), 0.16, 0.11, 2.0, 7, "wood", rot=(0, 0, 4))
    b.cylinder((-3.35, 2.2, 3.1), 0.07, 0.05, 1.4, 6, "wood", rot=(0, 0, 52))
    for c, r in (((-3.2, 2.9, 3.1), 1.25), ((-3.9, 2.45, 3.0), 0.85), ((-2.5, 2.5, 3.3), 0.8)):
        b.sphere(c, r, 14, 11, "foliage", squash=(1, 0.55, 1), jitter=0.08, rng=rng)
    # bamboo fence along the north wall
    for k in range(38):
        x = -4.55 + k * 0.24
        b.cylinder((x, 0.6, 4.55), 0.035, 0.035, 1.2, 6, "wood")
    b.box((0, 1.05, 4.55), (9.3, 0.05, 0.05), "wood")
    b.box((0, 0.45, 4.55), (9.3, 0.05, 0.05), "wood")
    # shrubs
    for c in ((-4.2, 0.32, -1.6), (4.3, 0.28, -3.9), (-1.9, 0.3, 4.2), (1.8, 0.26, -4.1)):
        b.sphere(c, 0.42, 12, 9, "foliage", squash=(1, 0.7, 1), jitter=0.1, rng=rng)
    # garden rocks
    for c, r in (((-1.7, 0.16, 1.9), 0.34), ((4.0, 0.13, 3.9), 0.28), ((-4.0, 0.2, 1.2), 0.4)):
        b.sphere(c, r, 12, 9, "stone", squash=(1, 0.65, 1), jitter=0.3, rng=rng)
    # stone lanterns flanking the path
    for x in (-1.3, 1.3):
        b.box((x, 0.25, -2.6), (0.34, 0.5, 0.34), "stone")
        b.box((x, 0.58, -2.6), (0.46, 0.16, 0.46), "stone")
        b.box((x, 0.78, -2.6), (0.3, 0.24, 0.3), "stone")
    # wooden deck along the west wall + stone basin
    b.box((-4.35, 0.09, -2.2), (1.1, 0.18, 3.6), "wood")
    for dz in (-3.8, -2.2, -0.6):
        b.box((-4.35, 0.05, dz), (0.9, 0.1, 0.3), "stone")
    b.cylinder((3.9, 0.28, -1.4), 0.34, 0.28, 0.56, 12, "stone")
    b.cylinder((3.9, 0.58, -1.4), 0.26, 0.26, 0.04, 12, "water")
    # grass tufts
    for _ in range(110):
        x = rng.uniform(-4.6, 4.6)
        z = rng.uniform(-4.6, 4.6)
        if abs(x) < 0.9 and z < 3.4:
            continue
        if (x - 2.9) ** 2 + (z - 1.9) ** 2 < 2.6 ** 2:
            continue
        b.cylinder((x, 0.09, z), 0.09, 0.01, 0.18, 5, "foliage", cap=False)
    return b


MANIFEST = [
    "# cell.name: niwa",
    "# cell.version: 0",
    "# cell.ambient: 1.0,0.88,0.7,0.55",
    "# cell.keylight: 1.0,0.75,0.5,1.8 ; -4,5,-1",
    "# collider: -3.1,1.0,3.1, 0.5,2.0,0.5",
    "# collider: -1.3,0.45,-2.6, 0.5,0.9,0.5",
    "# collider: 1.3,0.45,-2.6, 0.5,0.9,0.5",
    "# collider: 2.9,0.25,1.9, 3.4,0.5,3.4",
    "# collider: -1.7,0.25,1.9, 0.7,0.5,0.7",
    "# collider: 4.0,0.2,3.9, 0.6,0.4,0.6",
    "# collider: -4.0,0.3,1.2, 0.8,0.6,0.8",
]


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "cells")
    b = build()
    tris = b.write_obj(os.path.join(out, "cell002.obj"), MANIFEST, "# CELL2 niwa - see PROTOTYPE_SPEC.md")
    make_atlas(os.path.join(out, "cell002.png"))
    print(f"cell002 verts={len(b.verts)} tris={tris}")
