#!/usr/bin/env python3
"""Corridor cells rebuilt as mine tunnels with tools/minekit.py (2026-11-16).

cell006 cross (N/E/S/W), cell007 T (N/E/S), cell008 I (N/S), cell009 L (S/E),
cell014 offset cross (N/E/S/W). Floor plans, doors and wall colliders are the same
as the cave versions (gen_basic_cells / gen_variation_cells); only the look changes.

Usage: gen_mine_cells.py [cell number]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from minekit import Mine, make_atlas  # noqa: E402
from gen_variation_cells import CORRIDORS as OFFSET_CROSS  # noqa: E402

W = 1.5


def arm_sets(m, face, positions, lag=(), lantern=None, braces=True):
    """Timber sets across one 3 m arm; positions are distances from the cell centre."""
    axis = "z" if face in "NS" else "x"
    s = 1 if face in "NE" else -1
    for p in positions:
        m.timber_set(axis, s * p, -W, W, braces=braces)
    for a, b in lag:
        lo, hi = sorted((s * a, s * b))
        m.lagging(axis, lo, hi, -W, W)
    if lantern is not None:
        x, z = (0.0, s * lantern) if axis == "z" else (s * lantern, 0.0)
        m.lantern(x, z)


def cell006():
    m = Mine([(-W, W, -5, 5), (-5, 5, -W, W)], seed=6)
    m.floor()
    m.rock()
    m.worn(-0.7, 0.7, -5, 5)
    m.worn(-5, -0.7, -0.7, 0.7)
    m.worn(0.7, 5, -0.7, 0.7)
    for f in "NESW":
        m.door(f)
    arm_sets(m, "N", (1.85, 3.35), lag=[(1.85, 3.35)], lantern=3.35)
    arm_sets(m, "S", (1.85, 3.35), lag=[(1.85, 3.35)], lantern=3.35)
    arm_sets(m, "E", (1.85, 3.35), lantern=3.35)
    arm_sets(m, "W", (1.85, 3.35), lag=[(1.85, 3.35)])
    m.lantern(0, 0, top=3.5, intensity=2.2)          # junction, hung from the roof
    # west arm: the unlit one, used as a store
    m.crate(-3.0, 1.05, 0.62, ry=8)
    m.crate(-3.7, 1.1, 0.5, ry=-14)
    m.crate(-3.05, 1.08, 0.42, ry=30, y=0.62, collider=False)
    m.barrel(-2.3, -1.12)
    m.pickaxe(-4.2, -1.2, 0, -1)
    m.heap(1.25, 1.2, n=6, spread=0.3)
    m.rubble([(1.2, -2.6), (-1.25, 2.5), (2.7, -1.25), (-1.2, -4.1)])
    return m, m.manifest("jujiro-koudou", ["N", "E", "S", "W"])


def cell007():
    m = Mine([(-W, W, -5, 5), (W, 5, -W, W)], seed=7)
    m.floor()
    m.rock()
    m.worn(-0.7, 0.7, -5, 5)
    m.worn(0.7, 5, -0.7, 0.7)
    for f in "NES":
        m.door(f)
    arm_sets(m, "N", (1.85, 3.35), lag=[(1.85, 3.35)], lantern=1.85)
    arm_sets(m, "S", (1.85, 3.35), lag=[(1.85, 3.35)], lantern=3.35)
    arm_sets(m, "E", (1.85, 3.35), lantern=3.35)
    # the blind west wall of the junction: a half set against it
    m.timber_set("z", 0.0, -W, W, right=False, braces=False)
    m.planks(-1.05, -0.2, axis="z", n=5, length=2.2)
    m.barrel(-1.1, 1.25)
    m.heap(1.2, -1.15, n=5, spread=0.3)
    m.pickaxe(1.25, 2.6, 1, 0)
    m.rubble([(-1.25, -3.0), (2.4, 1.25), (1.2, 4.2)])
    return m, m.manifest("teijiro-koudou", ["N", "E", "S"])


def cell008():
    m = Mine([(-W, W, -5, 5)], seed=8)
    m.floor()
    m.rock()
    m.worn(-1.4, -0.3, -5, 5)                         # the walked line runs beside the track
    for f in "NS":
        m.door(f)
    zs = (-3.7, -2.2, -0.7, 0.8, 2.3, 3.8)
    for z in zs:
        m.timber_set("z", z, -W, W)
    m.lagging("z", -3.7, -2.2, -W, W)
    m.lagging("z", -0.7, 0.8, -W, W, keep=0.55)
    m.lagging("z", 2.3, 3.8, -W, W)
    m.lantern(0, -2.2)
    m.lantern(0, 2.3)
    # an abandoned length of track with a cart left on it
    m.rails("z", 0.62, -3.4, 3.3, missing=(3, 8))
    m.cart(0.62, 0.9)
    m.heap(1.15, -3.0, n=5, spread=0.28)
    m.rubble([(-1.25, 3.2), (1.3, 4.3), (-1.3, -1.5)])
    return m, m.manifest("ipponmichi-koudou", ["N", "S"])


def cell009():
    m = Mine([(-W, W, -5, W), (-W, 5, -W, W)], seed=9)
    m.floor()
    m.rock()
    m.worn(-0.7, 0.7, -5, 0.7)
    m.worn(0.7, 5, -0.7, 0.7)
    for f in "SE":
        m.door(f)
    arm_sets(m, "S", (1.85, 3.35), lag=[(1.85, 3.35)], lantern=3.35)
    arm_sets(m, "E", (1.85, 3.35), lag=[(1.85, 3.35)], lantern=3.35)
    # the corner itself: caps on the two blind walls
    m.timber_set("z", 0.2, -W, W, right=False)
    m.timber_set("x", -0.2, -W, W, left=False)
    m.lantern(-0.2, 0.2, top=3.5, intensity=1.6)
    m.crate(-1.05, 1.02, 0.6, ry=5)
    m.crate(-0.4, 1.1, 0.46, ry=-20)
    m.heap(-1.15, -1.0, n=5, spread=0.25)
    m.rubble([(1.25, -2.4), (2.5, 1.25), (-1.25, -4.2)])
    return m, m.manifest("magarimichi-koudou", ["S", "E"])


def cell014():
    m = Mine(OFFSET_CROSS, seed=14)
    m.floor()
    m.rock()
    m.pillar(-0.5, 0.0, 0.0, 1.0)                     # the thin rock between the jog and the plaza
    m.worn(-0.7, 0.7, 2.0, 5.0)
    m.worn(0.3, 3.4, 0.4, 1.6)
    m.worn(1.9, 3.4, -3.0, 0.4)
    m.worn(-0.7, 3.4, -3.9, -3.0)
    m.worn(-0.7, 0.7, -5.0, -3.9)
    m.worn(3.4, 5.0, -0.7, 0.7)
    m.worn(-5.0, -3.0, -0.7, 0.7)
    m.worn(-3.0, -0.7, 0.6, 1.9)
    for f in "NESW":
        m.door(f)
    m.timber_set("z", 3.0, -W, W)
    m.timber_set("z", 4.2, -W, W)
    m.lagging("z", 3.0, 4.2, -W, W)
    m.timber_set("z", -4.45, -W, W)
    m.timber_set("x", 4.45, -W, W)
    m.timber_set("x", -4.3, -W, W)
    m.timber_set("z", -2.0, 1.5, 4.0)                 # across the descent band
    m.timber_set("x", -2.3, 0.0, 3.0)                 # across the west jog
    m.lantern(0, 3.0)
    m.lantern(2.75, -2.0)
    m.lantern(-2.3, 1.5)
    m.lantern(2.0, 1.0, top=3.5, intensity=1.8)       # north plaza
    m.crate(3.55, 1.55, 0.6, ry=10)
    m.barrel(3.6, -3.55)
    m.heap(0.45, -2.95, n=5, spread=0.25)
    m.pickaxe(-0.9, 2.7, 0, 1)
    m.rubble([(1.3, 4.4), (-2.9, 2.6), (3.7, -0.9), (-4.2, -1.2)])
    return m, m.manifest("kuichigai-jujiro-koudou", ["N", "E", "S", "W"])


CELLS = [(6, cell006), (7, cell007), (8, cell008), (9, cell009), (14, cell014)]

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "cells")
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    for num, fn in CELLS:
        if only is not None and num != only:
            continue
        m, manifest = fn()
        tris = m.b.write_obj(os.path.join(out, f"cell{num:03d}.obj"), manifest,
                             f"# CELL{num} mine tunnel (minekit) - see MULTI_CELL_SPEC.md (dynamicworld)")
        make_atlas(os.path.join(out, f"cell{num:03d}.png"), seed=600 + num)
        print(f"cell{num:03d}: tris={tris} colliders={len(m.colliders)} lights={len(m.all_lights())} props={len(m.props)}")
