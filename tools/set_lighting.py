#!/usr/bin/env python3
"""Set the dark-mine lighting lines in the header of an existing cell OBJ whose
generator is not in this repository (cell010 / cell011, 2026-11-16).

Rewrites `# cell.baselight:` and `# cell.fog:` in place (inserted before the first
`# door:` line when absent); nothing else in the file changes.

Usage: set_lighting.py cells/cell010.obj <baselight> <fog start> <fog end>
"""
import sys


def main():
    path, base, f0, f1 = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    lines = open(path).read().split("\n")
    lines = [ln for ln in lines if not ln.startswith(("# cell.baselight:", "# cell.fog:"))]
    k = next(i for i, ln in enumerate(lines) if ln.startswith("# door:"))
    lines[k:k] = [f"# cell.baselight: {base}", f"# cell.fog: {f0}, {f1}"]
    open(path, "w").write("\n".join(lines))


if __name__ == "__main__":
    main()
