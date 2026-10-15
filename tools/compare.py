#!/usr/bin/env python3
"""Compare wowforevermap.com's subzones against the game client, chunk by chunk.

Rasterizes the site's polygons onto the terrain chunk grid and checks each
chunk against the area ID the game files store for it. Writes a Markdown
report, plus a diff image per continent if Pillow is installed.

    python compare.py
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from borders import rasterize

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def game_grid(continent_data):
    grid = {}
    for key, areas in continent_data["tiles"].items():
        tx, ty = map(int, key.split("_"))
        for i, area in enumerate(areas):
            grid[(ty * 16 + i // 16, tx * 16 + i % 16)] = area
    return grid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=DATA / "subzones.json")
    parser.add_argument("--game", type=Path, default=DATA / "game_areas.json")
    parser.add_argument("--out", type=Path, default=DATA / "comparison.md")
    args = parser.parse_args()

    site = json.loads(args.site.read_text(encoding="utf-8"))
    game = json.loads(args.game.read_text(encoding="utf-8"))
    names = {int(s["areaId"]): s["name"] for s in site}

    def name(area):
        return f"{names[area]} ({area})" if area in names else f"#{area}"

    report = [
        "# Subzone data: wowforevermap.com vs game client",
        "",
        f"Game build {game['build']}. Every terrain chunk (33⅓ yd square) the site marks as a subzone",
        "is checked against the area ID stored in that chunk's header in the game's terrain files.",
        "",
    ]
    totals = Counter()
    images = []
    for continent, cdata in sorted(game["continents"].items(), key=lambda kv: int(kv[0])):
        cid = int(continent)
        grid = game_grid(cdata)
        site_cells = {}
        for s in site:
            if int(s["mapId"]) == cid:
                for cell in rasterize(s["rings"]):
                    site_cells[cell] = int(s["areaId"])

        match = mismatch = missing_terrain = 0
        wrong = Counter()
        for cell, area in site_cells.items():
            g = grid.get(cell)
            if g is None:
                missing_terrain += 1
            elif g == area:
                match += 1
            else:
                mismatch += 1
                wrong[(area, g)] += 1
        checked = match + mismatch
        totals.update(match=match, mismatch=mismatch, checked=checked)

        site_areas = {int(s["areaId"]) for s in site if int(s["mapId"]) == cid}
        game_counts = Counter(grid.values())
        # Areas the game uses that the site never draws: zone-level areas
        # (the "rest of the zone") and any subzones the site doesn't have.
        not_on_site = [(a, n) for a, n in game_counts.most_common() if a and a not in site_areas]
        not_in_game = sorted(site_areas - set(game_counts))

        report += [
            f"## Continent {cid}",
            "",
            f"- Terrain tiles: {len(cdata['tiles'])} ({len(grid):,} chunks, {len(game_counts)} distinct area IDs)",
            f"- Site subzone chunks checked: **{checked:,}**",
            f"- Matching: **{match:,} ({match / checked:.2%})**" if checked else "- Matching: n/a",
            f"- Different area in game: {mismatch:,}",
        ]
        if missing_terrain:
            report.append(f"- Site chunks with no terrain in this build: {missing_terrain:,}")
        if wrong:
            report += ["", "Largest disagreements (site area → game area: chunks):", ""]
            for (s_area, g_area), n in wrong.most_common(15):
                report.append(f"- {name(s_area)} → {name(g_area)}: {n}")
        if not_in_game:
            report += ["", "Site subzones not present in the game's terrain: "
                       + ", ".join(name(a) for a in not_in_game)]
        report += ["", f"Game areas the site doesn't draw ({len(not_on_site)}; mostly zone-level areas,"
                   " i.e. parts of a zone that belong to no subzone): "
                   + ", ".join(f"{name(a)}×{n}" for a, n in not_on_site[:40])
                   + (" …" if len(not_on_site) > 40 else ""), ""]

        try:
            from PIL import Image
        except ImportError:
            continue
        rows = [r for r, _ in grid]
        cols = [c for _, c in grid]
        r0, c0 = min(rows), min(cols)
        img = Image.new("RGB", (max(cols) - c0 + 1, max(rows) - r0 + 1), (24, 24, 30))
        px = img.load()
        for (r, c), area in grid.items():
            px[c - c0, r - r0] = (60, 60, 70) if area else (30, 30, 36)
        for (r, c), area in site_cells.items():
            if (r, c) not in grid:
                continue
            px[c - c0, r - r0] = (90, 170, 110) if grid[(r, c)] == area else (230, 60, 60)
        img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
        path = args.out.with_name(f"comparison_{cid}.png")
        img.save(path)
        images.append(path.name)

    checked = totals["checked"]
    summary = [
        "## Overall",
        "",
        f"**{totals['match']:,} of {checked:,} subzone chunks match ({totals['match'] / checked:.2%}).**",
        "",
    ]
    if images:
        summary += ["Diff images (green = match, red = different, gray = terrain the site leaves unassigned): "
                    + ", ".join(images), ""]
    report[5:5] = summary
    args.out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(summary), file=sys.stderr)
    print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
