# SUBZONES

WoW addon for **WoW Forever** (client "Camelot", product `wow_classic_beta`, TOC `16001`, modern Midnight-style API) that draws subzone borders, names and optional color fills on the world map and minimap. Borders come from the game's own terrain files, extracted offline by the Python tools. See `README.md` for user-facing docs.

## Layout

- `SUBZONES/`: the addon, which is what gets installed.
  - `SUBZONES.lua`: all runtime code.
  - `SubzoneBorders.lua`: generated data (~750 KB). Never hand-edit it; regenerate with `tools/build_borders.py`.
  - `Build.lua`: `ns.Build = nil` in the repo; `install_beta.cmd` stamps the installed copy with the commit hash, shown by `/subzones debug`.
  - `SUBZONES.toc`
- `tools/`: offline data pipeline (Python 3, standard library except where noted). Needed to regenerate border data after game patches; not needed to run the addon.
  - `casc.py`: read-only CASC reader for the local install, with Blizzard CDN fallback.
  - `extract_game.py`: WDT/ADT → per-chunk area IDs → `data/game_areas.json`.
  - `borders.py`: shared geometry: grid → border polylines → smoothing → Lua writer.
  - `build_borders.py`: `game_areas.json` (or `--source site`) → `SUBZONES/SubzoneBorders.lua`.
  - `install_beta.cmd`: Windows; pulls from GitHub and mirrors `SUBZONES/` into the beta client's AddOns folder, stamping `Build.lua`. CRLF line endings (`.gitattributes`).
  - `package.py`: `SUBZONES/` → `release/SUBZONES-<version>.zip` (TOC + the files it loads).
  - `compare.py`: wowforevermap.com `subzones.json` vs game, chunk by chunk → `data/comparison.md` + PNGs (needs Pillow).
  - `data/`: extraction output, the site's JSON, comparison report.
  - `cache/`: CDN downloads (~65 MB, safe to delete; refetched on demand).
- `release/`: packaged zips for CurseForge / Wago, committed. Rebuild with `python tools/package.py` after a version bump.
- `listing/`: CurseForge / Wago listing copy (`LISTING.md`). Not part of the addon zip; keep the copy in step with features.
- `art/`: logos (1024 and 400 px squares, plus a round one with a transparent background). Not part of the addon zip.

## Workflow

- **After every addon change**, commit and push; the user runs `tools\install_beta.cmd`, which pulls and mirrors `SUBZONES/` into `C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns\SUBZONES` (skipping zips), then `/reload`s. `/subzones debug` shows the installed build.
- **After a game patch:** `python tools/extract_game.py` (first run ~6 min) then `python tools/build_borders.py`, then install as above.
- **Testing:** there's no in-game test runner. Verify Lua by loading it in LuaJIT (`pip install lupa` in a throwaway venv, never system Python) against stubbed WoW APIs, then render the recorded lines/quads/labels with Pillow and look at the image. Keep harnesses in the scratchpad, not the project. State plainly that stub tests can't prove client behaviour; the user tests in-game and reports `/subzones debug` output.
- Error and crash logs live in `...\_classic_beta_\Errors\`. Lua errors come via BugSack. Other addons (MapUtils, EllesmereUI, …) produce their own errors; check the stack before assuming it's ours.

## Data model

- Terrain: each ADT tile is 533⅓ yd = 16×16 chunks of 33⅓ yd. The MCNK header's area ID is at `+0x34`, and its IndexX/IndexY are at `+4`/`+8`.
- Continent grid: `row = tileY*16 + IndexY`, `col = tileX*16 + IndexX` (MAID index `i`: `tileX = i % 64`, `tileY = i // 64`).
- World coordinates: `worldX = (512 - row) * CHUNK` (north is +), `worldY = (512 - col) * CHUNK` (west is +).
- `SubzoneBorders.continents[continentID]` holds `areas[areaID] = {labelX, labelY, chunkCount}` (every area: subzones, zone-level areas, seas) and `lines[i] = {areaA, areaB (0 = none), x1, y1, ...}` in world coordinates. `names` is a fallback from the site.
- Known continent WDTs: 0 → 775971, 1 → 782779; 2991 (Zephras Isle) → 7198644 is auto-matched. 8 WDTs are encrypted (no keyring shipped). `AreaTable`/`Map` DB2 are encrypted too, so names and parents can only be read in-game.

## Runtime rules learned the hard way

- `C_Map.GetWorldPosFromMapPos` vectors are `(worldX, worldY)`, the same order as the data. Don't "auto-detect" axis order; a density heuristic picked the wrong order once.
- On Kalimdor and the Eastern Kingdoms, `C_Map.GetMapPosFromWorldPos` returns the **continent** map, not the zone. Map ownership therefore uses the parent continent's `C_Map.GetMapInfoAtPosition` (plus a check that no child city map is at the point). `GetMapPosFromWorldPos` is only a fallback (Zephras Isle has no continent map).
- Never draw on continent or world maps (`mapType < Zone`). Drawing a whole continent's borders froze and crashed the client. Keep the `MAX_SUBZONES_PER_MAP` cap.
- The zone-level area is dropped by name match with the map name, or else by being more than 35% of the map's chunks.
- `Blizzard_MapCanvas` is load-on-demand: no XML templates inheriting `MapCanvasPinTemplate`, and touch `MapCanvasDataProviderMixin` only in `Install()`.
- The world-map overlay is a plain frame on `WorldMapFrame:GetCanvas()` plus a data provider. Fills are `SetColorTexture` quads shaped with `SetVertexOffset` (trapezoid decomposition).
- Lua 5.1: a multi-return call that isn't the last argument is truncated to one value (`f(g(), 0)`).

## Conventions

- Lua: tabs, `local` everything, comments explain *why*. Globals only for `SubzonesDB`, `SubzonesMapToggle`, slash and settings registration.
- Python: 4-space indent, stdlib-first, small functions, a module docstring with usage.
- Settings go in `DEFAULTS` and are exposed in the Settings panel (`RegisterSettings`), the right-click map menu and `/subzones` (alias `/sz`). New options need all three.
- Defaults: style `lines` (tint is opt-in), minimap on.
- The user prefers concise updates. Bump the TOC `## Version` on notable changes.

## Git

GitHub: `addohm/SubZones-WoW-Forever` (public, GPLv3 in `LICENSE`), branch `main`. Everything committed is world-readable: no local paths, hostnames or private notes. `.gitignore` covers the global secret patterns, `tools/cache/`, `tools/data/subzones.json` (wowforevermap.com's data; never commit it) and `*.zip` except `release/*.zip`. Record notable changes in CHANGELOG.md, and keep README/DEPLOY in step with them.
