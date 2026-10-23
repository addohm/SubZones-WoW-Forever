# SUBZONES — CurseForge / Wago pitch sheet

Paste-ready copy for both listings, plus what still needs doing before upload. The logos are in this folder.

---

## Listing basics

| Field | Value |
| --- | --- |
| Project name | SUBZONES — Subzone Borders & Names |
| Author | addohm |
| Slug | `subzones` (fallback `subzones-forever`) |
| Category | Map & Minimap |
| Game version | WoW Forever, interface **16001** |
| Version | 1.0.0 |
| License | *pick one; the repo has no LICENSE yet* |
| Source | https://github.com/addohm/SubZones-WoW-Forever |
| Issues | https://github.com/addohm/SubZones-WoW-Forever/issues |
| Logo | `subzones-logo-400.png` (CurseForge), `subzones-logo-1024.png`; `subzones-logo-round-1024.png` has a transparent background |

**Summary** (one line, under 100 characters):

> See every subzone on your map: borders, names and optional color tints, straight from the game's terrain.

**Alternates:**

- Subzone borders and names on the world map and minimap, from WoW Forever's own terrain data.
- Know exactly where Goldshire ends: subzone outlines on your world map and minimap.

**Keywords / tags:** subzones, map, minimap, borders, world map, exploration, zones, overlay, WoW Forever, leveling

---

## Description (Markdown; works on both sites)

```markdown
# SUBZONES

**See where every subzone begins and ends.** SUBZONES draws subzone borders and names on your world map and minimap, with optional color tints, for **WoW Forever**.

The borders aren't hand-drawn or guessed. They come from the game's own terrain files, the same data the client uses to decide which subzone you're standing in. When you cross a SUBZONES line, your subzone changes.

## Features

- **World map borders:** clean, smoothed outlines for every subzone in the zone you're viewing.
- **Subzone names:** labels at the center of each area. Unexplored subzones show in grey, or you can hide them.
- **Three styles:** Lines only (default), Lines + tint, or Tint only, with each subzone in its own color.
- **Minimap overlay:** your current zone's borders drawn around you, clipped to round or square minimaps, and turning with Rotate Minimap.
- **Light on resources:** it only draws zone maps, never whole continents, and the minimap only redraws when you move, turn or zoom.
- **Easy to control:** a **Subzones** checkbox on the world map (right-click it for options), a full Settings panel, and slash commands.

## Coverage

Eastern Kingdoms, Kalimdor and Zephras Isle.

## How to use

- Tick **Subzones** at the bottom-left of the world map. Right-click it for the style, names, unexplored subzones and **Options…**
- **Settings → AddOns → SUBZONES** for line width, tint opacity and the minimap toggle.
- `/subzones` (or `/sz`): `toggle`, `options`, `lines`, `both`, `tint`, `labels`, `unexplored`, `minimap`, `alpha <0-1>`, `width <px>`, `blend`, `debug`

## Why it's accurate

WoW has no subzone shapes. Instead, the world is a grid of 33-yard terrain chunks, and each chunk is tagged with one area. SUBZONES reads that grid from the client, traces the edges between areas, and smooths the 33-yard staircase into curves. The result matches **99.95%** of the subzone chunks published by wowforevermap.com, and the only differences are where Forever itself changed the map (Dalaran and Windstead).

## Feedback

Found a border in the wrong place or a missing name? Open an issue on GitHub with a screenshot and the output of `/subzones debug`.
```

---

## Screenshots to take (in this order)

1. **Hero shot:** Elwynn Forest world map, Lines + tint, names on. It's the area most people know, and it reads well at thumbnail size.
2. **Lines only:** a busy zone (Stranglethorn or Ashenvale) showing the default style.
3. **Minimap:** standing on a border, with a round minimap and Rotate Minimap on if possible.
4. **Unexplored:** a partly explored zone with grey names next to gold ones.
5. **Settings panel** and the right-click menu on the map checkbox.
6. *(Optional)* Before/after GIF of the checkbox being ticked.

Shoot at 1920×1080 or higher with the UI scaled so the labels are readable.

---

## First release notes

```markdown
## 1.0.0

First public release.

- Subzone borders and names on the world map, with Lines / Lines + tint / Tint styles.
- Subzone borders on the minimap, clipped to its shape and rotating with it.
- Unexplored subzones shown in grey (optional).
- Settings panel, right-click map menu and /subzones (/sz) commands.
- Covers Eastern Kingdoms, Kalimdor and Zephras Isle.
```

---

## Before you upload

- **License:** CurseForge makes you pick one. MIT or All Rights Reserved are the usual choices. Add a matching `LICENSE` file to the repo.
- **TOC fields:** `## Author` and `## X-Website` are set. Add `## X-Curse-Project-ID:` and `## X-Wago-ID:` once the projects exist (the IDs let addon managers and packagers link them).
- **Zip:** upload `release/SUBZONES-<version>.zip`, built by `python tools/package.py`. It must contain a top-level `SUBZONES/` folder with only `SUBZONES.toc`, `SUBZONES.lua` and `SubzoneBorders.lua`, not `tools/` or `listing/`.
- **Forever flavor:** confirm the upload form offers WoW Forever / 16001 as a game version. Third-party guides say Forever builds are tagged on both sites, but I couldn't find official docs for it. Wago's API docs only list retail/classic patch fields.
- **wowforevermap.com mention:** the 99.95% line names their site. It's a fair comparison, but cut the sentence if you'd rather not reference another project.
- **Timing:** Forever launches **Nov 4, 2026**. Listing before launch catches people building their UI.
