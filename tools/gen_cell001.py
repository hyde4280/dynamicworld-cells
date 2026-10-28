#!/usr/bin/env python3
"""cell001 sample generator for the single-cell prototype (spec v0).

Produces:
  - cell001.obj : triangulated OBJ, manifest embedded in header comments
  - cell001.png : 512x512 texture atlas (4 material regions)

Cell rules (spec v0): 10m x 10m, origin at floor center, floor y=0,
entrance on the south (-Z) face center, 2m wide x 3m high, single material.
"""
import random
from PIL import Image, ImageDraw

# ---------- atlas ----------
ATLAS = 512
REGIONS = {  # name -> (u0, v0, u1, v1) in UV space (v up)
    "stone":     (0.0, 0.5, 0.5, 1.0),
    "plaster":   (0.5, 0.5, 1.0, 1.0),
    "wood":      (0.0, 0.0, 0.5, 0.5),
    "vermillion": (0.5, 0.0, 1.0, 0.5),
}

def uv_to_px(u, v):
    return (u * ATLAS, (1.0 - v) * ATLAS)

def make_atlas(path):
    rng = random.Random(42)
    img = Image.new("RGB", (ATLAS, ATLAS), (0, 0, 0))
    d = ImageDraw.Draw(img)

    def fill_region(name, base, speckle, n=900):
        u0, v0, u1, v1 = REGIONS[name]
        x0, y1 = uv_to_px(u0, v0)
        x1, y0 = uv_to_px(u1, v1)
        d.rectangle([x0, y0, x1, y1], fill=base)
        for _ in range(n):
            x = rng.uniform(x0, x1)
            y = rng.uniform(y0, y1)
            r = rng.uniform(1, 3)
            c = tuple(max(0, min(255, b + rng.randint(-18, 18))) for b in speckle)
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        return (x0, y0, x1, y1)

    # stone: tile grid lines
    box = fill_region("stone", (105, 108, 115), (105, 108, 115))
    x0, y0, x1, y1 = box
    for i in range(1, 4):
        gx = x0 + (x1 - x0) * i / 4
        gy = y0 + (y1 - y0) * i / 4
        d.line([gx, y0, gx, y1], fill=(70, 72, 78), width=3)
        d.line([x0, gy, x1, gy], fill=(70, 72, 78), width=3)
    # plaster
    fill_region("plaster", (214, 205, 188), (214, 205, 188))
    # wood: plank lines
    box = fill_region("wood", (110, 78, 50), (110, 78, 50))
    x0, y0, x1, y1 = box
    for i in range(1, 6):
        gy = y0 + (y1 - y0) * i / 6
        d.line([x0, gy, x1, gy], fill=(80, 55, 34), width=3)
    # vermillion
    fill_region("vermillion", (168, 52, 40), (168, 52, 40))

    img.save(path)

# ---------- geometry ----------
verts = []   # (x, y, z)
uvs = []     # (u, v)
norms = []   # (nx, ny, nz)
faces = []   # (v_idx, vt_idx, vn_idx) x3, 1-based after assembly

def add_face(p, normal, region, uv_corners):
    u0, v0, u1, v1 = REGIONS[region]
    corner_uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]  # BL, BR, TR, TL
    idx = []
    for i, pos in enumerate(p):
        verts.append(pos)
        uu, vv = corner_uv[uv_corners[i]]
        uvs.append((uu, vv))
        norms.append(normal)
        idx.append(len(verts))  # v/vt/vn share the same index in our layout
    # quad -> two triangles (0,1,2) (0,2,3), positions must be CCW seen from outside
    faces.append((idx[0], idx[1], idx[2]))
    faces.append((idx[0], idx[2], idx[3]))

