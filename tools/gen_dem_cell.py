#!/usr/bin/env python3
"""DEM -> dynamicworld scenery-cell generator (tools/gen_dem_cell.py).

Converts one GSI elevation-tile PNG (256x256) into a single 10m x 10m
diorama cell in the spec-v0 OBJ format used by CellLoader:
  - shared v/vt/vn arrays + triangle faces (the loader indexes v/vt/vn
    separately and expands internally, so a shared grid is valid here;
    verified against Packages/jp.hyde4280.cellloader/Runtime/Scripts/CellLoader.cs
    in the local dynamicworld snapshot)
  - manifest header lines in the same style as gen_cell001.py
  - one 512x512 atlas, painted hypsometrically (height -> colour)

Usage:
  python3 gen_dem_cell.py <dem.png> --name my-mountain --out outdir
  python3 gen_dem_cell.py --selftest   # synthetic cone, no real tile needed

GSI DEM tile decoding (VERIFIED 2026-11-05 against Mt. Fuji: the z14
tile 14505/6469 decodes to a maximum of 3774.04 m right at the summit
pixel, vs the known 3775.6 m summit; the z13 tiles agree at 3773 m):
raw = R*65536 + G*256 + B (24-bit); if raw < 2**23 then
h = raw * 0.01 m, else h = (raw - 2**24) * 0.01 m.  raw == 2**23 is the
no-data marker and is replaced by the tile minimum here (counted and
reported).  Tile URL pattern: https://cyberjapandata.gsi.go.jp/xyz/dem/
{z}/{x}/{y}.png  (one tile ~= 1.28 km at the zoom used in the 2026-11-05
discussion, so one tile shrunk into one 10 m cell is a diorama, not 1:1
terrain -- at true 10 m scale real terrain is almost flat).

Vertical scale is a design decision, not a fact of the data: by default
the tile's height range is fitted into --fit-height metres (default 8)
inside the 10 m cell.  Pass --vertical-scale to use a fixed m-per-m
factor instead (e.g. the true diorama scale 10/1280 for a 1.28 km tile).

Costs at the default --grid 128 (same order as cell003):
  tris = 2 * 128 * 128 = 32768; shared verts = 129 * 129 = 16641;
  OBJ lines ~= verts + uvs + normals + faces + header ~= 83k lines,
  i.e. roughly the cell003 parse cost, NOT the ~327k lines an expanded
  triangle soup would cost.  No collider is emitted: this is a
  look-at diorama cell, matching the 2026-11-05 conclusion that
  shader/displacement terrain has no collider (a coarse stepped
  collider grid is a separate, later option).

cell005 "fujisan" production (2026-11-05; regenerated 2026-11-06): the
summit sits near a tile corner at z13, so the four tiles x=7252..7253,
y=3234..3235 were stitched into a 512x512 canvas and a summit-centred
256x256 window was cropped from it; that crop is the input PNG. The crop
covers ~3.99 km x 3.98 km on the ground. First version fitted the height
range 2087.7..3769.7 m to 8 m, which exaggerated the vertical scale
~1.9x over the horizontal and looked too sharp in-world; the current
version uses --fit-height 4.2 (true scale for this crop) plus --skirt
(perimeter walls down to y=0 so the hem lands on the floor). Source data:
GSI (Geospatial Information Authority of Japan) elevation tiles,
https://cyberjapandata.gsi.go.jp/xyz/dem_png/{z}/{x}/{y}.png
"""
import argparse
import math
import os
import sys

from PIL import Image, ImageDraw


def decode_gsi_dem(img):
    """Return (heights[row][col] in metres, nodata_count)."""
    w, h = img.size
    px = img.load()
    heights = []
    nodata = 0
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b = px[x, y][:3]
            raw = (r << 16) | (g << 8) | b
            if raw == 1 << 23:
                nodata += 1
                row.append(None)
            elif raw < (1 << 23):
                row.append(raw * 0.01)
            else:
                row.append((raw - (1 << 24)) * 0.01)
        heights.append(row)
    valid = [v for row in heights for v in row if v is not None]
    fill = min(valid) if valid else 0.0
    heights = [[fill if v is None else v for v in row] for row in heights]
    return heights, nodata


