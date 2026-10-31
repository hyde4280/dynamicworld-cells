#!/usr/bin/env python3
"""Shared geometry/texture helpers for cell generators (spec v0).

Same conventions as gen_cell001.py: verts/uvs/norms are parallel arrays,
faces reference v/vt/vn with one shared index, everything is emitted as an
expanded triangle soup (which is what the loader builds anyway).

Primitives: box, cylinder, cone (via cylinder), sphere, rock (jittered
sphere), quad. All take an optional rot=(rx, ry, rz) in degrees, applied
around the primitive's center.
"""
import math
import random
from PIL import Image, ImageDraw


def rot_matrix(rx, ry, rz):
    ax, ay, az = (math.radians(a) for a in (rx, ry, rz))
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    # R = Ry * Rx * Rz (apply Z, then X, then Y)
    return (
        (cy * cz + sy * sx * sz, -cy * sz + sy * sx * cz, sy * cx),
        (cx * sz, cx * cz, -sx),
        (-sy * cz + cy * sx * sz, sy * sz + cy * sx * cz, cy * cx),
    )


def apply_rot(m, p):
    return (
        m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2],
        m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2],
        m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2],
    )


class CellBuilder:
    def __init__(self, regions):
        self.regions = regions  # name -> (u0, v0, u1, v1), v up
        self.verts = []
        self.uvs = []
        self.norms = []
        self.faces = []

    # -- low level ------------------------------------------------------
    def _emit(self, pos, normal, uv):
        self.verts.append(pos)
        self.uvs.append(uv)
        self.norms.append(normal)
        return len(self.verts)  # 1-based

    def tri(self, p1, p2, p3, n1, n2, n3, uv1, uv2, uv3):
        i1 = self._emit(p1, n1, uv1)
        i2 = self._emit(p2, n2, uv2)
        i3 = self._emit(p3, n3, uv3)
        self.faces.append((i1, i2, i3))

    def quad(self, pts, normals, region, uv_mode="full"):
        """pts/normals: 4 corners CCW seen from the normal side."""
        u0, v0, u1, v1 = self.regions[region]
        corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        idx = [self._emit(pts[i], normals[i], corners[i]) for i in range(4)]
        self.faces.append((idx[0], idx[1], idx[2]))
        self.faces.append((idx[0], idx[2], idx[3]))

    def _xform(self, center, rot):
        m = rot_matrix(*rot) if rot else None

        def f(p, n):
            if m:
                p = apply_rot(m, p)
                n = apply_rot(m, n)
            return (p[0] + center[0], p[1] + center[1], p[2] + center[2]), n

        return f

    # -- primitives -----------------------------------------------------
    def box(self, center, size, region, rot=None):
        f = self._xform(center, rot)
        hx, hy, hz = (s / 2 for s in size)
        faces = [
            ([(-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)], (0, 0, 1)),
            ([(hx, -hy, -hz), (-hx, -hy, -hz), (-hx, hy, -hz), (hx, hy, -hz)], (0, 0, -1)),
            ([(hx, -hy, hz), (hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz)], (1, 0, 0)),
            ([(-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, hz), (-hx, hy, -hz)], (-1, 0, 0)),
            ([(-hx, hy, hz), (hx, hy, hz), (hx, hy, -hz), (-hx, hy, -hz)], (0, 1, 0)),
            ([(-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz)], (0, -1, 0)),
        ]
        for pts, n in faces:
            tp = [f(p, n) for p in pts]
            self.quad([q[0] for q in tp], [q[1] for q in tp], region)

    def cylinder(self, center, r_bottom, r_top, height, seg, region, rot=None, cap=True):
        f = self._xform(center, rot)
        hh = height / 2
        # side
        for i in range(seg):
            a0 = 2 * math.pi * i / seg
            a1 = 2 * math.pi * (i + 1) / seg
            am = (a0 + a1) / 2
            pts = []
            ns = []
            for a, r, y in ((a0, r_bottom, -hh), (a1, r_bottom, -hh), (a1, r_top, hh), (a0, r_top, hh)):
                pts.append((r * math.sin(a), y, r * math.cos(a)))
            for a in (a0, a1, a1, a0):
                ns.append((math.sin(a), 0.0, math.cos(a)))
            tp = [f(p, n) for p, n in zip(pts, ns)]
            u0, v0, u1, v1 = self.regions[region]
            fu0 = u0 + (u1 - u0) * i / seg
            fu1 = u0 + (u1 - u0) * (i + 1) / seg
            uvs = [(fu0, v0), (fu1, v0), (fu1, v1), (fu0, v1)]
            idx = [self._emit(q[0], q[1], uv) for q, uv in zip(tp, uvs)]
            self.faces.append((idx[0], idx[1], idx[2]))
            self.faces.append((idx[0], idx[2], idx[3]))
            _ = am
        if cap:
            u0, v0, u1, v1 = self.regions[region]
            cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
            ru, rv = (u1 - u0) / 2, (v1 - v0) / 2
            for y, r, n, flip in ((hh, r_top, (0, 1, 0), False), (-hh, r_bottom, (0, -1, 0), True)):
                if r <= 0:
                    continue
                cp, cn = f((0, y, 0), n)
                ci = self._emit(cp, cn, (cu, cv))
                ring = []
                for i in range(seg):
                    a = 2 * math.pi * i / seg
                    p, nn = f((r * math.sin(a), y, r * math.cos(a)), n)
                    uv = (cu + ru * math.sin(a), cv + rv * math.cos(a))
                    ring.append(self._emit(p, nn, uv))
                for i in range(seg):
                    j = (i + 1) % seg
                    if flip:
                        self.faces.append((ci, ring[j], ring[i]))
                    else:
                        self.faces.append((ci, ring[i], ring[j]))

    def sphere(self, center, radius, seg_u, seg_v, region, squash=(1, 1, 1), rot=None, jitter=0.0, rng=None):
        f = self._xform(center, rot)
        u0, v0, u1, v1 = self.regions[region]
        grid = []
        for j in range(seg_v + 1):
            phi = math.pi * j / seg_v  # 0 top .. pi bottom
            row = []
            for i in range(seg_u + 1):
                theta = 2 * math.pi * i / seg_u
                d = (math.sin(phi) * math.sin(theta), math.cos(phi), math.sin(phi) * math.cos(theta))
                r = radius
                if jitter and rng is not None and 0 < j < seg_v:
                    r = radius * (1 + rng.uniform(-jitter, jitter))
                p = (d[0] * r * squash[0], d[1] * r * squash[1], d[2] * r * squash[2])
                tp, tn = f(p, d)
                uv = (u0 + (u1 - u0) * i / seg_u, v0 + (v1 - v0) * (1 - j / seg_v))
                row.append(self._emit(tp, tn, uv))
            grid.append(row)
        for j in range(seg_v):
            for i in range(seg_u):
                a, b = grid[j][i], grid[j][i + 1]
                c, d2 = grid[j + 1][i + 1], grid[j + 1][i]
                if j > 0:
                    self.faces.append((a, d2, c))
                if j < seg_v - 1:
                    self.faces.append((a, c, b))

    def room_shell(self, wall_region, floor_region, wall_h=4.0, beams=None, beam_region=None):
        """Standard v0 room: floor slab, N/E/W walls, south wall with the
        2m x 3m entrance gap, optional roof beams."""
        self.box((0, -0.05, 0), (10, 0.1, 10), floor_region)
        self.box((0, wall_h / 2, 4.9), (10, wall_h, 0.2), wall_region)
        self.box((4.9, wall_h / 2, 0), (0.2, wall_h, 10), wall_region)
        self.box((-4.9, wall_h / 2, 0), (0.2, wall_h, 10), wall_region)
        self.box((-3, wall_h / 2, -4.9), (4, wall_h, 0.2), wall_region)
        self.box((3, wall_h / 2, -4.9), (4, wall_h, 0.2), wall_region)
        self.box((0, 3 + (wall_h - 3) / 2, -4.9), (2, wall_h - 3, 0.2), wall_region)
        if beams:
            for z in beams:
                self.box((0, wall_h + 0.1, z), (10, 0.2, 0.4), beam_region)

    def write_obj(self, path, manifest_lines, header):
        lines = [header] + manifest_lines + ["mtllib none", "usemtl atlas"]
        for v in self.verts:
            lines.append(f"v {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}")
        for t in self.uvs:
            lines.append(f"vt {t[0]:.4f} {t[1]:.4f}")
        for n in self.norms:
            lines.append(f"vn {n[0]:.3f} {n[1]:.3f} {n[2]:.3f}")
        for fc in self.faces:
            lines.append("f " + " ".join(f"{i}/{i}/{i}" for i in fc))
        with open(path, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        return len(self.faces)


# ---------- atlas painting ----------

def region_rects_2x3():
    """Six regions in a 2-col x 3-row grid (u, v), v up."""
    names = []
    rects = {}
    return rects


def grid_regions(names, cols, rows):
    rects = {}
    for k, name in enumerate(names):
        col = k % cols
        row = k // cols  # row 0 = top in image = high v
        u0 = col / cols
        u1 = (col + 1) / cols
        v1 = 1.0 - row / rows
        v0 = 1.0 - (row + 1) / rows
        rects[name] = (u0, v0, u1, v1)
    return rects


class AtlasPainter:
    def __init__(self, size, regions, seed=42):
        self.size = size
        self.regions = regions
        self.img = Image.new("RGB", (size, size), (0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self.rng = random.Random(seed)

    def px(self, name):
        u0, v0, u1, v1 = self.regions[name]
        return (u0 * self.size, (1 - v1) * self.size, u1 * self.size, (1 - v0) * self.size)

    def speckle(self, name, base, n=1400, amp=18, rmax=3):
        x0, y0, x1, y1 = self.px(name)
        self.d.rectangle([x0, y0, x1, y1], fill=base)
        for _ in range(n):
            x = self.rng.uniform(x0, x1)
            y = self.rng.uniform(y0, y1)
            r = self.rng.uniform(1, rmax)
            c = tuple(max(0, min(255, b + self.rng.randint(-amp, amp))) for b in base)
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=c)

    def tile_grid(self, name, base, line, nx=4, ny=4, width=3):
        self.speckle(name, base)
        x0, y0, x1, y1 = self.px(name)
        for i in range(1, nx):
            gx = x0 + (x1 - x0) * i / nx
            self.d.line([gx, y0, gx, y1], fill=line, width=width)
        for i in range(1, ny):
            gy = y0 + (y1 - y0) * i / ny
            self.d.line([x0, gy, x1, gy], fill=line, width=width)

    def planks(self, name, base, line, n=6):
        self.speckle(name, base)
        x0, y0, x1, y1 = self.px(name)
        for i in range(1, n):
            gy = y0 + (y1 - y0) * i / n
            self.d.line([x0, gy, x1, gy], fill=line, width=3)

    def gradient(self, name, top, bottom, speckle_n=500):
        x0, y0, x1, y1 = self.px(name)
        h = max(1, int(y1 - y0))
        for k in range(h):
            t = k / h
            c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            self.d.line([x0, y0 + k, x1, y0 + k], fill=c)
        for _ in range(speckle_n):
            x = self.rng.uniform(x0, x1)
            y = self.rng.uniform(y0, y1)
            r = self.rng.uniform(1, 2.5)
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))

    def blobs(self, name, base, blob, n=260, rmin=6, rmax=20):
        self.speckle(name, base, n=500)
        x0, y0, x1, y1 = self.px(name)
        for _ in range(n):
            x = self.rng.uniform(x0, x1)
            y = self.rng.uniform(y0, y1)
            r = self.rng.uniform(rmin, rmax)
            c = tuple(max(0, min(255, b + self.rng.randint(-14, 14))) for b in blob)
            self.d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=c)

    def save(self, path):
        self.img.save(path)
