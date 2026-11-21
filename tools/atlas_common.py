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


def paint_calm_floor_path(p, seed):
    """Repaint the floor (dark stone slabs) and path (packed dirt) regions of
    painter p with calm, luminance-only shading (shared by make_atlas_dungeon and
    repaint_stair_atlas.py)."""
    import random
    from PIL import Image, ImageDraw
    from minekit import _field, _shade
    rng = random.Random(seed)
    S = 256

    def paste(name, tile):
        x0, y0, x1, y1 = (int(round(v)) for v in p.px(name))
        p.img.paste(tile.resize((x1 - x0, y1 - y0)), (x0, y0))

    # floor: dark stone slabs, no hue noise (pebbles shift all channels equally)
    t = _shade((74, 66, 56), [(_field(rng, S, S, 6, 6), 0.5), (_field(rng, S, S, 24, 24), 0.3),
                              (_field(rng, S, S, 96, 96), 0.2)], 0.65, 1.15)
    d = ImageDraw.Draw(t)
    for k in range(1, 4):                       # faint joints, darker only
        d.line([S * k / 4, 0, S * k / 4, S], fill=(46, 41, 35), width=2)
        d.line([0, S * k / 4, S, S * k / 4], fill=(46, 41, 35), width=2)
    for _ in range(200):
        x, y, r = rng.uniform(0, S), rng.uniform(0, S), rng.uniform(0.8, 3.0)
        g = rng.randint(-18, 20)
        d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=(76 + g, 68 + g, 58 + g))
    paste("floor", t)

    # path: packed dirt (minekit dirt)
    t = _shade((92, 74, 54), [(_field(rng, S, S, 6, 6), 0.5), (_field(rng, S, S, 24, 24), 0.3),
                              (_field(rng, S, S, 96, 96), 0.2)], 0.6, 1.2)
    d = ImageDraw.Draw(t)
    for _ in range(260):
        x, y, r = rng.uniform(0, S), rng.uniform(0, S), rng.uniform(0.8, 3.2)
        g = rng.randint(-26, 30)
        d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=(98 + g, 84 + g, 68 + g))
    paste("path", t)



def make_atlas_dungeon(path, seed, regions=REGIONS_HALF):
    """Atlas of the dungeon room cells 016-019 (2026-11-16 fix). Same as
    make_atlas_rock, but the floor and path regions are calm dark stone / packed
    dirt painted like the tunnel cells' dirt (minekit.make_atlas): smooth shading
    fields plus luminance-only pebbles. The old per-channel random speckle read
    as colour confetti when the floor was magnified."""
    p = AtlasPainter(512, regions, seed=seed)
    rock_photo(p)
    paint_calm_floor_path(p, seed)
    p.planks("wood", (104, 72, 42), (70, 47, 27))
    p.gradient("crystal", (132, 198, 188), (42, 96, 90), speckle_n=200)
    p.gradient("glow", (255, 196, 96), (196, 108, 36), speckle_n=200)
    p.save(path)


