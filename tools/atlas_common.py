"""Shared atlas helpers for the cave cells (2026-11-13).

The rock region dominates the wall impression, so the cave atlases use
a rock-first layout (REGIONS_HALF: rock takes the whole left half of
the 512x512 atlas) and a CC0 photo texture for the rock itself.
Used by gen_basic_cells.py (006-009) and gen_variation_cells.py (014).
"""
import os

from cellgen import AtlasPainter

# Rock-first layout: rock 256x512 (~3x the pixels of the equal 3x2
# split); the five accent materials share the right half.
REGIONS_HALF = {
    "rock": (0.0, 0.0, 0.5, 1.0),
    "floor": (0.5, 0.5, 0.75, 1.0),
    "path": (0.75, 0.5, 1.0, 1.0),
    "wood": (0.5, 0.0, 0.75, 0.5),
    "crystal": (0.75, 0.25, 1.0, 0.5),
    "glow": (0.75, 0.0, 1.0, 0.25),
}


def _mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def rock_texture(p):
    """Procedural rock face (fallback when the CC0 photo asset is
    missing). Layers: multi-scale smooth noise for large uneven
    shading, irregular polygon facets with a darker lower edge,
    wavy strata lines and random-walk cracks, then fine grain.
    (The older `blobs` ellipses read as a polka-dot pattern.)"""
    import math
    from PIL import Image, ImageDraw, ImageFilter
    rng = p.rng
    x0, y0, x1, y1 = (int(v) for v in p.px("rock"))
    w, h = x1 - x0, y1 - y0
    base = (76, 64, 51)
    dark = (40, 34, 27)
    light = (122, 106, 86)

    fields = []
    for cells_x, weight in ((5, 0.50), (11, 0.30), (23, 0.20)):
        cells_y = max(2, int(cells_x * h / w))
        small = Image.new("L", (cells_x, cells_y))
        sp = small.load()
        for yy in range(cells_y):
            for xx in range(cells_x):
                sp[xx, yy] = rng.randint(0, 255)
        layer = small.resize((w, h), Image.BICUBIC).filter(
            ImageFilter.GaussianBlur(1.2))
        fields.append((layer.load(), weight))
    tile = Image.new("RGB", (w, h))
    tp = tile.load()
    for yy in range(h):
        for xx in range(w):
            v = sum(f[xx, yy] * weight for f, weight in fields) / 255.0
            shade = (v - 0.5) * 2.0
            c = _mix(base, light, shade * 0.75) if shade > 0 else \
                _mix(base, dark, -shade * 0.85)
            jitter = rng.randint(-6, 6)
            tp[xx, yy] = tuple(max(0, min(255, ch + jitter)) for ch in c)
    p.img.paste(tile, (x0, y0))
    p.d = ImageDraw.Draw(p.img)
    d = p.d

    palette = [(90, 78, 62), (63, 54, 44), (99, 86, 68), (56, 47, 39)]
    for _ in range(46):
        cx = rng.uniform(x0, x1)
        cy = rng.uniform(y0, y1)
        r = rng.uniform(10, 34)
        nv = rng.randint(5, 8)
        pts = []
        for k in range(nv):
            ang = 2 * 3.14159265 * k / nv + rng.uniform(-0.3, 0.3)
            rr = r * rng.uniform(0.55, 1.15)
            pts.append((cx + rr * math.cos(ang),
                        cy + rr * math.sin(ang) * 0.78))
        fill = _mix(rng.choice(palette), base, 0.35)
        d.polygon(pts, fill=fill)
        low = max(range(nv), key=lambda k: pts[k][1])
        up = min(range(nv), key=lambda k: pts[k][1])
        for a, b, col, wd in ((low, (low + 1) % nv, dark, 2),
                              (up, (up + 1) % nv, light, 1)):
            d.line([pts[a], pts[b]], fill=_mix(col, fill, 0.3), width=wd)

    for _ in range(7):
        yy = rng.uniform(y0 + 8, y1 - 8)
        pts = []
        xx = x0
        while xx <= x1:
            pts.append((xx, yy + rng.uniform(-2.5, 2.5)))
            xx += rng.uniform(14, 30)
        d.line(pts, fill=_mix(dark, base, 0.25), width=rng.randint(1, 3))

    for _ in range(16):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        pts = [(x, y)]
        for _ in range(rng.randint(4, 9)):
            x += rng.uniform(-9, 9)
            y += rng.uniform(4, 13)
            pts.append((x, y))
        d.line(pts, fill=_mix(dark, base, 0.1), width=1)

    for _ in range(900):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        r = rng.uniform(0.6, 1.7)
        delta = rng.randint(-13, 13)  # luminance only: no colour confetti
        c = tuple(max(0, min(255, ch + delta)) for ch in base)
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)


def rock_photo(p):
    """Rock face from a CC0 photo texture (user suggestion 2026-11-13:
    real rock imagery beats procedural generation for the wall region).

    Source: Poly Haven "Rock Boulder Cracked" diffuse 1K
    (https://polyhaven.com/a/rock_boulder_cracked), CC0, photography
    Dimitrios Savva / processing Dario Barresi. The raw scan is very
    orange (iron-rich rock), so it is graded toward muddy brown-grey
    and darkened before pasting. Falls back to rock_texture() when the
    asset file is missing."""
    from PIL import Image
    asset = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "assets", "rock_boulder_cracked_diff_1k.jpg")
    if not os.path.exists(asset):
        rock_texture(p)
        return
    x0, y0, x1, y1 = (int(v) for v in p.px("rock"))
    w, h = x1 - x0, y1 - y0
    src = Image.open(asset).convert("RGB")
    crop_w = int(src.height * w / h)
    left = (src.width - crop_w) // 2
    tile = src.crop((left, 0, left + crop_w, src.height)).resize((w, h))
    tp = tile.load()
    for yy in range(h):
        for xx in range(w):
            r, g, b = tp[xx, yy]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            # pull toward a muddy brown-grey, then darken for cave use
            t = 0.48
            r = (r * (1 - t) + lum * 1.03 * t) * 0.84
            g = (g * (1 - t) + lum * 0.93 * t) * 0.84
            b = (b * (1 - t) + lum * 0.79 * t) * 0.84
            tp[xx, yy] = (max(0, min(255, int(r))), max(0, min(255, int(g))),
                          max(0, min(255, int(b))))
    p.img.paste(tile, (x0, y0))
    from PIL import ImageDraw
    p.d = ImageDraw.Draw(p.img)


def make_atlas_rock(path, seed, regions=REGIONS_HALF):
    """Muddy, rocky palette (user feedback 2026-11-13: the basic cells'
    blue-grey rock read as purple; use warm brown-grey rock and mud)."""
    p = AtlasPainter(512, regions, seed=seed)
    rock_photo(p)
    p.tile_grid("floor", (82, 74, 62), (54, 47, 39))
    p.speckle("path", (122, 102, 76), n=1700, amp=16)
    p.planks("wood", (104, 72, 42), (70, 47, 27))
    p.gradient("crystal", (132, 198, 188), (42, 96, 90), speckle_n=200)
    p.gradient("glow", (255, 196, 96), (196, 108, 36), speckle_n=200)
    p.save(path)
