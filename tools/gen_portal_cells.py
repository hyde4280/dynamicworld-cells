#!/usr/bin/env python3
"""cell012 / cell013: ladder-looking vertical pair for `kind=portal` (2026-11-15).

The player does not climb: a click on the interact point teleports to the
other cell (dynamicworld spec section 17). The look is a wooden ladder
standing against the north wall, rising through a square hatch in the
ceiling of cell012 / floor of cell013.

Headroom rule (found in the 6 m pitch tests): a portal arrival point must
leave 2 m or more of clearance under the cell above. Both portal points
are on the floor (y=0), so arriving from either side is always standing
height. The previous cell012 arrived at y=4.6 under the 6.0 floor of cell013
and pushed the player back up.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_basic_cells import Cave, make_atlas  # noqa: E402

H = 6.0
LX, LZ = 0.0, 4.62            # ladder axis
HX0, HX1, HZ0 = -0.65, 0.65, 4.15   # hatch x range, south edge (north edge is the wall)
PORTAL = (0.0, 0.0, 3.7)      # floor point in front of the ladder (both cells)
WH = H - 0.02                 # wall tops stay below the 6.0 floor of the cell above
RIM = 4.8                     # inner face of the rim walls


def walls(c, gaps):
    """Rock rim walls (visual only; the host slot guards the rim). gaps is a set
    of faces with a 2 m x 3 m door: N / S."""
    b = c.b
    for face in ("N", "S"):
        z = RIM + 0.1 if face == "N" else -(RIM + 0.1)
        if face in gaps:
            b.box((-3.0, WH / 2, z), (4.0, WH, 0.2), "rock", skip=("bottom",))
            b.box((3.0, WH / 2, z), (4.0, WH, 0.2), "rock", skip=("bottom",))
            b.box((0, 3.0 + (WH - 3.0) / 2, z), (2.08, WH - 3.0, 0.2), "rock", skip=("bottom",))
            for s in (-1, 1):
                b.box((s * 1.12, 1.56, z + (0.02 if face == "S" else -0.02)), (0.2, 3.12, 0.3), "wood", skip=("bottom",))
            b.box((0, 3.3, z + (0.02 if face == "S" else -0.02)), (2.4, 0.6, 0.3), "wood")
        else:
            b.box((0, WH / 2, z), (10.0, WH, 0.2), "rock", skip=("bottom",))
    for sx in (-1, 1):
        b.box((sx * (RIM + 0.1), WH / 2, 0), (0.2, WH, 9.6), "rock", skip=("bottom",))


def ceiling_with_hatch(c, top, thick, margin=0.0, span=RIM):
    """Slab (ceiling of cell012 / floor of cell013) as boxes around the hatch. The hatch
    touches the north wall. margin / span differ between the two cells so that the side
    faces of the stacked slabs are not coplanar (Z-fighting between cells)."""
    b = c.b
    y = top - thick / 2
    x0, x1, z0 = HX0 - margin, HX1 + margin, HZ0 + margin
    b.box(((-span + x0) / 2, y, 0), (x0 + span, thick, 2 * span), "rock")
    b.box(((span + x1) / 2, y, 0), (span - x1, thick, 2 * span), "rock")
    b.box((0, y, (-span + z0) / 2), (x1 - x0, thick, z0 + span), "rock")


def ladder(c, y0, y1, rail_w=0.07, skip_bottom=False):
    b = c.b
    h = y1 - y0
    for s in (-1, 1):
        b.box((LX + s * 0.25, y0 + h / 2, LZ), (rail_w, h, rail_w), "wood",
              skip=("bottom",) if skip_bottom else ())
    y = y0 + 0.3
    while y < y1 - 0.05:
        b.box((LX, y, LZ), (0.5, 0.05, 0.05), "wood")
        y += 0.3


def cell012():
    c = Cave()
    b = c.b
    b.box((0, -0.05, 0), (10, 0.1, 10), "floor", skip=("bottom",))
    b.box((0, 0.011, -0.45), (2.4, 0.022, 8.7), "path", skip=("bottom", "px", "nx", "pz", "nz"))
    walls(c, {"S"})
    # ceiling slab 5.68..5.98: its top stays below the floor top (6.0) of cell013
    ceiling_with_hatch(c, H - 0.02, 0.3)
    ladder(c, 0.0, H - 0.02)
    # tied to the rim wall by two brackets
    for y in (1.8, 4.2):
        b.box((LX, y, LZ + 0.1), (0.62, 0.06, 0.12), "wood")
    b.box((LX, 0.02, LZ - 0.0), (0.9, 0.04, 0.5), "path")   # worn spot at the ladder foot
    c.lantern(-RIM, -0.5, 1, 0)
    c.lantern(RIM, 1.5, -1, 0)
    c.stalagmites([(-3.4, -3.2), (3.5, -2.6)])
    c.crystals(-3.8, 2.8)
    c.rubble([(3.2, 3.0), (-2.6, -1.6)])
    m = c.manifest("hashigo-no-doukutsu-portal", "0.6,0.66,0.8,0.55",
                   "0.85,0.92,1.0,1.9 ; 0,4.4,-1", ["S", "U, portal"])
    m.append("# portal: U, %s,%s,%s" % PORTAL)
    return c, m


def cell013():
    c = Cave()
    b = c.b
    # floor slab -0.1..0 as boxes around the hatch (so the hole is visible)
    ceiling_with_hatch(c, 0.0, 0.1, margin=0.03, span=RIM + 0.05)
    b.box((0, 0.011, -0.45), (2.4, 0.022, 8.7), "path", skip=("bottom", "px", "nx", "pz", "nz"))
    walls(c, {"N", "S"})
    b.box((0, H - 0.17, 0), (9.6, 0.3, 9.6), "rock")      # ceiling slab 5.68..5.98
    # hatch frame
    b.box((HX0 - 0.06, 0.03, (HZ0 + RIM) / 2), (0.12, 0.06, RIM - HZ0), "wood")
    b.box((HX1 + 0.06, 0.03, (HZ0 + RIM) / 2), (0.12, 0.06, RIM - HZ0), "wood")
    b.box((0, 0.03, HZ0 - 0.06), (HX1 - HX0 + 0.24, 0.06, 0.12), "wood")
    # the ladder comes up through the hatch, 1.1 m above the floor
    ladder(c, 0.0, 1.1, rail_w=0.07, skip_bottom=True)
    c.lantern(-RIM, 0.0, 1, 0)
    c.lantern(RIM, -1.5, -1, 0)
    c.crystals(3.6, 3.2)
    c.stalagmites([(-3.5, 3.0), (3.4, -3.0)])
    c.rubble([(-2.8, -2.4), (2.4, 1.2)])
    m = c.manifest("hashigo-no-ue-portal", "0.6,0.66,0.8,0.55",
                   "0.85,0.92,1.0,1.7 ; 0,3.2,0", ["N", "S", "D, portal"])
    m.append("# portal: D, %s,%s,%s" % PORTAL)
    return c, m


CELLS = [(12, cell012), (13, cell013)]

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "cells")
    for num, fn in CELLS:
        cave, manifest = fn()
        tris = cave.b.write_obj(
            os.path.join(out, f"cell{num:03d}.obj"), manifest,
            f"# CELL{num} ladder portal pair - see MULTI_CELL_DESIGN.md (dynamicworld)")
        make_atlas(os.path.join(out, f"cell{num:03d}.png"), seed=600 + num)
        print(f"cell{num:03d}: tris={tris} colliders={len(cave.colliders)}")
