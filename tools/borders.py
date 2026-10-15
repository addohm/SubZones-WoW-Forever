"""Shared geometry: per-chunk area grids -> smoothed border polylines -> Lua.

A grid maps (row, col) chunk cells to area IDs. Rows run north to south and
columns west to east across a whole continent (64 tiles x 16 chunks), the same
layout as the terrain files:

    worldX = (512 - row) * CHUNK      (north edge of the cell)
    worldY = (512 - col) * CHUNK      (west edge of the cell)
"""

import math
from collections import defaultdict, deque

CHUNK = 100 / 3  # yards per terrain chunk (533 1/3-yard tile / 16)
GRID = 64 * 16


def cell_center(row, col):
    return (512 - row - 0.5) * CHUNK, (512 - col - 0.5) * CHUNK


def world_to_cell(x, y):
    return int(512 - x / CHUNK), int(512 - y / CHUNK)


# --- Rasterizing polygons (wowforevermap.com format) onto the chunk grid ------

def rasterize(rings):
    """Cells whose centers fall inside the rings (even-odd, so holes work)."""
    cells = set()
    edges = []
    for ring in rings:
        pts = [(512 - x / CHUNK, 512 - y / CHUNK) for x, y in ring]  # (row, col), fractional
        if pts[0] != pts[-1]:
            pts.append(pts[0])
        edges += list(zip(pts, pts[1:]))
    rows = [p[0] for e in edges for p in e]
    for row in range(int(math.floor(min(rows))), int(math.ceil(max(rows)))):
        r = row + 0.5
        xs = sorted(c0 + (c1 - c0) * (r - r0) / (r1 - r0)
                    for (r0, c0), (r1, c1) in edges if (r0 <= r) != (r1 <= r))
        for a, b in zip(xs[0::2], xs[1::2]):
            for col in range(int(math.ceil(a - 0.5)), int(math.floor(b - 0.5)) + 1):
                cells.add((row, col))
    return cells


# --- Labels -------------------------------------------------------------------

def label_cells(grid):
    """Per area, the cell deepest inside it (farthest from any other area)."""
    depth = {}
    queue = deque()
    for (r, c), a in grid.items():
        if any(grid.get(n, 0) != a for n in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))):
            depth[(r, c)] = 0
            queue.append((r, c))
    while queue:
        r, c = queue.popleft()
        a = grid[(r, c)]
        for n in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if n in grid and n not in depth and grid[n] == a:
                depth[n] = depth[(r, c)] + 1
                queue.append(n)
    best = {}
    for cell, d in depth.items():
        a = grid[cell]
        if a not in best or d > best[a][0] or (d == best[a][0] and cell < best[a][1]):
            best[a] = (d, cell)
    return {a: cell for a, (_, cell) in best.items()}


# --- Borders --------------------------------------------------------------------

def grid_edges(grid):
    """Unit edges between differing cells, keyed by (low, high) area pair.

    Vertices are grid points (row, col). Missing cells count as area 0.
    """
    pairs = defaultdict(list)

    def add(a, b, edge):
        if a != b:
            pairs[(min(a, b), max(a, b))].append(edge)

    for (r, c), a in grid.items():
        add(a, grid.get((r, c + 1), 0), ((r, c + 1), (r + 1, c + 1)))  # east side
        add(a, grid.get((r + 1, c), 0), ((r + 1, c), (r + 1, c + 1)))  # south side
        if (r, c - 1) not in grid:
            add(a, 0, ((r, c), (r + 1, c)))  # west side, facing nothing
        if (r - 1, c) not in grid:
            add(a, 0, ((r, c), (r, c + 1)))  # north side, facing nothing
    return pairs


def chain(edges):
    """Joins edges into polylines, breaking at junctions (degree != 2)."""
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    used = set()

    def key(a, b):
        return (a, b) if a < b else (b, a)

    paths = []
    for start in [v for v in adj if len(adj[v]) != 2] + list(adj):
        for nxt in adj[start]:
            if key(start, nxt) in used:
                continue
            used.add(key(start, nxt))
            path, prev, cur = [start, nxt], start, nxt
            while len(adj[cur]) == 2:
                step = adj[cur][0] if adj[cur][0] != prev else adj[cur][1]
                if key(cur, step) in used:
                    break
                used.add(key(cur, step))
                path.append(step)
                prev, cur = cur, step
            paths.append(path)
    return paths