def downsample(heights, grid):
    """Average blocks of the source grid down to (grid+1) x (grid+1) samples."""
    src_h = len(heights)
    src_w = len(heights[0])
    out = []
    for j in range(grid + 1):
        y0 = min(j * src_h // grid, src_h - 1)
        y1 = min(max(y0 + 1, (j + 1) * src_h // grid), src_h)
        row = []
        for i in range(grid + 1):
            x0 = min(i * src_w // grid, src_w - 1)
            x1 = min(max(x0 + 1, (i + 1) * src_w // grid), src_w)
            s = 0.0
            n = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    s += heights[y][x]
                    n += 1
            row.append(s / n)
        out.append(row)
    return out


def hypsometric(t):
    """t in [0,1] -> RGB, low green -> brown -> rock grey -> snow white."""
    stops = [(0.00, (74, 124, 62)), (0.35, (122, 138, 72)),
             (0.60, (139, 105, 72)), (0.80, (120, 120, 120)),
             (1.00, (245, 245, 245))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3))
    return stops[-1][1]


def build(name, heights, grid, fit_height, vertical_scale, outdir,
          skirt=False):
    samples = downsample(heights, grid)
    flat = [v for row in samples for v in row]
    h_min, h_max = min(flat), max(flat)
    span = h_max - h_min
    if vertical_scale is not None:
        scale = vertical_scale
    else:
        scale = (fit_height / span) if span > 0 else 0.0

    # Positions: x in [-5, 5], z in [-5, 5]; PNG row 0 is north -> -z is
    # south in cell convention (entrance face); flip so north is +z.
    verts, uvs, norms = [], [], []
    for j in range(grid + 1):
        for i in range(grid + 1):
            x = -5.0 + 10.0 * i / grid
            z = 5.0 - 10.0 * j / grid
            y = (samples[j][i] - h_min) * scale
            verts.append((x, y, z))
            uvs.append((i / grid, 1.0 - j / grid))
    # Normals from central differences on the height field.
    for j in range(grid + 1):
        for i in range(grid + 1):
            hl = samples[j][max(0, i - 1)]
            hr = samples[j][min(grid, i + 1)]
            hd = samples[max(0, j - 1)][i]
            hu = samples[min(grid, j + 1)][i]
            dx = 10.0 / grid
            nx = -((hr - hl) * scale) / (2 * dx)
            nz = -((hu - hd) * scale) / (2 * dx)
            n = (nx, 1.0, nz)
            ln = math.sqrt(sum(c * c for c in n))
            norms.append(tuple(c / ln for c in n))
    faces = []
    for j in range(grid):
        for i in range(grid):
            a = j * (grid + 1) + i + 1
            b = a + 1
            c = a + grid + 1
            d = c + 1
            # Winding must match cellgen.py: CCW seen from the normal
            # side, i.e. the geometric normal points up like the vn
            # above. (a, c, d)/(a, d, b) pointed down and the cell
            # rendered inside-out in-world; fixed 2026-11-06.
            faces.append((a, d, c))
            faces.append((a, b, d))

    if skirt:
        # Perimeter skirt: vertical walls from the border down to y=0, so
        # the heightfield sheet lands on the floor all the way around
        # instead of floating at border-terrain height. The terrain itself
        # is untouched. Loop order N -> E -> S -> W keeps the segment
        # winding outward with triangles (P, P', Q') / (P, Q', Q).
        loop = ([(0, i) for i in range(grid + 1)]
                + [(j, grid) for j in range(1, grid + 1)]
                + [(grid, i) for i in range(grid - 1, -1, -1)]
                + [(j, 0) for j in range(grid - 1, 0, -1)])
        top_idx = [j * (grid + 1) + i for (j, i) in loop]
        n_pts = len(loop)
        out_seg = []
        for k in range(n_pts):
            x0, _, z0 = verts[top_idx[k]]
            x1, _, z1 = verts[top_idx[(k + 1) % n_pts]]
            dx, dz = x1 - x0, z1 - z0
            ln = math.hypot(dx, dz) or 1.0
            out_seg.append((-dz / ln, dx / ln))  # outward (nx, nz)
        bot_idx = []
        for k in range(n_pts):
            x, _, z = verts[top_idx[k]]
            nx = out_seg[k - 1][0] + out_seg[k][0]
            nz = out_seg[k - 1][1] + out_seg[k][1]
            ln = math.hypot(nx, nz) or 1.0
            verts.append((x, 0.0, z))
            uvs.append(uvs[top_idx[k]])
            norms.append((nx / ln, 0.0, nz / ln))
            bot_idx.append(len(verts) - 1)
        for k in range(n_pts):
            k2 = (k + 1) % n_pts
            p, q = top_idx[k] + 1, top_idx[k2] + 1
            p2, q2 = bot_idx[k] + 1, bot_idx[k2] + 1
            faces.append((p, p2, q2))
            faces.append((p, q2, q))

    manifest = [
        f"# cell.name: {name}",
        "# cell.version: 0",
        "# cell.ambient: 1.0,1.0,1.0,0.7",
        "# cell.lightvolume: 1.0,1.0,1.0,0.7",
        "# cell.keylight: 1.0,0.95,0.85,1.5 ; 3,6,-2",
        "# DEM diorama cell: no collider (look-at only, see header)",
    ]
    lines = [f"# DEM diorama cell {name} -- source: GSI elevation tiles (dem_png), via tools/gen_dem_cell.py"]
    lines += manifest + ["mtllib none", "usemtl atlas"]
    lines += [f"v {x:.3f} {y:.3f} {z:.3f}" for (x, y, z) in verts]
    lines += [f"vt {u:.4f} {v:.4f}" for (u, v) in uvs]
    lines += [f"vn {x:.3f} {y:.3f} {z:.3f}" for (x, y, z) in norms]
    lines += ["f " + " ".join(f"{a}/{a}/{a}" for a in fc) for fc in faces]
    obj_path = os.path.join(outdir, f"{name}.obj")
    with open(obj_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    # Atlas: paint the height field itself as a 512x512 hypsometric map.
    size = 512
    img = Image.new("RGB", (size, size), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for py in range(size):
        j = min(grid, py * grid // size)
        for px_ in range(size):
            i = min(grid, px_ * grid // size)
            t = 0.0 if span == 0 else (samples[j][i] - h_min) / span
            img.putpixel((px_, py), hypsometric(t))
    png_path = os.path.join(outdir, f"{name}.png")
    img.save(png_path)
    return {
        "obj": obj_path, "png": png_path, "tris": len(faces),
        "verts": len(verts), "lines": len(lines),
        "obj_bytes": os.path.getsize(obj_path),
        "h_min": h_min, "h_max": h_max, "scale": scale,
        "peak_y": span * scale,
    }


def selftest(outdir):
    """Synthetic cone DEM, encoded with the same formula decode uses."""
    size = 256
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            dx = (x - 127.5) / 127.5
            dy = (y - 127.5) / 127.5
            dist = math.sqrt(dx * dx + dy * dy)
            h = max(0.0, 1000.0 * (1.0 - dist))  # 0..1000 m cone
            raw = int(round(h / 0.01))
            px[x, y] = ((raw >> 16) & 255, (raw >> 8) & 255, raw & 255)
    heights, nodata = decode_gsi_dem(img)
    peak = max(v for row in heights for v in row)
    assert nodata == 0, nodata
    # Apex falls between pixels, so the sampled peak is 1000*(1-sqrt(2)/255)
    # ~= 994.5 m, not 1000 m: check the round-trip against that, not 1000.
    assert 990.0 < peak <= 1000.0, peak
    r = build("dem-selftest", heights, 128, 8.0, None, outdir)
    r["peak"] = peak
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", nargs="?")
    ap.add_argument("--name", default="dem-cell")
    ap.add_argument("--out", default="out")
    ap.add_argument("--grid", type=int, default=128)
    ap.add_argument("--fit-height", type=float, default=8.0)
    ap.add_argument("--vertical-scale", type=float, default=None)
    ap.add_argument("--skirt", action="store_true",
                    help="add perimeter walls down to y=0")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if args.selftest:
        r = selftest(args.out)
        print(f"selftest OK: cone round-trip peak {r['peak']:.1f} m (sampled apex)")
    else:
        if not args.png:
            ap.error("give a DEM PNG, or --selftest")
        heights, nodata = decode_gsi_dem(Image.open(args.png).convert("RGB"))
        r = build(args.name, heights, args.grid, args.fit_height,
                  args.vertical_scale, args.out, skirt=args.skirt)
        print(f"nodata pixels replaced with tile minimum: {nodata}")
    print(f"tris={r['tris']} verts={r['verts']} obj_lines={r['lines']} "
          f"obj_bytes={r['obj_bytes']} height_range={r['h_min']:.1f}.."
          f"{r['h_max']:.1f} m peak_y={r['peak_y']:.2f} m "
          f"(scale={r['scale']:.5f})")
    print(f"wrote {r['obj']} and {r['png']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
