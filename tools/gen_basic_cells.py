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


def _rect_subtract(rect, other):
    """rect minus other (axis-aligned, (x0,x1,z0,z1)); returns sub-rects."""
    x0, x1, z0, z1 = rect
    a0, a1, b0, b1 = other
    ix0, ix1 = max(x0, a0), min(x1, a1)
    iz0, iz1 = max(z0, b0), min(z1, b1)
    if ix0 >= ix1 or iz0 >= iz1:
        return [rect]
    out = []
    if x0 < ix0:
        out.append((x0, ix0, z0, z1))
    if ix1 < x1:
        out.append((ix1, x1, z0, z1))
    if z0 < iz0:
        out.append((ix0, ix1, z0, iz0))
    if iz1 < z1:
        out.append((ix0, ix1, iz1, z1))
    return out


class Cave:
    def __init__(self):
        self.b = CellBuilder(REGIONS)
        self.colliders = []
        self.portals = []   # (face, x, y, z): interact floor points for stacked cells
        self._corridor_rects = []

    # -- pieces ---------------------------------------------------------
    def rock_block(self, x0, x1, z0, z1, h=4.0, collider=True):
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        self.b.box((cx, h / 2, cz), (x1 - x0, h, z1 - z0), "rock",
                   skip=("bottom",))
        if collider:
            self.colliders.append((cx, h / 2, cz, x1 - x0, h, z1 - z0))

    def wall(self, cx, cz, sx, sz, h=4.0):
        self.b.box((cx, h / 2, cz), (sx, h, sz), "rock", skip=("bottom",))

    def corridor(self, x0, x1, z0, z1, ceil_y=4.0):
        # Tile against previously placed corridors: arms overlap at
        # junctions (cross/T/L), and the duplicated path/ceiling faces
        # in the junction square Z-fight. Subtract placed rects first.
        rects = [(x0, x1, z0, z1)]
        for placed in self._corridor_rects:
            nxt = []
            for r in rects:
                nxt += _rect_subtract(r, placed)
            rects = nxt
        self._corridor_rects.append((x0, x1, z0, z1))
        for (a0, a1, b0, b1) in rects:
            cx, cz = (a0 + a1) / 2, (b0 + b1) / 2
            # path slab: top face only. Its 2.2cm side slivers are
            # coplanar with the neighbouring rock/door faces and
            # Z-fight in thin strips; they carry no visible surface.
            self.b.box((cx, 0.011, cz), (a1 - a0, 0.022, b1 - b0), "path",
                       skip=("bottom", "px", "nx", "pz", "nz"))
            self.b.box((cx, ceil_y + 0.15, cz), (a1 - a0, 0.3, b1 - b0),
                       "rock")

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
                b.box((cx, 1.5, z), (0.5, 3.0, 0.3), "rock", skip=("bottom",))
                self.colliders.append((cx, 1.5, z, 0.5, 3.0, 0.3))
                # post top at 3.12, not 3.0: coplanar with the rock
                # segment tops it Z-fought (both up-facing at y=3.0)
                b.box((s * 1.3, 1.56, zp), (0.22, 3.12, 0.3), "wood", skip=("bottom",))
            b.box((0, 3.3, z), (3.0, 0.6, 0.3), "wood")
            b.box((0, 3.85, z), (3.0, 0.3, 0.3), "rock")
        else:
            x = 4.83 if face == "E" else -4.83
            xp = 4.8 if face == "E" else -4.8
            for s in (-1, 1):
                cz = s * 1.25
                b.box((x, 1.5, cz), (0.3, 3.0, 0.5), "rock", skip=("bottom",))
                self.colliders.append((x, 1.5, cz, 0.3, 3.0, 0.5))
                b.box((xp, 1.56, s * 1.3), (0.3, 3.12, 0.22), "wood", skip=("bottom",))
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
        self.b.box((0, -0.05, 0), (10, 0.1, 10), "floor", skip=("bottom",))

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


# Stair rooms (cell010 / cell011): the D/U opening of kind "stair" is a 3 m x 5 m
# rectangle (long along z, the stair direction) centred on the cell, so the head
# clears the ceiling over the last flight. Rotations of the two stacked cells must
# agree modulo a half turn.
HOLE_X = 1.5     # half width of the stair opening
HOLE_Z = 2.5     # half length of the stair opening