# ---------------------------------------------------------------------------
# Cell props: '# prop:' lines and the '# cell.lights' derived from the flames
# (dynamicworld docs/PROTOTYPE_SPEC.md section 2.1, ADR 0015, Issue #52).
#
# Grammar (the loader's): '# prop: <kind>, x,y,z[, rotY][, key=value ...]', cell-local
# metres, the position is the BASE of the flame (wick / top of the logs). The loader
# rotates the slot root with the node's rot, so the generators write local coordinates
# exactly as they do for '# cell.lights'. Kinds: torch / lantern / candle (cutout
# flames, at most 8 placed per slot) and hearth (particle fire, at most 4 PC / 2 Quest
# in the whole stage, nearest first). At most 16 '# prop:' lines per cell.
#
# Light rule (generator side only; the loader never makes a light from a prop):
#   - every flame prop gets one point light, at the flame base + PROP_KINDS offset
#     (x scale), or at `light_at` when the generator gives one (to keep an existing
#     light where it was). Colour / intensity / flicker come from the caller.
#   - a flame with flag= or lit= gets NO light: '# cell.lights' are static and would
#     keep shining while the flame is hidden or out.
#   - the cell's explicit non-flame lights (e.g. the dawn light of cell019) follow
#     the flame lights.
#   - the shader takes 4 lights. With more candidates, keep the 4 whose horizontal
#     distance to the nearest anchor (the cell centre and the centre of each declared
#     side door at 4.5 m) is smallest (ties: declaration order), then write them in
#     declaration order. The first light is also the '# cell.keylight'.
# ---------------------------------------------------------------------------
PROP_KINDS = {
    # kind: (family, light height above the flame base at scale 1)
    "torch": ("cutout", 0.17),
    "lantern": ("cutout", 0.10),
    "candle": ("cutout", 0.05),
    "hearth": ("particle", 0.6),
}
PROP_ATTRS = ("tint", "scale", "tilt", "flag", "lit", "len", "sound")
MAX_PROPS = 16
MAX_CUTOUT = 8
MAX_LIGHTS = 4
DOOR_ANCHORS = {"N": (0.0, 4.5), "S": (0.0, -4.5), "E": (4.5, 0.0), "W": (-4.5, 0.0)}


def _pn(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def prop(kind, x, y, z, rot=None, light=None, light_at=None, **attrs):
    """One prop. light = (r, g, b, intensity, flicker) for a flame that lights the
    cell (None: no light); attrs are the key=value attributes (tint='#rrggbb', ...)."""
    assert kind in PROP_KINDS, f"unknown prop kind {kind}"
    for k in attrs:
        assert k in PROP_ATTRS, f"unknown prop attribute {k}"
    return {"kind": kind, "pos": (x, y, z), "rot": rot, "attrs": dict(attrs),
            "light": light, "light_at": light_at}


def prop_line(p):
    x, y, z = p["pos"]
    s = f"# prop: {p['kind']}, {_pn(x)},{_pn(y)},{_pn(z)}"
    if p["rot"] is not None:
        s += f", {_pn(p['rot'])}"
    for k, v in p["attrs"].items():
        s += f", {k}={_pn(v) if isinstance(v, float) else v}"
    return s


def prop_lines(props):
    assert len(props) <= MAX_PROPS, f"{len(props)} props > {MAX_PROPS} per cell"
    assert sum(PROP_KINDS[p["kind"]][0] == "cutout" for p in props) <= MAX_CUTOUT, \
        f"more than {MAX_CUTOUT} cutout flames (the slot places only {MAX_CUTOUT})"
    return [prop_line(p) for p in props]


def flame_light(p):
    """(x, y, z, r, g, b, intensity, flicker) of a flame prop, or None (see the rule)."""
    if p["light"] is None or "flag" in p["attrs"] or "lit" in p["attrs"]:
        return None
    if p["light_at"] is not None:
        lx, ly, lz = p["light_at"]
    else:
        x, y, z = p["pos"]
        lx, ly, lz = x, y + PROP_KINDS[p["kind"]][1] * float(p["attrs"].get("scale", 1.0)), z
    return (lx, ly, lz) + tuple(p["light"])


def derive_lights(props, extra=(), doors=()):
    """'# cell.lights' entries: flame lights in declaration order, then `extra`
    (explicit non-flame lights), reduced to MAX_LIGHTS by the anchor rule above."""
    cands = [lt for lt in (flame_light(p) for p in props) if lt is not None] + list(extra)
    if len(cands) <= MAX_LIGHTS:
        return cands
    anchors = [(0.0, 0.0)] + [DOOR_ANCHORS[d[0]] for d in doors if d[:1] in DOOR_ANCHORS]

    def score(i):
        x, _, z = cands[i][:3]
        return (min(((x - ax) ** 2 + (z - az) ** 2) ** 0.5 for ax, az in anchors), i)
    keep = sorted(sorted(range(len(cands)), key=score)[:MAX_LIGHTS])
    return [cands[i] for i in keep]
