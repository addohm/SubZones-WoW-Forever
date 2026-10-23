# SUBZONES

A WoW addon for WoW Forever (TOC 16001) that draws subzone borders and names on the world map, with optional color fills. The borders are extracted from the game's own terrain files.

## Using it

- **Map checkbox:** a **Subzones** checkbox at the bottom-left of the world map toggles the overlay. Right-click it for the style, names, unexplored subzones, and **Options…**.
- **Options panel:** Settings → AddOns → **SUBZONES**, or `/subzones options`. It has: show subzones, style (Lines only / Lines + tint / Tint only), subzone names, unexplored subzones, show on minimap, line width, and tint opacity.
- **Commands:** `/subzones` (or `/sz`) followed by `toggle`, `options`, `lines`, `both`, `tint`, `labels`, `unexplored`, `minimap`, `alpha <0-1>`, `width <px>`, `blend` or `debug`.
- **Minimap:** your current zone's subzone borders are drawn around you too. They're clipped to the minimap's round or square edge and turn with it when Rotate Minimap is on. The minimap only redraws when you move, turn or zoom. Turn it off with **Show on minimap**.

## Where the borders come from

The game has no subzone polygons. Instead, every terrain tile (ADT, 533⅓ yd) is a 16×16 grid of chunks, and each chunk header (MCNK) stores one area ID. Your subzone changes exactly when you cross into a chunk with a different area. SUBZONES' data is that grid, read straight from the client:

1. `tools/extract_game.py` reads each continent's tile list (WDT) and every tile's chunk area IDs. It reads your local install first and fetches anything the client hasn't downloaded from Blizzard's CDN, then writes `tools/data/game_areas.json`.
2. `tools/build_borders.py` turns the grid into border lines between differing areas, one line per border. It smooths the 33⅓-yard staircase into curves, keeping the junctions fixed, and writes `SUBZONES/SubzoneBorders.lua`.
3. In-game, SUBZONES projects the lines onto each map with `C_Map.GetWorldPosFromMapPos`. It asks the client which map owns each area (`C_Map.GetMapPosFromWorldPos`), drops the zone-level area, and names subzones with `C_Map.GetAreaInfo`. Fills are built from the same lines, so tint and borders always agree.

### Updating after a game patch

```
pip install pillow numpy        # only needed for compare.py's diff images
python tools/extract_game.py    # reads the installed build; first run ~6 min, cached after
python tools/build_borders.py
```

Then copy `SUBZONES/` into `Interface/AddOns/`. Useful options:
- `extract_game.py --product`: pick a different install, for example `wow_classic`.
- `extract_game.py --wdt ID=FDID`: add a continent that couldn't be identified automatically.
- `build_borders.py --raw`: keep the exact chunk staircase.

### Checking against wowforevermap.com

```
curl -o tools/data/subzones.json https://wowforevermap.com/subzones.json   # the site's data, not committed
python tools/compare.py
```

This compares the site's subzones (`tools/data/subzones.json`) with the game, chunk by chunk, and writes `tools/data/comparison.md` plus diff images. On build 1.60.1.70334, **99.95%** of the site's subzone chunks match the game. All the differences are in two places WoW Forever changed: Dalaran and Windstead. `build_borders.py --source site` can still build from the site's data if you ever want to.

## Tools

| File | Purpose |
| --- | --- |
| `casc.py` | Read-only access to the game's storage (CASC), with Blizzard CDN fallback; standard library only |
| `extract_game.py` | Terrain chunk area IDs → `data/game_areas.json` |
| `build_borders.py` | Area grid → `SUBZONES/SubzoneBorders.lua` |
| `borders.py` | Shared geometry: grid → border lines, smoothing, Lua output |
| `compare.py` | Site vs game report |

Limits: this beta build ships no decryption keys, so the 8 encrypted (unreleased) continents are skipped, and area names are only read in-game. One 16-tile map (fileDataID 790377) isn't matched to a continent ID automatically.

## Docs

- [CHANGELOG.md](CHANGELOG.md): what changed in each version
- [DEPLOY.md](DEPLOY.md): installing, shipping changes, updating data after a patch
- [SECURITY.md](SECURITY.md): reporting problems; no secrets are used
- [listing/LISTING.md](listing/LISTING.md): CurseForge / Wago listing copy and logos
- [CLAUDE.md](CLAUDE.md): orientation for working on the code with Claude