def wall_with_door(b, zc, h, door=True):
    """North/south perimeter wall at z=zc (0.2 m thick, inner side at |z|=4.8):
    pieces are laid out edge to edge, never overlapping, so no coplanar
    duplicates. Door: 2 m x 3 m at the centre, jambs 0.5 m, rock lintel above."""
    s = 1 if zc > 0 else -1
    if not door:
        b.box((0, h / 2, zc), (9.6, h, 0.2), "rock", skip=("bottom",))
        return
    b.box((-3.15, h / 2, zc), (3.3, h, 0.2), "rock", skip=("bottom",))
    b.box((3.15, h / 2, zc), (3.3, h, 0.2), "rock", skip=("bottom",))
    for sx in (-1, 1):
        b.box((sx * 1.25, 1.5, zc), (0.5, 3.0, 0.2), "rock", skip=("bottom",))
    b.box((0, (3.0 + h) / 2, zc), (3.0, h - 3.0, 0.2), "rock")
    # wooden posts just inside the room (touching the inner face, not overlapping it)
    zin = zc - s * 0.1 - s * 0.06
    buried = "nz" if s < 0 else "pz"      # the face that touches the wall's inner face
    for sx in (-1, 1):
        b.box((sx * 1.06, 1.5, zin), (0.12, 3.0, 0.12), "wood", skip=("bottom", buried))
    b.box((0, 3.06, zin), (2.24, 0.12, 0.12), "wood", skip=(buried,))


def side_walls(b, h):
    """East/west walls: full length, 0.2 m thick; the north/south pieces stop at
    |x|=4.8 so their end faces do not overlap the outer faces of these walls."""
    for sx in (-1, 1):
        b.box((sx * 4.9, h / 2, 0), (0.2, h, 10), "rock", skip=("bottom",))


def cell010(portal=False):
    """Stair tower for a 6 m vertical pitch (floor y=0 is the base).

    Two cave ramps (visually fine steps of 0.125 m rise, 2.4 m wide, so they
    read as a slope), each lifting 3 m:
      F1 west lane   north  z -2.3 .. 2.5   y 0 -> 3     landing A  z 2.5 .. 4.8, y 3 (solid)
      F2 centre lane south  z  2.5 .. -2.5  y 3 -> 6     through the 3 x 5 opening
    The opening (x +-1.5, z +-2.5, ceiling slab y 5.5-5.8) is the U door; F2 ends
    flush with the floor of the cell above (world y 6) at the opening's south edge.
    Walkable surfaces are tilted boxes (one per ramp), no step colliders. Every box
    is laid out so that no two same-facing faces overlap (no Z-fighting).

    portal=True builds the same room as a *visual-only* stair for the portal kind:
    the ceiling is closed (no opening), the door is "U, portal" and an interact
    point stands on F2; the player is teleported to the cell above."""
    c = Cave()
    b = c.b
    H = 6.0
    N = 24
    RISE = 3.0 / N
    b.box((0, -0.05, 0), (10, 0.1, 10), "floor")
    side_walls(b, H)
    wall_with_door(b, 4.9, H, door=False)
    wall_with_door(b, -4.9, H, door=True)
    # worn path: entry strip under the ceiling
    b.box((0, 0.011, -3.65), (9.6, 0.022, 2.3), "path", skip=("bottom",))

    def flight(xc, z_start, z_end, y_base):
        """Solid fine steps from the floor, from z_start to z_end (either direction)."""
        tread = abs(z_end - z_start) / N
        d = 1 if z_end > z_start else -1
        for i in range(N):
            top = y_base + (i + 1) * RISE
            zc = z_start + d * (i + 0.5) * tread
            b.box((xc, top / 2, zc), (2.4, top, tread), "floor", skip=("bottom",))

    flight(-3.6, -2.3, 2.5, 0.0)    # F1
    flight(0.0, 2.5, -2.5, 3.0)     # F2
    # landing A (y=3) as one solid block
    b.box((0, 1.5, 3.65), (9.6, 3.0, 2.3), "floor", skip=("bottom",))
    # ceiling slab (y 5.5-5.8): around the 3 x 5 opening, or closed for the portal kind
    if portal:
        b.box((0, 5.65, 0), (9.6, 0.3, 9.6), "rock")
    else:
        cz = (4.8 + HOLE_Z) / 2
        cl = 4.8 - HOLE_Z
        b.box((0, 5.65, cz), (9.6, 0.3, cl), "rock")
        b.box((0, 5.65, -cz), (9.6, 0.3, cl), "rock")
        cx = (4.8 + HOLE_X) / 2
        cw = 4.8 - HOLE_X
        b.box((cx, 5.65, 0), (cw, 0.3, 2 * HOLE_Z), "rock")
        b.box((-cx, 5.65, 0), (cw, 0.3, 2 * HOLE_Z), "rock")
        for sz in (-1, 1):
            b.box((0, 5.35, sz * (HOLE_Z + 0.1)), (2 * HOLE_X + 0.4, 0.3, 0.2), "wood")
        for sx in (-1, 1):
            b.box((sx * (HOLE_X + 0.1), 5.35, 0), (0.2, 0.3, 2 * HOLE_Z), "wood")

    lip = 0.03   # surface line through the tread centres, a hair above
    c.colliders.append(ramp_collider(-3.6, -2.3, 0.0 + lip, 2.5, 3.0 + lip, 2.4))      # F1
    c.colliders.append(ramp_collider(0.0, 2.5, 3.0 + lip, -2.5, 6.0 + lip, 2.4))       # F2
    c.colliders.append((0, 1.5, 3.65, 9.6, 3.0, 2.3))                                  # landing A (solid)
    c.colliders.append((-2.4, 1.5, 0.1, 0.2, 3.0, 4.8))                                # F1 east side
    c.colliders.append((-1.2, 3.0, 0.0, 0.2, 6.0, 5.0))                                # F2 west side
    c.colliders.append((1.2, 3.0, 0.0, 0.2, 6.0, 5.0))                                 # F2 east side
    if portal:
        c.portals.append(("U", 0.0, round(3.0 + lip + 0.6 * (0.0 - 2.5) * -1, 2), 0.0))   # on F2 near mid height
    c.stalactites([(-2.0, -3.9), (2.0, -3.9)], ceil_y=5.5)
    c.crystals(-1.9, -3.4)
    c.crystals(3.0, 1.0)
    c.rubble([(-0.6, -4.1), (3.0, -1.0)])
    name = "kaidan-no-doukutsu-portal" if portal else "kaidan-no-doukutsu"
    return c, c.manifest(name, "0.6,0.66,0.8,0.55",
                         "0.85,0.92,1.0,1.9 ; 0,4.4,-1",
                         ["S", "U, portal" if portal else "U, stair"])


