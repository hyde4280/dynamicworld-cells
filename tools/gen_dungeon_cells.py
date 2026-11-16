#!/usr/bin/env python3
"""Room cells for the mine01 dungeon (dynamicworld docs/DUNGEON_DESIGN.md), 2026-11-16.

cell016 hokora  (shrine, dead end: door S)      - altar with a `# switch:` point
cell017 hiroma  (hall: doors N/S)               - pillars, `# spawn:` points
cell018 takibi  (campfire: doors N/S)           - `# cell.save: 1`

Same construction rules as the cave cells (gen_basic_cells / gen_variation_cells):
the 10 m square is solid rock, the walkable space is carved out of it, door openings
are the standard 2 m x 3 m at the face centres behind a 3 m wide, 4 m high arm (so
`Cave.door` dressing, host gates and rim colliders stay standard).

Unlike the corridor cells the rooms have different ceiling heights per area. Every
open rect carries its own ceiling height; the rock and the ceiling boxes all end at
TOP, so a higher room next to a lower arm is closed by the side of the arm's ceiling
box. TOP stays below the 6 m vertical pitch (the cell above starts at y = 6).

`# switch:` and `# spawn:` are proposed manifest lines (DUNGEON_DESIGN.md section 4.1).
Loaders that do not know them skip the lines.

Usage: gen_dungeon_cells.py [cell number]
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atlas_common import REGIONS_HALF, make_atlas_rock  # noqa: E402
from gen_basic_cells import Cave, _rect_subtract, _n, dark_mine  # noqa: E402
from gen_variation_cells import rock_complement, collider_rects  # noqa: E402

TOP = 5.6          # top of the rock and of every ceiling box
WARM = (1.0, 0.72, 0.42)


class Room(Cave):
    def __init__(self):
        super().__init__(REGIONS_HALF)
        self._open = []      # (x0, x1, z0, z1)
        self.extra = []      # manifest lines after the standard block
        self.tiling = ("rock", 2.0, REGIONS_HALF["rock"])
        dark_mine(self)

    def open_area(self, x0, x1, z0, z1, ceil_y, path=True):
        """Carve a walkable rect with its own ceiling height. Rects may overlap:
        the part already carved keeps its first ceiling."""
        rects = [(x0, x1, z0, z1)]
        for placed in self._open:
            nxt = []
            for r in rects:
                nxt += _rect_subtract(r, placed)
            rects = nxt
        self._open.append((x0, x1, z0, z1))
        for (a0, a1, b0, b1) in rects:
            cx, cz = (a0 + a1) / 2, (b0 + b1) / 2
            if path:
                self.b.box((cx, 0.011, cz), (a1 - a0, 0.022, b1 - b0), "path",
                           skip=("bottom", "px", "nx", "pz", "nz"))
            self.b.box((cx, (ceil_y + TOP) / 2, cz), (a1 - a0, TOP - ceil_y, b1 - b0),
                       "rock", skip=("top",))

    def close_rock(self):
        """Rock = exact complement of the open rects (no overlapping boxes), plus
        the colliders along the walls."""
        for (x0, x1, z0, z1, _touch) in rock_complement(self._open):
            self.rock_block(x0, x1, z0, z1, h=TOP, collider=False)
        for (x0, x1, z0, z1) in collider_rects(self._open):
            self.colliders.append(((x0 + x1) / 2, TOP / 2, (z0 + z1) / 2,
                                   x1 - x0, TOP, z1 - z0))

    def solid(self, center, size, region, skip=("bottom",), collider=True):
        self.b.box(center, size, region, skip=skip)
        if collider:
            self.colliders.append((center[0], center[1], center[2],
                                   size[0], size[1], size[2]))

    def light(self, x, y, z, intensity, flicker, rgb=WARM):
        self.lights.append((x, y, z, rgb[0], rgb[1], rgb[2], intensity, flicker))

    def keylight(self):
        x, y, z, r, g, b, inten, _ = self.lights[0]
        return f"{_n(r)},{_n(g)},{_n(b)},{_n(inten)} ; {_n(x)},{_n(y)},{_n(z)}"

    def stones(self, pts, rmin=0.16, rmax=0.30, seed=7):
        rng = random.Random(seed)
        for x, z in pts:
            self.b.sphere((x, 0.10, z), rng.uniform(rmin, rmax), 7, 5, "rock",
                          squash=(1, 0.6, 1), jitter=0.3, rng=rng)

    def finish(self, name, ambient, doors):
        m = self.manifest(name, ambient, self.keylight(), doors)
        # extras go before the collider block so the header stays readable
        k = next((i for i, ln in enumerate(m) if ln.startswith("# collider:")), len(m))
        return m[:k] + self.extra + m[k:]


# ---------------------------------------------------------------------------
# cell016: shrine. A 7 m x 6.5 m chamber behind the south arm, with a low
# alcove in the north wall holding the altar. The switch point sits in front
# of the altar (the host places the FlagSwitch there; the flag number is the
# world definition's business).
# ---------------------------------------------------------------------------
def cell016():
    c = Room()
    b = c.b
    c.floor_slab()
    c.open_area(-1.5, 1.5, -5.0, -3.0, 4.0)              # south arm
    c.open_area(-3.5, 3.5, -3.0, 3.5, 5.0, path=False)   # chamber (stone floor)
    c.open_area(-1.5, 1.5, 3.5, 4.5, 3.6, path=False)    # altar alcove
    c.close_rock()
    c.door("S")
    # worn strip from the door to the altar
    b.box((0, 0.011, 0.25), (1.6, 0.022, 6.5), "path",
          skip=("bottom", "px", "nx", "pz", "nz"))
    # altar: stone block with an ember bowl
    c.solid((0, 0.45, 4.0), (1.8, 0.9, 0.7), "floor")
    b.box((0, 0.94, 4.0), (2.0, 0.08, 0.86), "wood")                 # altar top board
    b.cylinder((0, 1.08, 4.0), 0.14, 0.24, 0.2, 8, "wood", cap=False)  # bowl
    b.cylinder((0, 1.2, 4.0), 0.2, 0.0, 0.32, 6, "glow", cap=False)    # ember
    c.light(0, 1.35, 3.9, 1.6, 0.5)
    # gate frame in front of the alcove (posts clear of the alcove jambs)
    for s in (-1, 1):
        b.box((s * 1.25, 1.65, 3.3), (0.24, 3.3, 0.24), "wood", skip=("bottom",))
        c.colliders.append((s * 1.25, 1.65, 3.3, 0.24, 3.3, 0.24))
    b.box((0, 3.25, 3.3), (3.4, 0.22, 0.3), "wood")
    b.box((0, 2.8, 3.3), (2.9, 0.14, 0.2), "wood")
    # two columns halfway down the chamber
    for s in (-1, 1):
        b.cylinder((s * 2.3, 2.52, -0.8), 0.38, 0.30, 5.04, 8, "rock", cap=False)
        c.colliders.append((s * 2.3, 2.5, -0.8, 0.66, 5.0, 0.66))
        b.box((s * 2.3, 0.15, -0.8), (1.0, 0.3, 1.0), "floor", skip=("bottom",))
    # stone tablet on the west wall (place for the inscription)
    c.solid((-3.42, 0.8, 1.6), (0.2, 1.6, 1.1), "floor")
    c.lantern(-3.5, -1.9, 1, 0)
    c.lantern(3.5, 1.2, -1, 0)
    c.crystals(-2.9, 3.0, n=3)
    c.crystals(2.9, 3.0, n=2)
    c.stalactites([(-2.6, 1.9), (2.4, -2.2), (0.6, 0.4)], ceil_y=5.0)
    c.stones([(3.1, -2.6), (-3.0, -2.5), (1.3, -4.1)])
    c.extra.append("# switch: 0,1.05,3.45")
    return c, c.finish("hokora-no-ma", "0.62,0.58,0.52,0.5", ["S"])


# ---------------------------------------------------------------------------
# cell017: hall. One 8.4 m square room, 5.3 m high, four pillars as cover.
# Spawn points: the centre and the four corners behind the pillars.
# ---------------------------------------------------------------------------
def cell017():
    c = Room()
    b = c.b
    c.floor_slab()
    c.open_area(-1.5, 1.5, -5.0, -4.2, 4.0)              # south arm
    c.open_area(-1.5, 1.5, 4.2, 5.0, 4.0)                # north arm
    c.open_area(-4.2, 4.2, -4.2, 4.2, 5.3, path=False)   # hall
    c.close_rock()
    for f in ("N", "S"):
        c.door(f)
    # worn floor: the way through and the centre
    b.box((0, 0.011, 0), (1.6, 0.022, 8.4), "path", skip=("bottom", "px", "nx", "pz", "nz"))
    for s in (-1, 1):
        b.box((s * 1.3, 0.011, 0), (1.0, 0.022, 2.6), "path",
              skip=("bottom", "px", "nx", "pz", "nz"))
    # pillars (into the ceiling, no top/bottom faces)
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * 2.3, sz * 2.3
            b.box((x, 2.7, z), (0.9, 5.4, 0.9), "rock", skip=("bottom", "top"))
            c.colliders.append((x, 2.65, z, 0.9, 5.3, 0.9))
            b.box((x, 0.2, z), (1.3, 0.4, 1.3), "floor", skip=("bottom",))
            c.colliders.append((x, 0.2, z, 1.3, 0.4, 1.3))
    # mine timbering under the ceiling
    for z in (-2.3, 2.3):
        b.box((0, 5.2, z), (8.6, 0.26, 0.3), "wood", skip=("top", "px", "nx"))
    for x in (-2.3, 2.3):
        b.box((x, 4.98, 0), (0.26, 0.18, 8.6), "wood", skip=("pz", "nz"))
    c.lantern(-4.2, 2.3, 1, 0)
    c.lantern(4.2, -2.3, -1, 0)
    c.lantern(-4.2, -2.3, 1, 0)
    c.lantern(4.2, 2.3, -1, 0)
    c.stalactites([(0, 0), (-3.4, 0.3), (3.3, -0.4), (0.4, 3.3), (-0.5, -3.4)], ceil_y=5.3)
    c.stalagmites([(-3.8, 3.8), (3.8, -3.8)])
    c.crystals(3.6, 3.7, n=3)
    c.stones([(-3.6, -3.5), (1.2, 3.8), (-1.3, -3.9), (3.7, 0.9), (-3.8, -0.8)])
    c.extra += ["# spawn: 0,0,0", "# spawn: 3.3,0,3.3", "# spawn: -3.3,0,3.3",
                "# spawn: 3.3,0,-3.3", "# spawn: -3.3,0,-3.3"]
    return c, c.finish("hiroma", "0.60,0.56,0.50,0.5", ["N", "S"])


# ---------------------------------------------------------------------------
# cell018: campfire (save point). A 6 m square chamber with two low sleeping
# niches; the fire sits in the centre, so the way through goes around it.
# ---------------------------------------------------------------------------
def cell018():
    c = Room()
    b = c.b
    c.floor_slab()
    c.open_area(-1.5, 1.5, -5.0, -3.0, 4.0)              # south arm
    c.open_area(-1.5, 1.5, 3.0, 5.0, 4.0)                # north arm
    c.open_area(-3.0, 3.0, -3.0, 3.0, 4.6)               # chamber (dirt floor)
    c.open_area(-4.2, -3.0, -1.5, 1.5, 3.0)              # west niche
    c.open_area(3.0, 4.2, -1.5, 1.5, 3.0)                # east niche
    c.close_rock()
    for f in ("N", "S"):
        c.door(f)
    # the fire: stone ring, three leaning logs, flame
    import math
    rng = random.Random(18)
    for k in range(9):
        a = 2 * math.pi * k / 9
        b.sphere((0.62 * math.sin(a), 0.09, 0.62 * math.cos(a)), rng.uniform(0.13, 0.19),
                 6, 4, "rock", squash=(1, 0.7, 1), jitter=0.25, rng=rng)
    for k in range(3):
        ry = 120 * k + 15
        a = math.radians(ry)
        b.cylinder((0.2 * math.sin(a), 0.2, 0.2 * math.cos(a)), 0.07, 0.06, 0.8, 6,
                   "wood", rot=(62, ry, 0))
    b.cylinder((0, 0.48, 0), 0.26, 0.0, 0.8, 7, "glow", cap=False)
    b.cylinder((0.05, 0.36, -0.04), 0.34, 0.05, 0.5, 7, "glow", cap=False)
    c.colliders.append((0, 0.3, 0, 1.3, 0.6, 1.3))
    c.light(0, 0.8, 0, 3.0, 0.6, rgb=(1.0, 0.62, 0.3))
    # log benches either side of the fire
    for s in (-1, 1):
        b.cylinder((s * 1.7, 0.22, 0), 0.22, 0.22, 1.7, 8, "wood", rot=(90, 0, 0))
        c.colliders.append((s * 1.7, 0.22, 0, 0.44, 0.44, 1.7))
    # west niche: bedroll; east niche: crates
    b.box((-3.65, 0.07, 0), (0.8, 0.14, 1.9), "wood", skip=("bottom",))
    b.box((-3.65, 0.2, 0.75), (0.7, 0.16, 0.36), "path")
    c.solid((3.7, 0.3, -0.7), (0.6, 0.6, 0.6), "wood")
    c.solid((3.65, 0.35, 0.3), (0.7, 0.7, 0.7), "wood")
    b.box((3.7, 0.85, -0.2), (0.5, 0.5, 0.5), "wood", rot=(0, 20, 0), skip=("bottom",))
    c.lantern(-3.0, 2.3, 1, 0)
    c.lantern(3.0, -2.3, -1, 0)
    c.stalactites([(-2.2, -2.3), (2.3, 2.2), (0.9, -2.0)], ceil_y=4.6)
    c.stalagmites([(-2.6, 2.6)])
    c.stones([(2.6, -2.6), (-2.5, -1.9), (1.2, 4.2)], seed=11)
    c.extra.append("# cell.save: 1")
    return c, c.finish("takibi-no-ma", "0.64,0.57,0.48,0.5", ["N", "S"])


# ---------------------------------------------------------------------------
# cell019: ending / dawn hall (dead end: door S). A calm, bright 8.4 m x 7.2 m
# room, the reward after the last key: warm light, long sight, shafts of light
# (pale vertical quads, visual only). A round dais in the centre carries a
# pedestal with an unlit stone bowl: the ember is placed there. The switch point
# is the bowl (the host places the FlagSwitch; the flag number is the world
# definition's business, e0 switch=6 in mine01).
# ---------------------------------------------------------------------------
def cell019():
    c = Room()
    b = c.b
    # bright room: high base light, long sight distance (the mine cells use 0.12 / 3..10)
    c.baselight = 0.45
    c.fog = (12.0, 40.0)
    c.floor_slab()
    c.open_area(-1.5, 1.5, -5.0, -3.0, 4.0)              # south arm
    c.open_area(-4.2, 4.2, -3.0, 4.2, 5.4, path=False)   # hall (stone floor)
    c.close_rock()
    c.door("S")
    # worn strip from the door to the dais
    b.box((0, 0.011, -2.5), (1.6, 0.022, 1.0), "path",
          skip=("bottom", "px", "nx", "pz", "nz"))
    # dais: two low round inlays (visual; the floor stays at 0)
    b.cylinder((0, 0.04, 0), 2.1, 2.1, 0.08, 24, "floor", cap=True)
    b.cylinder((0, 0.1, 0), 1.5, 1.5, 0.12, 24, "path", cap=True)
    # pedestal and stone bowl (the ember goes in here), unlit
    b.cylinder((0, 0.4, 0), 0.5, 0.36, 0.7, 12, "rock", cap=False)
    c.colliders.append((0, 0.4, 0, 0.9, 0.8, 0.9))
    b.cylinder((0, 0.88, 0), 0.34, 0.5, 0.3, 12, "rock", cap=False)     # bowl
    b.cylinder((0, 0.9, 0), 0.3, 0.3, 0.02, 12, "soot" if "soot" in b.regions else "wood", cap=True)  # dark bowl floor
    # four shafts of light: crossed thin glow quads from the ceiling, a patch on the floor
    for (x, z) in ((-2.9, 2.3), (2.9, 2.3), (-2.9, -1.4), (2.9, -1.4)):
        b.box((x, 2.7, z), (0.8, 5.3, 0.03), "glow", skip=("top", "bottom"))
        b.box((x, 2.7, z), (0.03, 5.3, 0.8), "glow", skip=("top", "bottom"))
        b.box((x, 0.03, z), (1.0, 0.01, 1.0), "glow", skip=("bottom", "px", "nx", "pz", "nz"))
    # crates, rubble, crystals
    c.solid((3.6, 0.3, 3.5), (0.6, 0.6, 0.6), "wood")
    c.solid((3.5, 0.35, 2.8), (0.7, 0.7, 0.7), "wood")
    b.box((3.6, 0.85, 3.4), (0.5, 0.5, 0.5), "wood", rot=(0, 20, 0), skip=("bottom",))
    c.solid((-3.6, 0.3, -2.3), (0.6, 0.6, 0.6), "wood")
    c.crystals(-3.5, 3.5, n=3)
    c.crystals(3.6, -2.2, n=2)
    c.crystals(0.0, 3.8, n=3)
    c.stalagmites([(-3.8, 0.4), (3.8, 0.6)])
    c.stones([(-3.0, 3.4), (2.6, 3.6), (-1.3, -2.6), (1.5, -2.7), (3.7, 1.2), (-3.7, -0.6)], seed=19)
    # warm light: the dawn at the centre and over the two corners
    c.light(0, 3.6, 0, 1.8, 0.0, rgb=(1.0, 0.88, 0.62))
    c.light(-3.0, 3.2, 2.3, 1.2, 0.0, rgb=(1.0, 0.9, 0.7))
    c.light(3.0, 3.2, 2.3, 1.2, 0.0, rgb=(1.0, 0.9, 0.7))
    c.light(0, 3.0, -3.8, 0.9, 0.0, rgb=(1.0, 0.86, 0.6))
    c.extra.append("# switch: 0,1.0,0")
    return c, c.finish("asa-no-ma", "0.86,0.80,0.68,0.55", ["S"])


CELLS = [(16, cell016), (17, cell017), (18, cell018), (19, cell019)]
HEADERS = {19: "# CELL19 dungeon room (ending, dawn hall) - see DUNGEON_DESIGN.md (dynamicworld)",
16: "# CELL16 dungeon room (shrine) - see DUNGEON_DESIGN.md (dynamicworld)",
           17: "# CELL17 dungeon room (hall) - see DUNGEON_DESIGN.md (dynamicworld)",
           18: "# CELL18 dungeon room (campfire, save point) - see DUNGEON_DESIGN.md (dynamicworld)"}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "cells")
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    for num, fn in CELLS:
        if only is not None and num != only:
            continue
        room, manifest = fn()
        ntris = len(room.b.faces)
        k = next(i for i, ln in enumerate(manifest) if ln.startswith("# door:"))
        manifest.insert(k, f"# cell.tris: {ntris}")
        room.b.write_obj(os.path.join(out, f"cell{num:03d}.obj"), manifest, HEADERS[num])
        make_atlas_rock(os.path.join(out, f"cell{num:03d}.png"), seed=600 + num)
        print(f"cell{num:03d}: tris={ntris} colliders={len(room.colliders)}")
