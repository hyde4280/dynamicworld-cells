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

Usage: check_def.py defs/mine01.txt [--map]      (exit status 1 on errors)
"""
import os
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


def cell_manifest(cell):
    """doors {face: kind}, counts of switch / spawn lines, save flag; None if missing."""
    path = os.path.join(CELLS, cell + ".obj")
    if not os.path.exists(path):
        return None
    info = {"doors": {}, "switch": 0, "spawn": 0, "save": False}
    for line in open(path, encoding="utf-8"):
        if not line.startswith("#"):
            if line.startswith("v "):
                break
            continue
        if line.startswith("# door:"):
            p = [x.strip() for x in line.split(":", 1)[1].split(",")]
            info["doors"][p[0]] = p[1].lower() if len(p) > 1 else ("hatch" if p[0] in "UD" else "")
        elif line.startswith("# switch:"):
            info["switch"] += 1
        elif line.startswith("# spawn:"):
            info["spawn"] += 1
        elif line.startswith("# cell.save:"):
            info["save"] = line.split(":", 1)[1].strip().startswith("1")
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
