#!/usr/bin/env python3
"""Validate a generated cell OBJ against spec v0 basics and render a
software preview (painter's algorithm, atlas-sampled) for eyeballing."""
import math
import sys
from PIL import Image, ImageDraw


def parse_obj(path):
    verts, uvs, norms, faces, manifest = [], [], [], [], []
    for line in open(path):
        if line.startswith("#"):
            manifest.append(line.strip())
        elif line.startswith("v "):
            verts.append(tuple(float(x) for x in line.split()[1:4]))
        elif line.startswith("vt "):
            uvs.append(tuple(float(x) for x in line.split()[1:3]))
        elif line.startswith("vn "):
            norms.append(tuple(float(x) for x in line.split()[1:4]))
        elif line.startswith("f "):
            faces.append(tuple(int(t.split("/")[0]) for t in line.split()[1:4]))
    return verts, uvs, norms, faces, manifest


def validate(path):
    verts, uvs, norms, faces, manifest = parse_obj(path)
    errs = []
    if not (len(verts) == len(uvs) == len(norms)):
        errs.append(f"count mismatch v={len(verts)} vt={len(uvs)} vn={len(norms)}")
    n = len(verts)
    for f in faces:
        for i in f:
            if i < 1 or i > n:
                errs.append(f"face index out of range: {i}")
                break
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]
    if min(xs) < -5.3 or max(xs) > 5.3 or min(zs) < -5.3 or max(zs) > 5.3:
        errs.append(f"x/z out of cell: x[{min(xs)},{max(xs)}] z[{min(zs)},{max(zs)}]")
    if min(ys) < -0.2 or max(ys) > 10.05:
        errs.append(f"y out of range: [{min(ys)},{max(ys)}]")
    for u, v in uvs:
        if u < -0.001 or u > 1.001 or v < -0.001 or v > 1.001:
            errs.append(f"uv out of [0,1]: {(u, v)}")
            break
    cols = [m for m in manifest if m.startswith("# collider:")]
    if len(cols) > 16:
        errs.append(f"colliders {len(cols)} > pool 16")
    if not any(m.startswith("# cell.name:") for m in manifest):
        errs.append("no cell.name")
    print(f"{path}: tris={len(faces)} verts={n} colliders={len(cols)} "
          f"y[{min(ys):.2f},{max(ys):.2f}] {'OK' if not errs else 'ERRORS: ' + '; '.join(errs[:5])}")
    return not errs


def look_at(eye, target):
    fwd = [target[i] - eye[i] for i in range(3)]
    ln = math.sqrt(sum(x * x for x in fwd)); fwd = [x / ln for x in fwd]
    up = (0, 1, 0)
    right = [fwd[1] * up[2] - fwd[2] * up[1], fwd[2] * up[0] - fwd[0] * up[2], fwd[0] * up[1] - fwd[1] * up[0]]
    ln = math.sqrt(sum(x * x for x in right)); right = [x / ln for x in right]
    up2 = [right[1] * fwd[2] - right[2] * fwd[1], right[2] * fwd[0] - right[0] * fwd[2], right[0] * fwd[1] - right[1] * fwd[0]]
    return right, up2, fwd


def preview(obj_path, png_path, out_path, eye=(3.9, 2.7, -3.9), size=640):
    verts, uvs, norms, faces, _ = parse_obj(obj_path)
    atlas = Image.open(png_path).convert("RGB")
    AW, AH = atlas.size
    img = Image.new("RGB", (size, size), (24, 26, 32))
    d = ImageDraw.Draw(img)
    right, up, fwd = look_at(eye, (-0.4, 0.7, 0.8))
    light = (-0.45, 0.8, -0.4)
    ln = math.sqrt(sum(x * x for x in light)); light = tuple(x / ln for x in light)

    def proj(p):
        rel = [p[i] - eye[i] for i in range(3)]
        cx = sum(rel[i] * right[i] for i in range(3))
        cy = sum(rel[i] * up[i] for i in range(3))
        cz = sum(rel[i] * fwd[i] for i in range(3))
        s = size * 0.62 / max(0.1, cz)
        return (size / 2 + cx * s, size / 2 - cy * s), cz

    tris = []
    for f in faces:
        pts = [verts[i - 1] for i in f]
        rel0 = [pts[0][i] - eye[i] for i in range(3)]
        if sum(rel0[i] * fwd[i] for i in range(3)) < 0.4:
            continue
        ns = [norms[i - 1] for i in f]
        uvs_f = [uvs[i - 1] for i in f]
        depth = sum(proj(p)[1] for p in pts) / 3
        tris.append((depth, pts, ns, uvs_f))
    tris.sort(key=lambda t: -t[0])
    for _, pts, ns, uvs_f in tris:
        sp = [proj(p)[0] for p in pts]
        n = tuple(sum(ns[k][i] for k in range(3)) / 3 for i in range(3))
        ndl = abs(sum(n[i] * light[i] for i in range(3)))
        shade = 0.35 + 0.65 * ndl
        cu = sum(u[0] for u in uvs_f) / 3
        cv = sum(u[1] for u in uvs_f) / 3
        px = atlas.getpixel((min(AW - 1, int(cu * AW)), min(AH - 1, int((1 - cv) * AH))))
        col = tuple(max(0, min(255, int(c * shade))) for c in px)
        d.polygon(sp, fill=col)
    img.save(out_path)
    print("preview ->", out_path)


if __name__ == "__main__":
    ok = validate(sys.argv[1])
    if len(sys.argv) > 3:
        preview(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if ok else 1)
