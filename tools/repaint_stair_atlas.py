#!/usr/bin/env python3
"""Repaint the atlas PNGs of the stair cells 010 / 011 in place (2026-11-16).

Both cells were hand-patched and have no generator. Their atlas uses the 3x2 grid
layout grid_regions(["rock","floor","path","wood","crystal","glow"], 3, 2) of
gen_basic_cells.py (top row rock / floor / path, bottom row wood / crystal / glow;
512x512). The old "blobs" rock painter gave saturated camouflage patches and the
floor/path had per-channel colour speckle. This script keeps the layout (so the OBJ
UVs and geometry are untouched) and repaints only rock / floor / path:
  rock  = CC0 rock photo, graded like the tunnel cells (atlas_common.rock_photo)
  floor, path = calm luminance-only stone / packed dirt (paint_calm_floor_path)
wood / crystal / glow are left as they are. Idempotent: the same pixels come out
every run (seeded, deterministic).

The CC0 photo (tools/assets/rock_boulder_cracked_diff_1k.jpg.b64) is decoded to a
temporary .jpg only while running and deleted afterwards (the .jpg is not committed).

Usage: repaint_stair_atlas.py [cells dir]
"""
import base64
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cellgen import AtlasPainter, grid_regions  # noqa: E402
from atlas_common import rock_photo, paint_calm_floor_path  # noqa: E402

REGIONS = grid_regions(["rock", "floor", "path", "wood", "crystal", "glow"], 3, 2)


def repaint(path, seed):
    p = AtlasPainter(512, REGIONS, seed=seed)
    p.img = Image.open(path).convert("RGB")      # keep wood / crystal / glow
    p.d = ImageDraw.Draw(p.img)
    rock_photo(p)
    paint_calm_floor_path(p, seed)
    p.save(path)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "cells")
    assets = os.path.join(here, "assets")
    jpg = os.path.join(assets, "rock_boulder_cracked_diff_1k.jpg")
    had = os.path.exists(jpg)
    if not had:
        with open(jpg + ".b64") as f:
            data = base64.b64decode("".join(f.read().split()))
        with open(jpg, "wb") as f:
            f.write(data)
    try:
        for n in (10, 11):
            repaint(os.path.join(out, f"cell{n:03d}.png"), seed=600 + n)
            print(f"cell{n:03d}.png repainted")
    finally:
        if not had:
            os.remove(jpg)


if __name__ == "__main__":
    main()
