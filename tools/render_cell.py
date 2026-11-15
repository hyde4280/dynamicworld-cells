#!/usr/bin/env python3
"""Software preview of a cell as the CellSurface shader would light it.

A small z-buffer rasteriser (numpy): atlas sampling with the `# cell.tiling:` region
repeated, room tint x `# cell.baselight:`, the `# cell.lights:` point lights (same
falloff as the shader, no flicker), `# cell.glow:` and the `# cell.fog:` sight distance. It is a
check of layout and brightness, not of what Unity will show.

Usage: render_cell.py cells/cell008.obj out.png ex,ey,ez tx,ty,tz [--bright] [--size WxH]
"""
import math
import sys

import numpy as np
from PIL import Image


def load(path):
    v, vt, f, man = [], [], [], {}
    for line in open(path):
        if line.startswith("# ") and ":" in line:
            k, val = line[2:].split(":", 1)
            man.setdefault(k.strip(), []).append(val.strip())
        elif line.startswith("v "):
            v.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("vt "):
            vt.append([float(x) for x in line.split()[1:3]])
        elif line.startswith("f "):
            f.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
    return np.array(v), np.array(vt), np.array(f), man


def render(obj, out, eye, target, size=(640, 400), bright=False, fov=75.0):
    V, VT, F, man = load(obj)
    atlas = np.asarray(Image.open(obj[:-4] + ".png").convert("RGB"), dtype=np.float32) / 255.0
    AH, AW = atlas.shape[:2]
    num = lambda s: [float(x) for x in s.replace(";", ",").split(",")]
    base = 1.0 if bright or "cell.baselight" not in man else num(man["cell.baselight"][0])[0]
    fog = None if bright or "cell.fog" not in man else num(man["cell.fog"][0])
    amb = num(man.get("cell.ambient", ["1,1,1,1"])[0])
    tint = (0.5 + 0.5 * np.array(amb[:3])) * (0.7 + 0.3 * min(1.0, amb[3])) * base
    lights = []
    for seg in man.get("cell.lights", [""])[0].split(";"):
        p = [float(x) for x in seg.split(",") if x.strip()]
        if len(p) >= 7:
            lights.append(p)
    tile = None
    if "cell.tiling" in man:
        p = man["cell.tiling"][0].split(",")
        tile = (float(p[1]), [float(x) for x in p[2:6]])

    glow = None if "cell.glow" not in man else num(man["cell.glow"][0])
    eye = np.array(eye, dtype=float)
    fw = np.array(target, dtype=float) - eye
    fw /= np.linalg.norm(fw)
    rt = np.cross(fw, [0, 1, 0]); rt /= np.linalg.norm(rt)
    up = np.cross(rt, fw)
    W, H = size
    fl = (W / 2) / math.tan(math.radians(fov) / 2)
    img = np.zeros((H, W, 3), dtype=np.float32)
    zb = np.full((H, W), 1e9, dtype=np.float32)
    NEAR = 0.08

    for tri in F:
        P = V[tri]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        ln = np.linalg.norm(n)
        if ln < 1e-9 or np.dot(n, P[0] - eye) >= 0:      # degenerate / back face
            continue
        n /= ln
        cam = np.stack([(P - eye) @ rt, (P - eye) @ up, (P - eye) @ fw], axis=1)
        poly = [(cam[i], P[i], VT[tri[i]]) for i in range(3)]
        clipped = []
        for i in range(len(poly)):                        # clip against the near plane
            a, b = poly[i], poly[(i + 1) % len(poly)]
            ia, ib = a[0][2] >= NEAR, b[0][2] >= NEAR
            if ia:
                clipped.append(a)
            if ia != ib:
                t = (NEAR - a[0][2]) / (b[0][2] - a[0][2])
                clipped.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
        for k in range(1, len(clipped) - 1):
            t3 = (clipped[0], clipped[k], clipped[k + 1])
            sx = np.array([W / 2 + p[0][0] / p[0][2] * fl for p in t3])
            sy = np.array([H / 2 - p[0][1] / p[0][2] * fl for p in t3])
            x0, x1 = max(0, int(sx.min())), min(W - 1, int(sx.max()) + 1)
            y0, y1 = max(0, int(sy.min())), min(H - 1, int(sy.max()) + 1)
            if x0 > x1 or y0 > y1:
                continue
            den = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
            if abs(den) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((sy[1] - sy[2]) * (gx - sx[2]) + (sx[2] - sx[1]) * (gy - sy[2])) / den
            w1 = ((sy[2] - sy[0]) * (gx - sx[2]) + (sx[0] - sx[2]) * (gy - sy[2])) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
            iz = np.array([1.0 / p[0][2] for p in t3])
            q = w0 * iz[0] + w1 * iz[1] + w2 * iz[2]
            z = 1.0 / np.maximum(q, 1e-9)
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            m = inside & (z < sub)
            if not m.any():
                continue
            b0, b1, b2 = w0 * iz[0] * z, w1 * iz[1] * z, w2 * iz[2] * z
            pos = b0[..., None] * t3[0][1] + b1[..., None] * t3[1][1] + b2[..., None] * t3[2][1]
            uv = b0[..., None] * t3[0][2] + b1[..., None] * t3[1][2] + b2[..., None] * t3[2][2]
            is_glow = None
            if glow is not None:
                is_glow = ((uv[..., 0] >= glow[0]) & (uv[..., 0] <= glow[2])
                           & (uv[..., 1] >= glow[1]) & (uv[..., 1] <= glow[3]))
            if tile is not None:
                u0, v0, u1, v1 = tile[1]
                rel = (uv - [u0, v0]) / [u1 - u0, v1 - v0]
                if ((rel >= 0) & (rel <= 1)).all(axis=-1)[m].mean() > 0.5:
                    an = np.abs(n)
                    pl = pos[..., [2, 1]] if (an[0] > an[1] and an[0] > an[2]) else (pos[..., [0, 2]] if an[1] > an[2] else pos[..., [0, 1]])
                    uv = np.array([u0, v0]) + np.mod(pl / tile[0], 1.0) * [u1 - u0, v1 - v0]
            tx = np.clip((uv[..., 0] * AW).astype(int), 0, AW - 1)
            ty = np.clip(((1 - uv[..., 1]) * AH).astype(int), 0, AH - 1)
            tex = atlas[ty, tx]
            shade = 0.82 + 0.18 * max(0.0, float(np.dot(n, np.array([0.3, 1.0, 0.2]) / np.linalg.norm([0.3, 1.0, 0.2]))))
            lit = tex * tint * shade
            for L in lights:
                lv = np.array(L[:3]) - pos
                d = np.linalg.norm(lv, axis=-1)
                att = L[6] / (1 + 0.25 * d * d)
                ndl = np.clip((lv @ n) / np.maximum(d, 1e-4), 0, 1)
                lit = lit + tex * np.array(L[3:6]) * (att * ndl)[..., None]
            if is_glow is not None:
                lit = np.where(is_glow[..., None], tex * (glow[4] if len(glow) > 4 else 1.0), lit)
            if fog is not None:
                fd = np.linalg.norm(pos - eye, axis=-1)
                ff = np.clip((fd - fog[0]) / max(fog[1] - fog[0], 1e-3), 0, 1)[..., None]
                lit = lit * (1 - ff)
            sub[m] = z[m]
            img[y0:y1 + 1, x0:x1 + 1][m] = lit[m]
    Image.fromarray((np.clip(img, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8)).save(out)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    size = (640, 400)
    if "--size" in sys.argv:
        size = tuple(int(x) for x in sys.argv[sys.argv.index("--size") + 1].split("x"))
        a.remove(sys.argv[sys.argv.index("--size") + 1])
    render(a[0], a[1], [float(x) for x in a[2].split(",")], [float(x) for x in a[3].split(",")],
           size=size, bright="--bright" in sys.argv)
