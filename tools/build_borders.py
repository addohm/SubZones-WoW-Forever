#!/usr/bin/env python3
"""Generate SUBZONES/SubzoneBorders.lua from the game's terrain (or the site's data).

    python build_borders.py                  # from tools/data/game_areas.json (extract_game.py)
    python build_borders.py --source site    # from tools/data/subzones.json (wowforevermap.com)
    python build_borders.py --raw            # keep the exact chunk staircase

Game data includes every area: subzones, zone-level areas and seas. The addon
works out in-game which of them are subzones of the map being viewed.
Names come from the client in-game; the site's names are kept as a fallback.
"""

import argparse
import json
import sys
from pathlib import Path

from borders import build_continent, rasterize, write_lua
from compare import game_grid

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DEFAULT_OUT = ROOT.parent / "SUBZONES" / "SubzoneBorders.lua"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=("game", "site"), default="game")
    parser.add_argument("--game", type=Path, default=DATA / "game_areas.json")
    parser.add_argument("--site", type=Path, default=DATA / "subzones.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--raw", action="store_true", help="no smoothing")
    args = parser.parse_args()

    site = json.loads(args.site.read_text(encoding="utf-8")) if args.site.exists() else []
    names = {int(s["areaId"]): s["name"] for s in site}

    continents = {}
    if args.source == "game":
        game = json.loads(args.game.read_text(encoding="utf-8"))
        source = f"game client {game['build']} terrain"
        for cid, cdata in game["continents"].items():
            continents[int(cid)] = build_continent(game_grid(cdata), raw=args.raw)
    else:
        source = "wowforevermap.com subzones.json"
        grids, labels = {}, {}
        for s in site:
            grid = grids.setdefault(int(s["mapId"]), {})
            for cell in rasterize(s["rings"]):
                grid[cell] = int(s["areaId"])
            labels.setdefault(int(s["mapId"]), {})[int(s["areaId"])] = tuple(s["label"])
        for cid, grid in grids.items():
            continents[cid] = build_continent(grid, labels[cid], raw=args.raw)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_lua(args.out, source, continents, names)
    for cid, data in sorted(continents.items()):
        points = sum(len(p) for _, _, p in data["lines"])
        print(f"continent {cid}: {len(data['areas'])} areas, {len(data['lines'])} lines, {points} points",
              file=sys.stderr)
    print(f"wrote {args.out} ({args.out.stat().st_size // 1024} KB) from {source}", file=sys.stderr)


if __name__ == "__main__":
    main()
