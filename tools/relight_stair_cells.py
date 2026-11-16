#!/usr/bin/env python3
"""Give the stair cells 010 / 011 the dark-mine lighting of the tunnel cells (2026-11-16).

The geometry and colliders of both cells are published and verified, so only the
header lines change: ambient / lightvolume / keylight take the tunnel values, and
`# cell.baselight:`, `# cell.fog:` and `# cell.lights:` (warm wall lanterns, the
tunnel convention 1,0.7,0.4 / intensity 2 / flicker 0.35) are written. The script
is idempotent: the lines it owns are removed first and re-inserted before the
first `# door:` line.

cell010 (flight along the west wall x=-3.6 rising toward +z, landing at y=3 for
z 2.5..4.8, second flight inside the x=+-1.2 shaft rising toward -z):
  entrance (0,2.5,-3.7), first flight (-3.6,3.0,0), landing (0,4.3,3.7),
  second flight (0,5.3,0)
cell011 (open room, stair hole x +-1.5 / z +-2.5 in the middle, doors N/S):
  one lantern light near each door and beside the hole.

Usage: relight_stair_cells.py [cells dir]
"""
import os
import sys

OWNED = ("# cell.ambient:", "# cell.lightvolume:", "# cell.keylight:", "# cell.baselight:",
         "# cell.fog:", "# cell.lights:")
RGB = "1,0.7,0.4"
LIGHTS = {
    10: [(0, 2.5, -3.7), (-3.6, 3.0, 0), (0, 4.3, 3.7), (0, 5.3, 0)],
    11: [(0, 2.5, -3.7), (0, 2.5, 3.7), (-3.6, 2.5, 0), (3.6, 2.5, 0)],
}


def num(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def relight(path, pts):
    lines = open(path, newline="").read().split("\n")
    lines = [ln for ln in lines if not ln.startswith(OWNED)]
    x, y, z = pts[0]
    block = [
        "# cell.ambient: 0.62,0.55,0.46,0.5",
        "# cell.lightvolume: 0.55,0.45,0.34,0.3",
        f"# cell.keylight: {RGB},2 ; {num(x)},{num(y)},{num(z)}",
        "# cell.baselight: 0.12",
        "# cell.fog: 3, 10",
        "# cell.lights: " + " ; ".join(f"{num(a)},{num(b)},{num(c)}, {RGB},2,0.35" for a, b, c in pts),
    ]
    k = next(i for i, ln in enumerate(lines) if ln.startswith("# door:"))
    lines[k:k] = block
    open(path, "w", newline="").write("\n".join(lines))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "cells")
    for n, pts in LIGHTS.items():
        relight(os.path.join(out, f"cell{n:03d}.obj"), pts)
        print(f"cell{n:03d}: {len(pts)} lights")


if __name__ == "__main__":
    main()
