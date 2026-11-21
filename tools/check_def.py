#!/usr/bin/env python3
"""Validate a world definition (defs/*.txt) against the cells it uses.

Mirrors the checks of the runtime parser (dynamicworld WorldDefinition.cs) and adds
the ones only the data side can do: the cell files exist, every edge end is a door the
cell really declares, vertical pairs agree on their kind, every node can be reached,
and the key flags can be collected in some order (no soft lock).

Node attributes after the rotation are a proposal (DUNGEON_DESIGN.md section 4.1):
    switch=<flag>          the node's cell has a `# switch:` point that raises <flag>
    spawn=<kind>:<count>   enemies at the cell's `# spawn:` points (may repeat)
    clear=<flag>           <flag> is raised when the node's enemies are defeated

Each cell's `# prop:` lines (dynamicworld PROTOTYPE_SPEC section 2.1, Issue #52) are
checked like the loader parses them: known kind (torch / lantern / candle / hearth),
numeric position inside the cell box (x, z -5..5, y 0..cell.pitch.y, default 6),
optional numeric rotY, attributes tint=#rrggbb, scale 0.1..4, tilt -90..90,
flag / lit integers 0..2047 (len / sound are accepted, uv is reserved), at most 16
lines. Warnings: more than 8 cutout flames (the slot places 8), more than 2 hearths
in one cell (the particle pool is 4 on PC / 2 on Quest for the whole stage), and a
flame whose centre (base + 0.17 torch / 0.10 lantern / 0.05 candle / 0.6 hearth, x scale)
has no `# cell.lights` entry within 0.5 m ('flame without light'; flames with
flag= / lit= get no light by the generator rule, atlas_common.derive_lights).

Usage: check_def.py defs/mine01.txt [--map]      (exit status 1 on errors)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CELLS = os.path.join(HERE, "..", "cells")
FACES = ["N", "E", "S", "W", "U", "D"]
STEP = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}
MAX_NODES, MAX_EDGES, MAX_KEY = 64, 128, 2047
MODES = ("fixed", "generated")
MULTI = ("solo", "party", "phase")
NODE_ATTRS = ("switch", "spawn", "clear")
EDGE_OPTS = ("key", "gate", "open")
# '# prop:' (the loader's CellLoader.ParsePropLine; the generators' atlas_common.PROP_KINDS)
PROP_FAMILY = {"torch": "cutout", "lantern": "cutout", "candle": "cutout", "hearth": "particle"}
# flame centre above the base at scale 1 (= atlas_common.PROP_KINDS light height)
PROP_CENTRE = {"torch": 0.17, "lantern": 0.10, "candle": 0.05, "hearth": 0.6}
MAX_PROPS, MAX_CUTOUT, MAX_HEARTH, FLAME_LIGHT_DIST = 16, 8, 2, 0.5
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _num(v):
    try:
        f = float(v)
    except ValueError:
        return None
    return f if f == f and abs(f) != float("inf") else None


def check_props(cell, info, pitch):
    """Errors / warnings / notes for the '# prop:' lines of one cell."""
    errs, warns, notes = [], [], []
    if len(info["props"]) > MAX_PROPS:
        errs.append(f"{cell}: {len(info['props'])} '# prop:' lines > {MAX_PROPS} (the loader ignores the rest)")
    kinds = []
    for ln, body in info["props"]:
        t = [x.strip() for x in body.split(",")]
        tag = f"{cell} line {ln}: prop"
        if len(t) < 4:
            errs.append(f"{tag}: malformed (needs <kind>, x,y,z): {body.strip()}")
            continue
        kind = t[0].lower()
        if kind not in PROP_FAMILY:
            errs.append(f"{tag}: unknown kind '{t[0]}' (the loader ignores it)")
            continue
        pos = [_num(v) for v in t[1:4]]
        if None in pos:
            errs.append(f"{tag}: position is not numeric: {body.strip()}")
            continue
        x, y, z = pos
        if not (-5 <= x <= 5 and -5 <= z <= 5 and 0 <= y <= pitch):
            errs.append(f"{tag}: {kind} at ({x:g},{y:g},{z:g}) is outside the cell box "
                        f"(x,z -5..5, y 0..{pitch:g})")
            continue
        attrs = {}
        for i, tok in enumerate(t[4:], 4):
            if not tok:
                continue
            if "=" not in tok:
                if i != 4 or _num(tok) is None:
                    errs.append(f"{tag}: malformed field '{tok}' (rotY is the 5th field, then key=value)")
                continue
            k, _, v = (a.strip() for a in tok.partition("="))
            k = k.lower()
            if k in attrs:
                warns.append(f"{tag}: attribute '{k}' given twice (the last one wins)")
            attrs[k] = v
            if k == "tint":
                if not HEX.match(v):
                    errs.append(f"{tag}: tint '{v}' is not #rrggbb")
            elif k == "scale":
                f = _num(v)
                if f is None or not 0.1 <= f <= 4:
                    errs.append(f"{tag}: scale '{v}' is outside 0.1..4")
            elif k == "tilt":
                f = _num(v)
                if f is None or not -90 <= f <= 90:
                    errs.append(f"{tag}: tilt '{v}' is outside -90..90")
                elif PROP_FAMILY[kind] != "particle":
                    notes.append(f"{tag}: tilt has no effect on the cutout kind {kind}")
            elif k in ("flag", "lit"):
                if not v.isdigit() or int(v) > MAX_KEY:
                    errs.append(f"{tag}: {k} must be a flag 0..{MAX_KEY}: '{v}'")
            elif k == "len":
                if _num(v) is None:
                    errs.append(f"{tag}: len '{v}' is not a number")
            elif k == "sound":
                pass
            elif k == "uv":
                warns.append(f"{tag}: uv= is reserved (syntax not decided), the loader ignores it")
            else:
                warns.append(f"{tag}: unknown attribute '{k}' (the loader ignores it)")
        kinds.append(kind)
        if "flag" in attrs or "lit" in attrs:
            continue      # no light by the generator rule
        sc = _num(attrs.get("scale", "1")) or 1.0
        cy = y + PROP_CENTRE[kind] * sc      # measured from the flame centre, not the base
        near = min((((x - a) ** 2 + (cy - b) ** 2 + (z - c) ** 2) ** 0.5 for a, b, c in info["lights"]),
                   default=None)
        if near is None or near > FLAME_LIGHT_DIST:
            warns.append(f"{tag}: flame without light: {kind} at ({x:g},{y:g},{z:g}) has no "
                         f"'# cell.lights' entry within {FLAME_LIGHT_DIST} m"
                         + ("" if near is None else f" (nearest {near:.2f} m)"))
    cut = sum(PROP_FAMILY[k] == "cutout" for k in kinds)
    hearth = kinds.count("hearth")
    if cut > MAX_CUTOUT:
        warns.append(f"{cell}: {cut} cutout flames > {MAX_CUTOUT} per slot (the rest are not placed)")
    if hearth > MAX_HEARTH:
        warns.append(f"{cell}: {hearth} hearths in one cell > {MAX_HEARTH} (particle pool: PC 4 / Quest 2 "
                     "for the whole stage, nearest first)")
    return errs, warns, notes, kinds


def cell_manifest(cell):
    """doors {face: kind}, counts of switch / spawn lines, save flag; None if missing."""
    path = os.path.join(CELLS, cell + ".obj")
    if not os.path.exists(path):
        return None
    info = {"doors": {}, "switch": 0, "spawn": 0, "save": False, "props": [], "lights": []}
    for ln, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.startswith("#"):
            continue      # the loader reads '#' lines anywhere in the file
        if line.startswith("# door:"):
            p = [x.strip() for x in line.split(":", 1)[1].split(",")]
            info["doors"][p[0]] = p[1].lower() if len(p) > 1 else ("hatch" if p[0] in "UD" else "")
        elif line.startswith("# switch:"):
            info["switch"] += 1
        elif line.startswith("# spawn:"):
            info["spawn"] += 1
        elif line.startswith("# cell.save:"):
            info["save"] = line.split(":", 1)[1].strip().startswith("1")
        elif line.startswith("# prop:"):
            info["props"].append((ln, line.split(":", 1)[1]))
        elif line.startswith("# cell.lights:"):
            for seg in line.split(":", 1)[1].split(";"):
                v = [_num(a) for a in seg.split(",")[:3]]
                if len(v) == 3 and None not in v:
                    info["lights"].append(tuple(v))
    return info


def check(path, show_map=False):
    errs, warns, notes = [], [], []
    head, nodes, order, edges = {}, {}, [], []
    for ln, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            errs.append(f"line {ln}: trailing comment (the loader does not strip '#'): {line}")
            continue
        if ":" not in line:
            warns.append(f"line {ln}: no 'key: value': {line}")
            continue
        key, value = (s.strip() for s in line.split(":", 1))
        if key == "node":
            t = [s.strip() for s in value.split(",")]
            if len(t) < 6:
                errs.append(f"line {ln}: bad node line: {value}")
                continue
            nid, cell = t[0], t[1]
            try:
                x, y, z, rot = (int(v) for v in t[2:6])
            except ValueError:
                errs.append(f"line {ln}: node position / rotation must be integers: {value}")
                continue
            if not 0 <= rot <= 3:
                errs.append(f"line {ln}: rotation {rot} is outside 0..3")
            if cell.startswith("@"):
                errs.append(f"line {ln}: composite nodes are not supported by the loader yet")
                continue
            if nid in nodes:
                errs.append(f"line {ln}: duplicate node id {nid}")
                continue
            attrs = {"switch": [], "spawn": [], "clear": []}
            for a in t[6:]:
                k, _, v = a.partition("=")
                if k not in NODE_ATTRS or not v:
                    warns.append(f"line {ln}: unknown node attribute '{a}'")
                    continue
                if k == "spawn":
                    kind, _, cnt = v.partition(":")
                    if not kind or not cnt.isdigit():
                        errs.append(f"line {ln}: spawn must be <kind>:<count>: {a}")
                        continue
                    attrs[k].append((kind, int(cnt)))
                elif not v.isdigit() or int(v) > MAX_KEY:
                    errs.append(f"line {ln}: {k} must be a flag 0..{MAX_KEY}: {a}")
                else:
                    attrs[k].append(int(v))
            nodes[nid] = {"cell": cell, "pos": (x, y, z), "rot": rot % 4, "attrs": attrs, "ln": ln}
            order.append(nid)
        elif key == "edge":
            edges.append((ln, value))
        elif key == "group":
            errs.append(f"line {ln}: group is not supported by the loader yet")
        elif key == "param":
            head.setdefault("param", {}).update(
                dict((kv.split("=")[0].strip(), kv.split("=")[1].strip())
                     for kv in value.split(",") if "=" in kv))
        else:
            head[key] = value

    # ---- header
    for k in ("spec.version", "world.name", "world.rev", "world.mode", "world.multiplayer", "world.root"):
        if k not in head:
            errs.append(f"missing '{k}'")
    if head.get("world.mode", "fixed") not in MODES:
        errs.append(f"world.mode must be one of {MODES}")
    if head.get("world.multiplayer", "solo") not in MULTI:
        errs.append(f"world.multiplayer must be one of {MULTI}")
    if not head.get("world.rev", "0").isdigit():
        errs.append("world.rev must be an integer")
    root = head.get("world.root")
    if root is not None and root not in nodes:
        errs.append(f"world.root '{root}' is not a node")
    if len(nodes) > MAX_NODES:
        errs.append(f"{len(nodes)} nodes > loader limit {MAX_NODES}")

    # ---- nodes
    at, cells = {}, {}
    for nid in order:
        n = nodes[nid]
        if n["pos"] in at:
            errs.append(f"line {n['ln']}: {nid} shares its position with {at[n['pos']]}")
        at[n["pos"]] = nid
        if n["cell"] not in cells:
            cells[n["cell"]] = cell_manifest(n["cell"])
        m = cells[n["cell"]]
        if m is None:
            errs.append(f"line {n['ln']}: {nid}: cells/{n['cell']}.obj does not exist")
            continue
        if not m["doors"]:
            errs.append(f"line {n['ln']}: {nid}: {n['cell']} declares no door (not walkable)")
        if n["attrs"]["switch"] and m["switch"] < len(n["attrs"]["switch"]):
            errs.append(f"line {n['ln']}: {nid}: switch= needs a '# switch:' line in {n['cell']}")
        want = sum(c for _, c in n["attrs"]["spawn"])
        if want > m["spawn"]:
            errs.append(f"line {n['ln']}: {nid}: {want} enemies > {m['spawn']} '# spawn:' points in {n['cell']}")
        if n["attrs"]["clear"] and not want:
            errs.append(f"line {n['ln']}: {nid}: clear= without spawn=")

    # ---- cell props
    pitch = _num(str(head.get("param", {}).get("cell.pitch.y", 6))) or 6.0
    prop_cells = {}
    for cell, m in cells.items():
        if m is None:
            continue
        e, w, nt, kinds = check_props(cell, m, pitch)
        errs += e
        warns += w
        notes += nt
        if kinds:
            prop_cells[cell] = kinds
    if prop_cells:
        hearths = sum(k.count("hearth") for k in prop_cells.values())
        notes.append(f"props: {sum(len(k) for k in prop_cells.values())} in {len(prop_cells)} cells ("
                     + ", ".join(f"{c} " + "+".join(f"{k.count(n)} {n}" for n in sorted(set(k)))
                                 for c, k in sorted(prop_cells.items()))
                     + f"); hearth cells {sum(1 for k in prop_cells.values() if 'hearth' in k)}, "
                     f"hearths {hearths} (pool PC 4 / Quest 2 for the stage, nearest first)")

    # ---- edges
    used = {}        # (node, local face) -> edge line
    graph = {nid: [] for nid in nodes}   # nid -> [(other, key)]
    if len(edges) > MAX_EDGES:
        errs.append(f"{len(edges)} edges > loader limit {MAX_EDGES}")
    for ln, value in edges:
        t = [s.strip() for s in value.split(",")]
        ends = []
        ok = len(t) >= 2
        for e in t[:2] if ok else []:
            p = e.split(".")
            if len(p) != 2 or p[0] not in nodes or p[1] not in FACES:
                ok = False
            else:
                ends.append((p[0], p[1]))
        if not ok:
            errs.append(f"line {ln}: bad edge (unknown node, face, or composite endpoint): {value}")
            continue
        key = None
        for opt in t[2:]:
            k, _, v = opt.partition("=")
            if k not in EDGE_OPTS or not v:
                warns.append(f"line {ln}: unknown edge option '{opt}'")
            elif k == "key":
                if not v.isdigit() or int(v) > MAX_KEY:
                    errs.append(f"line {ln}: key must be a flag 0..{MAX_KEY}: {opt}")
                else:
                    key = int(v)
        (a, fa), (b, fb) = ends
        na, nb = nodes[a], nodes[b]
        bad = False
        for nid, f in ends:
            m = cells.get(nodes[nid]["cell"])
            if m is not None and f not in m["doors"]:
                errs.append(f"line {ln}: {nid} ({nodes[nid]['cell']}) has no door {f}")
                bad = True
            if (nid, f) in used:
                errs.append(f"line {ln}: {nid}.{f} is already used by the edge on line {used[(nid, f)]}")
                bad = True
            used[(nid, f)] = ln
        ia, ib = FACES.index(fa), FACES.index(fb)
        (ax, ay, az), (bx, by, bz) = na["pos"], nb["pos"]
        if ia >= 4 or ib >= 4:
            if ia < 4 or ib < 4 or ia == ib:
                errs.append(f"line {ln}: a vertical edge must join U and D: {value}")
                continue
            dy = 1 if ia == 4 else -1
            if (ax, az) != (bx, bz) or by != ay + dy:
                errs.append(f"line {ln}: vertical edge does not connect stacked nodes: {value}")
                bad = True
            if (na["rot"] & 1) != (nb["rot"] & 1):
                errs.append(f"line {ln}: vertical edge joins cells a quarter turn apart: {value}")
                bad = True
            ma, mb = cells.get(na["cell"]), cells.get(nb["cell"])
            if ma and mb and fa in ma["doors"] and fb in mb["doors"] and ma["doors"][fa] != mb["doors"][fb]:
                errs.append(f"line {ln}: vertical kinds differ: {a}.{fa} is '{ma['doors'][fa]}', "
                            f"{b}.{fb} is '{mb['doors'][fb]}'")
                bad = True
        else:
            wa, wb = (ia + na["rot"]) % 4, (ib + nb["rot"]) % 4
            if (ax + STEP[wa][0], ay, az + STEP[wa][1]) != (bx, by, bz):
                errs.append(f"line {ln}: edge does not connect adjacent nodes: {value} "
                            f"({a}.{fa} faces world {FACES[wa]})")
                bad = True
            elif (bx + STEP[wb][0], bz + STEP[wb][1]) != (ax, az):
                errs.append(f"line {ln}: edge faces do not point at each other: {value} "
                            f"({b}.{fb} faces world {FACES[wb]})")
                bad = True
        if not bad:
            graph[a].append((b, key))
            graph[b].append((a, key))

    # ---- sealed doors, resident load
    sealed = []
    for nid in order:
        m = cells.get(nodes[nid]["cell"])
        if m:
            sealed += [f"{nid}.{f}" for f in m["doors"] if (nid, f) not in used]
    if sealed:
        notes.append("sealed doors (declared, no edge): " + ", ".join(sealed))
    slots = int(float(head.get("param", {}).get("slots.count", 8)))
    worst = max(((len(graph[n]) + 1, n) for n in order), default=(0, ""))
    if worst[0] > slots:
        errs.append(f"{worst[1]} needs {worst[0]} resident cells > slots.count {slots}")
    else:
        notes.append(f"resident cells: at most {worst[0]} (at {worst[1]}), slots.count {slots}")

    # ---- reachability and key order
    if root in nodes:
        sources = {}
        for nid in order:
            for f in nodes[nid]["attrs"]["switch"] + nodes[nid]["attrs"]["clear"]:
                sources.setdefault(f, []).append(nid)
        keys = sorted({k for adj in graph.values() for _, k in adj if k is not None})
        for k in keys:
            if k not in sources:
                warns.append(f"key={k} has no switch= / clear= node that raises it")
        have, seen, steps = set(), set(), []
        while True:
            seen, stack = {root}, [root]
            while stack:
                cur = stack.pop()
                for other, k in graph[cur]:
                    if other not in seen and (k is None or k in have):
                        seen.add(other)
                        stack.append(other)
            new = {f for f, ns in sources.items() if f not in have and any(n in seen for n in ns)}
            if not new:
                break
            have |= new
            steps.append(f"{len(seen)} nodes -> flags {sorted(new)}")
        if steps:
            notes.append("progress: " + "; ".join(steps) + f"; {len(seen)} nodes")
        lost = [n for n in order if n not in seen]
        ever = {root}
        stack = [root]
        while stack:
            for other, _ in graph[stack.pop()]:
                if other not in ever:
                    ever.add(other)
                    stack.append(other)
        for n in lost:
            if n not in ever:
                errs.append(f"{n} cannot be reached from {root} (no path)")
            elif all(k in sources for k in keys):
                errs.append(f"{n} is locked behind a key that is only raised behind that key (soft lock)")
            else:
                warns.append(f"{n} is behind a key that nothing raises yet")
        unused = sorted(f for f in sources if f not in keys)
        if unused:
            notes.append("flags raised but not used as a key: " + ", ".join(str(f) for f in unused))
        saves = [n for n in order if cells.get(nodes[n]["cell"]) and cells[nodes[n]["cell"]]["save"]]
        notes.append("save points: " + (", ".join(saves) if saves else "none"))

    name = os.path.basename(path)
    print(f"{name}: world={head.get('world.name')} rev={head.get('world.rev')} "
          f"nodes={len(nodes)} edges={len(edges)} cells={len(cells)}")
    for s in notes:
        print("  note: " + s)
    for s in warns:
        print("  WARNING: " + s)
    for s in errs:
        print("  ERROR: " + s)
    if show_map and not errs:
        print_map(nodes, order, graph)
    print("  " + ("OK" if not errs else f"{len(errs)} error(s)"))
    return not errs


def print_map(nodes, order, graph):
    """One grid per layer, north up. '--' / '|' are edges, '==' / '‖' locked edges."""
    for y in sorted({n["pos"][1] for n in nodes.values()}, reverse=True):
        layer = {n["pos"][0::2]: nid for nid, n in nodes.items() if n["pos"][1] == y}
        xs = [p[0] for p in layer]
        zs = [p[1] for p in layer]
        print(f"  layer y={y}")
        for z in range(max(zs), min(zs) - 1, -1):
            row, below = "    ", "    "
            for x in range(min(xs), max(xs) + 1):
                nid = layer.get((x, z))
                if nid is None:
                    row += " " * 12
                    below += " " * 12
                    continue
                vert = "".join("^" if nodes[o]["pos"][1] > y else "v"
                               for o, _ in graph[nid] if nodes[o]["pos"][1] != y)
                label = f"{nid}:{nodes[nid]['cell'][4:]}{vert}"
                east = next((k for o, k in graph[nid] if nodes[o]["pos"] == (x + 1, y, z)), 0)
                south = next((k for o, k in graph[nid] if nodes[o]["pos"] == (x, y, z - 1)), 0)
                row += label.ljust(9) + ("   " if east == 0 else ("-- " if east is None else "== "))
                below += ("" if south == 0 else ("|" if south is None else "‖")).ljust(12)
            print(row.rstrip())
            if below.strip():
                print(below.rstrip())


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    good = all([check(p, "--map" in sys.argv) for p in args])
    sys.exit(0 if good else 1)
