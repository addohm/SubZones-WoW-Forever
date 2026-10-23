# Deploying SubZones-WoW-Forever

SUBZONES is a client-side WoW addon. There's no server: "deploying" means copying the addon folder into the game's AddOns folder.

## First-time setup

1. Clone the repo and run `tools\install_beta.cmd` (double-click works). It pulls from GitHub and mirrors `SUBZONES/` into the beta client's AddOns folder:

   ```
   C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns\SUBZONES
   ```

   Edit `ADDON` at the top of the script if your client is installed elsewhere. Without the script, copy the `SUBZONES/` folder there by hand.

2. Start the game (or `/reload`) and make sure **SUBZONES** is enabled in the AddOns list.
3. Check it on a zone map: `/subzones debug` reports the subzone count, data source, version and build (the commit the script installed, or `release` for a zip install).

Only `SUBZONES.toc`, `Build.lua`, `SUBZONES.lua` and `SubzoneBorders.lua` are needed. Everything in `tools/` is for regenerating data.

## Shipping a change

1. Edit `SUBZONES/SUBZONES.lua`. Never hand-edit `SubzoneBorders.lua`; it's generated.
2. Push, run `tools\install_beta.cmd`, `/reload`, and test. The script only installs what's on GitHub.
3. Bump `## Version` in `SUBZONES.toc` and add a CHANGELOG entry.
4. Run `python tools/package.py` to build `release/SUBZONES-<version>.zip`. That zip is what gets uploaded to CurseForge and Wago.
5. Commit and push, including the new zip.

To roll back, check out the previous commit's `SUBZONES/` folder and copy it in again.

## Updating border data after a game patch

Requires Python 3. Pillow is needed only for `compare.py`'s images.

```
python tools/extract_game.py      # reads the installed client; fetches missing files from Blizzard's CDN
python tools/build_borders.py     # writes SUBZONES/SubzoneBorders.lua
```

The first extraction takes about 6 minutes. CDN downloads are cached in `tools/cache/`, which isn't committed. Use `--product` to pick a different install, and `--wdt ID=FDID` for a continent that isn't identified automatically.

To re-run the comparison, first download the site's data to `tools/data/subzones.json` (also not committed):

```
curl -o tools/data/subzones.json https://wowforevermap.com/subzones.json
python tools/compare.py
```

## Configuration

There's nothing to configure for deployment. Player settings are saved by the game in the `SubzonesDB` SavedVariable.
