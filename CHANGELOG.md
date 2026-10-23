# Changelog

All notable changes to SubZones-WoW-Forever. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- CurseForge / Wago listing copy in `listing/`, and logos and a banner in `art/`.
- `Author` and `X-Website` fields in the TOC.
- `tools/package.py` and the packaged `release/SUBZONES-1.0.0.zip`.
- `tools/install_beta.cmd`: pulls from GitHub and installs the addon into the beta client, stamping the commit into `Build.lua`.
- `/subzones debug` shows the addon version and installed build.

### Changed

- Licensed under GPLv3 (`LICENSE`, also packed into the release zip).
- The repository is public. SECURITY.md describes the release zips.

## [1.0.0] - 2026-10-15

### Added

- SUBZONES addon for WoW Forever (TOC 16001). It draws subzone borders and names on the world map, with optional color fills (styles: Lines only, Lines + tint, Tint only).
- Subzone borders on the minimap for your current zone. They're clipped to round or square minimaps and turn with Rotate Minimap.
- Options panel under Settings → AddOns → SUBZONES, a right-click menu on the world map's **Subzones** checkbox, and `/subzones` (`/sz`) commands.
- Border data extracted from the game's own terrain files (per-chunk area IDs), covering Eastern Kingdoms, Kalimdor and Zephras Isle.
- Data tools: a CASC reader with Blizzard CDN fallback (`casc.py`), terrain extraction (`extract_game.py`), border generation (`build_borders.py`) and a comparison against wowforevermap.com (`compare.py`). The comparison shows 99.95% of chunks match.
- Standard docs: README, CLAUDE, CHANGELOG, DEPLOY and SECURITY.

### Fixed

- The world map froze and the client crashed when opening continent maps. Subzones are now drawn only on zone-level maps, with a per-map safety cap.
- Kalimdor and Eastern Kingdoms zones showed no subzones. Map ownership now uses the continent map's own hover lookup.
