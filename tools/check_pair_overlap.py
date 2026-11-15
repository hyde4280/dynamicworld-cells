#!/usr/bin/env python3
"""Z-fighting between neighbouring cells: for every edge of a world definition, place the
two cells at their grid positions (10 m pitch x/z, 6 m y, rot*90 deg about y) and report the
coplanar, same-facing overlap that exists only between the two cells (not inside one).

With --all, grid neighbours without an edge are checked too (side by side or stacked):
a sheet on the rim of one cell can Z-fight the outer face of any neighbour, and it is
seen from inside the first cell whether or not a door joins them.

The planes listed under a pair are the between-cell part only. Whether one matters is
a judgement: overlaps on outward faces (the rim planes, rock tops above the ceilings)
are not seen from inside; anything else is.

Usage: check_pair_overlap.py defs/stagetest.txt [--all]
"""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_overlap as co  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CELLS = os.path.join(HERE, "..", "cells")


def parse_def(path):
    nodes, edges = {}, []
    for line in open(path, encoding="utf-8"):
        line = line.split("#")[0].strip()
        if line.startswith("node:"):
            p = [x.strip() for x in line[5:].split(",")]
            nodes[p[0]] = (p[1], int(p[2]), int(p[3]), int(p[4]), int(p[5]) if len(p) > 5 else 0)
        elif line.startswith("edge:"):
            p = [x.strip() for x in line[5:].split(",")]
            edges.append((p[0].split(".")[0], p[1].split(".")[0]))
    return nodes, edges


def placed(node):
    cell, gx, gy, gz, rot = node
    verts, tris = co.load(os.path.join(CELLS, cell + ".obj"))
    th = math.radians(90 * rot)
    c, s = math.cos(th), math.sin(th)
    out = [(x * c + z * s + gx * 10, y + gy * 6, -x * s + z * c + gz * 10) for x, y, z in verts]
    return out, tris


def write(path, parts):
    with open(path, "w") as f:
        base = 0
        for verts, tris in parts:
            for v in verts:
                f.write("v %f %f %f\n" % v)
            for t in tris:
                f.write("f %d %d %d\n" % (t[0] + 1 + base, t[1] + 1 + base, t[2] + 1 + base))
            base += len(verts)


def neighbours(nodes, edges):
    """Grid-adjacent node pairs that no edge joins."""
    at = {(n[1], n[2], n[3]): k for k, n in nodes.items()}
    have = {frozenset(e) for e in edges}
    out = []
    for (x, y, z), k in sorted(at.items()):
        for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            o = at.get((x + d[0], y + d[1], z + d[2]))
            if o is not None and frozenset((k, o)) not in have:
                out.append((k, o))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    nodes, edges = parse_def(args[0])
    if "--all" in sys.argv:
        edges = edges + neighbours(nodes, edges)
    tmp = tempfile.mkdtemp()
    solo, solo_planes = {}, {}
    for e in edges:
        for n in e:
            if n not in solo:
                p = os.path.join(tmp, n + ".obj"); write(p, [placed(nodes[n])])
                solo[n], _, planes = co.overlaps(p)
                solo_planes[n] = {key: ar for ar, key in planes}
        p = os.path.join(tmp, "pair.obj")
        write(p, [placed(nodes[e[0]]), placed(nodes[e[1]])])
        total, pairs, per_plane = co.overlaps(p)
        extra = total - solo[e[0]] - solo[e[1]]
        print(f"{e[0]}({nodes[e[0]][0]}) - {e[1]}({nodes[e[1]][0]}): between-cell overlap {extra:.2f} m^2")
        if extra > 0.01:
            between = sorted(((ar - solo_planes[e[0]].get(key, 0) - solo_planes[e[1]].get(key, 0), key)
                              for ar, key in per_plane), reverse=True)
            for ar, key in between[:6]:
                if ar > 0.005:
                    print(f"    {ar:6.2f} m^2  n=({key[0]},{key[1]},{key[2]}) d~{key[3] * co.EPS_PLANE:.3f}")


if __name__ == "__main__":
    main()
