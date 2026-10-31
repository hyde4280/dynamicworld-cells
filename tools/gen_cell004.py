#!/usr/bin/env python3
"""cell004 'suisho-doukutsu' - crystal cave, measurement tier ~50k tris.

This is the limit-probe cell (spec section 7): most small crystals and
rubble have no colliders on purpose; only the centerpiece and the big
rock pillars are solid. Expect the loader parse time to be the story here.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cellgen import CellBuilder, AtlasPainter, grid_regions

REGIONS = grid_regions(["rock", "crystal", "crystal2", "floor", "glow", "dark"], 3, 2)


def make_atlas(path):
    p = AtlasPainter(1024, REGIONS, seed=23)
    p.speckle("rock", (58, 56, 64), n=1800, amp=12)
    p.gradient("crystal", (190, 240, 255), (70, 150, 200), speckle_n=260)
    p.gradient("crystal2", (225, 200, 255), (130, 90, 200), speckle_n=260)
    p.speckle("floor", (44, 42, 50), n=1800, amp=10)
    p.gradient("glow", (240, 255, 250), (150, 210, 205), speckle_n=160)
    p.speckle("dark", (30, 29, 36), n=1200, amp=8)
    p.save(path)


def crystal(b, x, z, h, r, region, seg=6, tilt=(0, 0)):
    """Two-tier crystal: tapered shaft + cone tip, base at y=0."""
    hh = h * 0.55
    b.cylinder((x, hh / 2, z), r, r * 0.68, hh, seg, region, rot=(tilt[0], 0, tilt[1]))
    tip_y = hh + (h - hh) / 2
    cx = x - tilt[1] * 0.01 * hh
    b.cylinder((cx, tip_y, z), r * 0.68, 0.0, h - hh, seg, region, rot=(tilt[0], 0, tilt[1]))


def build():
    b = CellBuilder(REGIONS)
    rng = random.Random(404)
    # cave shell: rock walls h=6, ceiling slab, entrance gap on the south
    b.box((0, -0.05, 0), (10, 0.1, 10), "floor")
    b.box((0, 3, 4.9), (10, 6, 0.2), "rock")
    b.box((4.9, 3, 0), (0.2, 6, 10), "rock")
    b.box((-4.9, 3, 0), (0.2, 6, 10), "rock")
    b.box((-3, 3, -4.9), (4, 6, 0.2), "rock")
    b.box((3, 3, -4.9), (4, 6, 0.2), "rock")
    b.box((0, 4.5, -4.9), (2, 3, 0.2), "rock")
    b.box((0, 6.15, 0), (10, 0.3, 10), "dark")
    # stalactites
    for _ in range(90):
        x, z = rng.uniform(-4.7, 4.7), rng.uniform(-4.7, 4.7)
        h = rng.uniform(0.8, 2.1)
        b.cylinder((x, 6.0 - h / 2, z), 0.0, rng.uniform(0.14, 0.3), h, 7, "rock")
    # glowing pool disc at the center
    b.cylinder((0, 0.02, 0.6), 1.5, 1.5, 0.04, 24, "glow")
    # centerpiece crystal cluster
    crystal(b, 0, 0.6, 3.4, 0.55, "crystal", seg=10)
    crystal(b, 0.85, 0.1, 2.3, 0.4, "crystal2", seg=8, tilt=(6, 10))
    crystal(b, -0.8, 1.1, 2.0, 0.36, "crystal", seg=8, tilt=(-8, -6))
    crystal(b, -0.5, -0.3, 1.4, 0.28, "crystal2", seg=8, tilt=(4, -12))
    crystal(b, 0.6, 1.3, 1.2, 0.24, "crystal", seg=8, tilt=(10, 4))
    # rock pillars in the corners (stacked boulders)
    pillar_centers = [(-3.75, -3.7), (3.75, -3.7), (-3.75, 3.75), (3.75, 3.75)]
    for px, pz in pillar_centers:
        y = 0.0
        for s in (1.15, 0.9, 0.62):
            b.sphere((px + rng.uniform(-0.1, 0.1), y + s * 0.55, pz + rng.uniform(-0.1, 0.1)),
                     s * 0.8, 12, 9, "rock", squash=(1, 0.75, 1), jitter=0.22, rng=rng)
            y += s * 0.85
    # cave rocks along the walls - a large share of the tri budget
    for _ in range(160):
        side = rng.randrange(4)
        if side == 0:
            x, z = rng.uniform(-4.8, 4.8), rng.uniform(3.6, 4.6)
        elif side == 1:
            x, z = rng.uniform(-4.8, 4.8), rng.uniform(-4.6, -3.6)
        elif side == 2:
            x, z = rng.uniform(-4.6, -3.6), rng.uniform(-3.6, 3.6)
        else:
            x, z = rng.uniform(3.6, 4.6), rng.uniform(-3.6, 3.6)
        r = rng.uniform(0.35, 0.95)
        lim = 5.0 - r * 1.32
        x = max(-lim, min(lim, x))
        z = max(-lim, min(lim, z))
        b.sphere((x, r * 0.95, z), r, 12, 9, "rock", squash=(1, 0.7, 1), jitter=0.3, rng=rng)
    # crystal field
    for _ in range(350):
        x, z = rng.uniform(-4.6, 4.6), rng.uniform(-4.6, 4.6)
        if abs(x) < 0.85 and z > -3.6:
            continue  # entrance aisle
        d2 = (x) ** 2 + (z - 0.6) ** 2
        if d2 < 2.1 ** 2:
            continue  # keep the centerpiece clearing
        h = rng.uniform(0.25, 1.15)
        region = "crystal" if rng.random() < 0.65 else "crystal2"
        crystal(b, x, z, h, rng.uniform(0.07, 0.2), region, seg=6,
                tilt=(rng.uniform(-9, 9), rng.uniform(-9, 9)))
    # floor rubble
    for _ in range(90):
        x, z = rng.uniform(-4.7, 4.7), rng.uniform(-4.7, 4.7)
        if abs(x) < 0.85 and z > -3.6:
            continue
        r = rng.uniform(0.08, 0.26)
        b.sphere((x, r * 0.45, z), r, 8, 6, "dark", squash=(1, 0.6, 1), jitter=0.3, rng=rng)
    return b


MANIFEST = [
    "# cell.name: suisho-doukutsu",
    "# cell.version: 0",
    "# cell.ambient: 0.5,0.62,0.85,0.55",
    "# cell.keylight: 0.6,0.85,1.0,2.4 ; 0,4.5,0.5",
    "# collider: 0,1.2,0.6, 2.6,2.4,2.6",
    "# collider: -3.75,1.2,-3.7, 1.7,2.4,1.7",
    "# collider: 3.75,1.2,-3.7, 1.7,2.4,1.7",
    "# collider: -3.75,1.2,3.75, 1.7,2.4,1.7",
    "# collider: 3.75,1.2,3.75, 1.7,2.4,1.7",
]


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "cells")
    b = build()
    tris = b.write_obj(os.path.join(out, "cell004.obj"), MANIFEST, "# CELL4 suisho-doukutsu - see PROTOTYPE_SPEC.md")
    make_atlas(os.path.join(out, "cell004.png"))
    print(f"cell004 verts={len(b.verts)} tris={tris}")