def add_box(center, size, region):
    cx, cy, cz = center
    sx, sy, sz = (s / 2 for s in size)
    # corners
    x0, x1 = cx - sx, cx + sx
    y0, y1 = cy - sy, cy + sy
    z0, z1 = cz - sz, cz + sz
    # each face: 4 positions CCW from outside + normal + uv corner order matching add_face
    F = [
        # +Z
        ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
        # -Z
        ([(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)], (0, 0, -1)),
        # +X
        ([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], (1, 0, 0)),
        # -X
        ([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], (-1, 0, 0)),
        # +Y
        ([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], (0, 1, 0)),
        # -Y
        ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
    ]
    for positions, normal in F:
        add_face(positions, normal, region, [0, 1, 2, 3])

def build_cell():
    # floor slab (top at y=0)
    add_box((0, -0.05, 0), (10, 0.1, 10), "stone")
    # north / east / west walls (height 4)
    add_box((0, 2, 4.9), (10, 4, 0.2), "plaster")
    add_box((4.9, 2, 0), (0.2, 4, 10), "plaster")
    add_box((-4.9, 2, 0), (0.2, 4, 10), "plaster")
    # south wall: two segments + lintel (entrance 2m wide, 3m high at center)
    add_box((-3, 2, -4.9), (4, 4, 0.2), "plaster")
    add_box((3, 2, -4.9), (4, 4, 0.2), "plaster")
    add_box((0, 3.5, -4.9), (2, 1, 0.2), "plaster")
    # roof beams (semi-open ceiling)
    for z in (-3, 0, 3):
        add_box((0, 4.1, z), (10, 0.2, 0.4), "wood")
    # entrance pillars
    add_box((-1.15, 1.5, -4.7), (0.3, 3, 0.3), "wood")
    add_box((1.15, 1.5, -4.7), (0.3, 3, 0.3), "wood")
    # central shrine
    add_box((0, 0.25, 2.5), (2.4, 0.5, 1.2), "stone")
    add_box((0, 0.9, 2.5), (1.4, 0.8, 0.8), "vermillion")
    add_box((0, 1.42, 2.5), (1.9, 0.16, 1.1), "wood")
    add_box((0, 1.62, 2.5), (1.2, 0.24, 0.7), "wood")
    # stepping stones (entrance -> shrine)
    for z in (-2.6, -0.6, 1.2):
        add_box((0, 0.03, z), (1.2, 0.06, 0.9), "stone")
    # stone lanterns
    add_box((-2.5, 0.3, 0.5), (0.4, 0.6, 0.4), "stone")
    add_box((2.5, 0.3, 0.5), (0.4, 0.6, 0.4), "stone")

MANIFEST = [
    "# cell.name: hajimari-no-hokora",
    "# cell.version: 0",
    "# cell.ambient: 1.0,0.95,0.85,0.6",
    "# cell.keylight: 1.0,0.8,0.55,2.0 ; 3,6,-2",
    "# collider: 0,0.8,2.5, 2.4,1.6,1.2",
    "# collider: -2.5,0.3,0.5, 0.4,0.6,0.4",
    "# collider: 2.5,0.3,0.5, 0.4,0.6,0.4",
    "# collider: -1.15,1.5,-4.7, 0.3,3,0.3",
    "# collider: 1.15,1.5,-4.7, 0.3,3,0.3",
]

def write_obj(path):
    lines = ["# CELL1 sample - see PROTOTYPE_SPEC.md"]
    lines += MANIFEST
    lines.append("mtllib none")
    lines.append("usemtl atlas")
    for v in verts:
        lines.append(f"v {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}")
    for t in uvs:
        lines.append(f"vt {t[0]:.4f} {t[1]:.4f}")
    for n in norms:
        lines.append(f"vn {n[0]:.1f} {n[1]:.1f} {n[2]:.1f}")
    for f in faces:
        lines.append("f " + " ".join(f"{i}/{i}/{i}" for i in f))
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    build_cell()
    write_obj(os.path.join(here, "cell001.obj"))
    make_atlas(os.path.join(here, "cell001.png"))
    print(f"verts={len(verts)} tris={len(faces)}")