def cell011(portal=False):
    """Upper landing room for the 6 m stair tower (cell010).

    Floor with a 3 x 5 opening at the centre (the D opening, kind stair): the top
    of cell010's second ramp ends flush with this floor (y=0) at the opening's
    south edge. A wooden rim surrounds the opening; N/S doors. Floor colliders
    come from the host slot, which swaps its full floor box for four boxes around
    the opening when the cell declares a D door of kind stair. Rotation must match
    cell010's modulo a half turn.

    portal=True builds the same room with a full floor and the door "D, portal": no
    opening; the interact point stands at the room centre (arrival and way down)."""
    c = Cave()
    b = c.b
    H = 4.0
    if portal:
        b.box((0, -0.05, 0), (10, 0.1, 10), "floor")
    else:
        cz = (4.8 + HOLE_Z) / 2
        cl = 4.8 - HOLE_Z
        b.box((0, -0.05, cz), (9.6, 0.1, cl), "floor")
        b.box((0, -0.05, -cz), (9.6, 0.1, cl), "floor")
        cx = (4.8 + HOLE_X) / 2
        cw = 4.8 - HOLE_X
        b.box((cx, -0.05, 0), (cw, 0.1, 2 * HOLE_Z), "floor")
        b.box((-cx, -0.05, 0), (cw, 0.1, 2 * HOLE_Z), "floor")
        # floor under the perimeter walls (the 0.2 m rim the pieces above leave)
        b.box((0, -0.05, 4.9), (10, 0.1, 0.2), "floor")
        b.box((0, -0.05, -4.9), (10, 0.1, 0.2), "floor")
        b.box((4.9, -0.05, 0), (0.2, 0.1, 9.6), "floor")
        b.box((-4.9, -0.05, 0), (0.2, 0.1, 9.6), "floor")
        # wooden rim around the opening (N/S pieces include the corners, E/W fit between)
        for sz in (-1, 1):
            b.box((0, 0.15, sz * (HOLE_Z + 0.1)), (2 * HOLE_X + 0.4, 0.3, 0.2), "wood", skip=("bottom",))
        for sx in (-1, 1):
            b.box((sx * (HOLE_X + 0.1), 0.15, 0), (0.2, 0.3, 2 * HOLE_Z), "wood", skip=("bottom",))
    side_walls(b, H)
    wall_with_door(b, 4.9, H, door=True)
    wall_with_door(b, -4.9, H, door=True)
    b.box((0, H + 0.15, 0), (9.6, 0.3, 9.6), "rock")
    b.box((0, 0.011, 3.9), (3.0, 0.022, 1.8), "path", skip=("bottom",))
    b.box((0, 0.011, -3.9), (3.0, 0.022, 1.8), "path", skip=("bottom",))
    if portal:
        c.portals.append(("D", 0.0, 0.0, 0.0))
    c.stalactites([(-3.2, 2.8), (3.2, -2.8), (-3.0, -3.0)], ceil_y=H)
    c.crystals(-3.4, 0.0)
    c.rubble([(3.4, 2.4), (-2.6, -2.2)])
    name = "kaidan-no-ue-portal" if portal else "kaidan-no-ue"
    return c, c.manifest(name, "0.6,0.66,0.8,0.55",
                         "0.85,0.92,1.0,1.7 ; 0,3.2,0",
                         ["N", "S", "D, portal" if portal else "D, stair"])


def cell012():
    return cell010(portal=True)


def cell013():
    return cell011(portal=True)


CELLS = [
    (6, cell006), (7, cell007), (8, cell008), (9, cell009), (10, cell010), (11, cell011), (12, cell012), (13, cell013),
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
