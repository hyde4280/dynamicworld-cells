#!/usr/bin/env python3
"""Detect coplanar overlapping triangles (Z-fighting) in a cell OBJ.

Two triangles Z-fight when they lie in the same plane, face the same way and
share a region of positive area. The report lists the total overlap area (m^2)
and the number of overlapping pairs, plus the planes with the most overlap.

Usage: check_overlap.py cells/cell010.obj [...]   (exit status 1 if any overlap)
"""
import sys
from collections import defaultdict

EPS_PLANE = 2e-3     # plane distance tolerance (m)
EPS_AREA = 1e-6      # ignore slivers (m^2)


def load(path):
    verts, tris = [], []
    for line in open(path):
        if line.startswith("v "):
            verts.append(tuple(float(x) for x in line.split()[1:4]))
        elif line.startswith("f "):
            idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
            for i in range(1, len(idx) - 1):
                tris.append((idx[0], idx[i], idx[i + 1]))
    return verts, tris


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    l = dot(a, a) ** 0.5
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-12 else None


def area2d(poly):
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def clip(subject, clipper):
    """Sutherland-Hodgman; both polygons CCW."""
    out = subject
    n = len(clipper)
    for i in range(n):
        a, b = clipper[i], clipper[(i + 1) % n]
        inp, out = out, []
        if not inp:
            break

        def inside(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-12

        def inter(p, q):
            x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
            x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(den) < 1e-15:
                return q
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

        for j in range(len(inp)):
            p, q = inp[j], inp[(j + 1) % len(inp)]
            if inside(q):
                if not inside(p):
                    out.append(inter(p, q))
                out.append(q)
            elif inside(p):
                out.append(inter(p, q))
    return out


def overlaps(path):
    verts, tris = load(path)
    groups = defaultdict(list)
    for t in tris:
        a, b, c = (verts[i] for i in t)
        n = norm(cross(sub(b, a), sub(c, a)))
        if n is None:
            continue
        d = dot(n, a)
        key = (round(n[0], 2), round(n[1], 2), round(n[2], 2), round(d / EPS_PLANE))
        groups[key].append((t, n, d))
    total = 0.0
    pairs = 0
    per_plane = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        n = items[0][1]
        # in-plane basis
        ref = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
        u = norm(cross(n, ref))
        v = cross(n, u)
        polys = []
        for t, _, _ in items:
            p2 = [(dot(verts[i], u), dot(verts[i], v)) for i in t]
            if area2d(p2) < 0:
                p2.reverse()
            polys.append(p2)
        plane_total = 0.0
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                ov = clip(list(polys[i]), polys[j])
                if len(ov) >= 3:
                    ar = abs(area2d(ov))
                    if ar > EPS_AREA:
                        plane_total += ar
                        pairs += 1
        if plane_total > 0:
            per_plane.append((plane_total, key))
        total += plane_total
    per_plane.sort(reverse=True)
    return total, pairs, per_plane


def main():
    bad = False
    for path in sys.argv[1:]:
        total, pairs, per_plane = overlaps(path)
        print(f"{path}: overlap {total:.2f} m^2 ({pairs} pairs)")
        for ar, key in per_plane[:6]:
            print(f"    {ar:6.2f} m^2  n=({key[0]},{key[1]},{key[2]}) d~{key[3] * EPS_PLANE:.3f}")
        if total > 0.01:
            bad = True
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