def simplify(points, eps):
    """Douglas-Peucker, iterative."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        (x1, y1), (x2, y2) = points[i], points[j]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        best, best_k = 0.0, None
        for k in range(i + 1, j):
            px, py = points[k]
            d = (abs(dy * px - dx * py + x2 * y1 - y2 * x1) / length) if length else math.hypot(px - x1, py - y1)
            if d > best:
                best, best_k = d, k
        if best_k is not None and best > eps:
            keep[best_k] = True
            stack += [(i, best_k), (best_k, j)]
    return [p for p, k in zip(points, keep) if k]


def chaikin(points, max_cut):
    """Corner cutting capped at max_cut; endpoints stay put so junctions still meet."""
    if len(points) < 3:
        return points
    out = [points[0]]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        t = min(0.25, max_cut / length) if length else 0
        out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        out.append((x1 - (x1 - x0) * t, y1 - (y1 - y0) * t))
    out.append(points[-1])
    return out


def smooth(points):
    """Single-chunk staircases collapse to diagonals, then corners round off."""
    if points[0] == points[-1] and len(points) > 4:
        # Split closed loops at their farthest point so DP has two real anchors.
        far = max(range(len(points) - 1),
                  key=lambda i: math.hypot(points[i][0] - points[0][0], points[i][1] - points[0][1]))
        points = simplify(points[:far + 1], 0.6) + simplify(points[far:], 0.6)[1:]
    else:
        points = simplify(points, 0.6)
    for _ in range(2):
        points = chaikin(points, 0.35)
    return simplify(points, 0.04)


def grid_lines(grid, raw=False):
    """[(areaA, areaB, [(worldX, worldY), ...]), ...] for every border in the grid."""
    lines = []
    for (a, b), edges in sorted(grid_edges(grid).items()):
        for path in chain(edges):
            points = [(float(r), float(c)) for r, c in path]
            points = simplify(points, 0.01) if raw else smooth(points)
            lines.append((a, b, [((512 - r) * CHUNK, (512 - c) * CHUNK) for r, c in points]))
    return lines


# --- Lua output -------------------------------------------------------------------

def lua_num(v):
    text = f"{v:.1f}"
    return text[:-2] if text.endswith(".0") else text


def lua_string(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_lua(path, source, continents, names):
    """continents: {continentID: {"areas": {areaID: (labelX, labelY, cells)}, "lines": [...]}}"""
    out = [
        "-- Generated by tools/. Do not edit by hand.",
        f"-- Source: {source}",
        "-- World coordinates (worldX, worldY); the addon projects them onto each map in-game.",
        "SubzoneBorders = { source = " + lua_string(source) + ", continents = {} }",
        "-- names[areaID]: fallback when the client can't name an area",
        "SubzoneBorders.names = {",
    ]
    for area_id in sorted(names):
        out.append(f"\t[{area_id}] = {lua_string(names[area_id])},")
    out.append("}")
    for continent in sorted(continents):
        data = continents[continent]
        out.append("do")
        out.append("\tlocal c = { areas = {}, lines = {} }")
        out.append(f"\tSubzoneBorders.continents[{continent}] = c")
        out.append("\t-- areas[areaID] = { labelX, labelY, chunkCount }")
        out.append("\tc.areas = {")
        for area_id in sorted(data["areas"]):
            x, y, cells = data["areas"][area_id]
            out.append(f"\t\t[{area_id}] = {{{lua_num(x)},{lua_num(y)},{cells}}},")
        out.append("\t}")
        out.append("\t-- lines[i] = { areaA, areaB (0 = none), x1, y1, x2, y2, ... }")
        out.append("\tc.lines = {")
        for a, b, points in data["lines"]:
            coords = ",".join(f"{lua_num(x)},{lua_num(y)}" for x, y in points)
            out.append(f"\t\t{{{a},{b},{coords}}},")
        out.append("\t}")
        out.append("end")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def build_continent(grid, labels=None, raw=False):
    """Areas (label point, chunk count) and border lines for one continent's grid."""
    counts = defaultdict(int)
    for area in grid.values():
        counts[area] += 1
    areas = {}
    for area, (r, c) in label_cells(grid).items():
        if area:
            x, y = (labels or {}).get(area) or cell_center(r, c)
            areas[area] = (x, y, counts[area])
    return {"areas": areas, "lines": grid_lines(grid, raw)}
