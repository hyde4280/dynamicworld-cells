#!/usr/bin/env python3
"""cell003 'iseki' - noon ruins, measurement tier ~20k tris (spec section 7)."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cellgen import CellBuilder, AtlasPainter, grid_regions

REGIONS = grid_regions(["stone", "dark", "sand", "bronze", "moss", "plaster"], 3, 2)


def make_atlas(path):
    p = AtlasPainter(1024, REGIONS, seed=11)
    p.tile_grid("stone", (112, 110, 104), (76, 74, 70))
    p.speckle("dark", (74, 72, 68), n=1600, amp=12)
    p.speckle("sand", (178, 158, 120), n=1800, amp=16)
    p.speckle("bronze", (122, 96, 52), n=900, amp=14)
    p.blobs("moss", (88, 104, 62), (104, 122, 74), n=380, rmin=5, rmax=16)
    p.speckle("plaster", (206, 196, 178))
    p.save(path)


def column(b, x, z, shaft_h, broken=False):
    b.box((x, 0.15, z), (0.95, 0.3, 0.95), "dark")
    b.cylinder((x, 0.3 + shaft_h / 2, z), 0.34, 0.30, shaft_h, 18, "stone")
    if not broken:
        b.box((x, 0.3 + shaft_h + 0.12, z), (0.9, 0.24, 0.9), "dark")
    return 0.3 + shaft_h + (0.24 if not broken else 0)


def build():
    b = CellBuilder(REGIONS)
    rng = random.Random(303)
    # floor + walls (north wall broken into segments of varying height)
    b.box((0, -0.05, 0), (10, 0.1, 10), "sand")
    b.box((4.9, 2, 0), (0.2, 4, 10), "stone")
    b.box((-4.9, 2, 0), (0.2, 4, 10), "stone")
    b.box((-3, 2, -4.9), (4, 4, 0.2), "stone")
    b.box((3, 2, -4.9), (4, 4, 0.2), "stone")
    b.box((0, 3.5, -4.9), (2, 1, 0.2), "stone")
    for x, h in ((-3.9, 4.0), (-1.95, 2.6), (0.0, 3.4), (1.95, 1.9), (3.9, 4.0)):
        b.box((x, h / 2, 4.9), (1.9, h, 0.2), "stone")
    # floor tile grid (central plaza)
    for ix in range(7):
        for iz in range(7):
            x = -3.3 + ix * 1.1
            z = -3.3 + iz * 1.1
            if rng.random() < 0.12:
                continue  # missing tile
            b.box((x, 0.015, z), (1.0, 0.03, 1.0), "stone" if (ix + iz) % 2 else "dark")
    # columns: two rows
    column(b, -2.7, -2.0, 2.9)
    column(b, -2.7, 0.8, 1.1, broken=True)
    column(b, -2.7, 3.4, 2.5)
    column(b, 2.7, -2.0, 2.9)
    column(b, 2.7, 0.8, 2.9)
    column(b, 2.7, 3.4, 0.7, broken=True)
    # entablature beam across the intact pair (north end)
    b.box((0, 3.62, -2.0), (6.3, 0.35, 0.8), "dark")
    # fallen columns + drums
    b.cylinder((-0.9, 0.32, 1.9), 0.32, 0.32, 2.4, 18, "stone", rot=(90, 0, 12))
    b.cylinder((1.6, 0.32, 3.6), 0.32, 0.32, 1.7, 18, "stone", rot=(90, 0, -30))
    for c in ((-1.9, 0.3, 3.1), (0.4, 0.3, 0.4), (3.6, 0.3, 1.8)):
        b.cylinder(c, 0.3, 0.3, 0.6, 18, "dark", rot=(90, 0, rng.uniform(0, 90)))
    # guardian statue on a pedestal (center-north)
    b.box((0, 0.25, 3.9), (1.7, 0.5, 1.1), "dark")
    b.box((0, 0.65, 3.9), (1.3, 0.3, 0.85), "stone")
    b.cylinder((0, 1.45, 3.9), 0.34, 0.26, 1.3, 14, "bronze")          # torso
    b.sphere((0, 2.42, 3.9), 0.30, 16, 12, "bronze")                      # head
    b.cylinder((-0.5, 1.5, 3.9), 0.09, 0.07, 1.1, 8, "bronze", rot=(0, 0, 18))   # arm L
    b.cylinder((0.52, 1.62, 3.9), 0.09, 0.07, 1.3, 8, "bronze", rot=(0, 0, -32)) # arm R
    b.cylinder((0.95, 1.7, 3.9), 0.025, 0.025, 2.6, 6, "dark")            # spear shaft
    b.cylinder((0.95, 3.15, 3.9), 0.09, 0.0, 0.35, 6, "bronze")          # spear tip
    b.box((0, 0.95, 3.52), (0.7, 0.5, 0.18), "bronze")                    # shield front (faces entrance)
    # relief blocks protruding from the east wall
    for ix in range(3):
        for iz in range(4):
            b.box((4.72, 0.8 + iz * 0.85, -3.2 + ix * 2.6), (0.16, 0.6, 1.4), "dark")
    # scattered slabs
    for _ in range(22):
        x, z = rng.uniform(-4.4, 4.4), rng.uniform(-4.4, 4.4)
        if abs(x) < 1.3 and z > 3.1:
            continue
        b.box((x, 0.05, z), (rng.uniform(0.4, 0.9), 0.1, rng.uniform(0.3, 0.7)),
              "stone", rot=(0, rng.uniform(0, 180), 0))
    # moss patches on floor and column bases
    for _ in range(26):
        x, z = rng.uniform(-4.6, 4.6), rng.uniform(-4.6, 4.6)
        b.box((x, 0.008, z), (rng.uniform(0.4, 1.0), 0.016, rng.uniform(0.4, 1.0)), "moss")
    # rubble - the bulk of the tri budget
    for _ in range(222):
        x, z = rng.uniform(-4.7, 4.7), rng.uniform(-4.7, 4.7)
        if abs(x) < 0.9 and z < -3.2:
            continue  # keep the entrance aisle clear
        r = rng.uniform(0.07, 0.30)
        b.sphere((x, r * 0.5, z), r, 8, 6, "dark" if rng.random() < 0.5 else "stone",
                 squash=(1, 0.6, 1), jitter=0.35, rng=rng)
    return b


MANIFEST = [
    "# cell.name: iseki",
    "# cell.version: 0",
    "# cell.ambient: 1.0,0.98,0.92,0.7",
    "# cell.keylight: 1.0,0.95,0.82,2.2 ; 2,7,-3",
    "# collider: -2.7,1.6,-2.0, 1.0,3.2,1.0",
    "# collider: -2.7,0.7,0.8, 1.0,1.4,1.0",
    "# collider: -2.7,1.4,3.4, 1.0,2.8,1.0",
    "# collider: 2.7,1.6,-2.0, 1.0,3.2,1.0",
    "# collider: 2.7,1.6,0.8, 1.0,3.2,1.0",
    "# collider: 2.7,0.5,3.4, 1.0,1.0,1.0",
    "# collider: -0.9,0.35,1.9, 2.4,0.7,0.7",
    "# collider: 1.6,0.35,3.6, 1.8,0.7,0.7",
    "# collider: 0,1.0,3.9, 1.8,2.0,1.2",
]


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "cells")
    b = build()
    tris = b.write_obj(os.path.join(out, "cell003.obj"), MANIFEST, "# CELL3 iseki - see PROTOTYPE_SPEC.md")
    make_atlas(os.path.join(out, "cell003.png"))
    print(f"cell003 verts={len(b.verts)} tris={tris}")
