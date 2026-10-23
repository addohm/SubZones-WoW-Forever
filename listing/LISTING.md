# SUBZONES: CurseForge and Wago listing

Copy-paste material for the project pages. Placeholders are in [brackets].

---

## Basics

| Field | Value |
| --- | --- |
| Name | SUBZONES |
| Slug | `subzones` (fallback `subzones-forever`) |
| Game version | WoW: Forever (Interface 16001, client 1.60.1) |
| Author | addohm |
| License | [choose: All Rights Reserved, MIT, ...] |
| Source | https://github.com/addohm/SubZones-WoW-Forever |
| Issues | https://github.com/addohm/SubZones-WoW-Forever/issues |
| Logo | `subzones-logo-400.png`, `subzones-logo-1024.png`, `subzones-logo-round-1024.png` (transparent) in this folder |

**Categories**
- CurseForge: Map & Minimap (main), Quests & Leveling
- Wago: [the map/minimap category (main)], [the leveling category]

**Summary** (the one-liner under the name; 105 characters)

> See every subzone on your map: borders, names and optional color tints, straight from the game's
> terrain.

**Short tagline** (for images or a Discord post)

> Know exactly where Goldshire ends.

---

## Description

*(Paste as Markdown. Both sites accept it.)*

### SUBZONES

**Subzone borders and names on your world map and minimap, built for WoW: Forever.**

The world map shows you a zone, but not where its subzones begin and end. SUBZONES draws them: clean
outlines, names, and optional color tints, on the world map and around you on the minimap.

The borders aren't hand-drawn or guessed. They come from the game's own terrain files, the same data
the client uses to decide which subzone you're standing in. When you cross a SUBZONES line, your
subzone changes.

#### On the world map

- Smoothed outlines for every subzone of the zone you're viewing.
- Names at the center of each subzone. Ones you haven't explored yet show in grey, or you can hide
  them.
- Three styles: **Lines only** (default), **Lines + tint**, or **Tint only**, with neighbouring
  subzones always in clearly different colors.
- A **Subzones** checkbox at the bottom-left of the map turns it on and off. Right-click it for the
  style, names and options.

#### On the minimap

- Your current zone's subzone borders, drawn around you as you move.
- Clipped to round or square minimaps, and turning with **Rotate Minimap**.
- It only redraws when you move, turn or zoom.

#### Accurate by design

WoW has no subzone shapes. Instead, the world is a grid of 33-yard terrain chunks, and each chunk is
tagged with one area. SUBZONES reads that grid from the client, traces the edges between areas and
smooths the 33-yard staircase into curves. The result matches **99.95%** of the subzone chunks
published by wowforevermap.com; the only differences are where Forever itself changed the map
(Dalaran and Windstead).

#### Settings

- Show subzones, style, subzone names, unexplored subzones, show on minimap, line width and tint
  opacity.
- In **Settings → AddOns → SUBZONES**, the right-click menu on the map checkbox, or by command.

#### Commands

- `/subzones`: turn the overlay on or off. `/subzones options`: the settings panel.
- `/subzones lines`, `both`, `tint`, `labels`, `unexplored`, `minimap`, `alpha <0-1>`, `width <px>`,
  `blend`, `debug`
- `/sz` works too.

#### Good to know

- Covers Eastern Kingdoms, Kalimdor and Zephras Isle.
- Draws on zone maps only, never whole continents, to keep the map fast.
- Settings stay on your computer in the game's own saved data. No network access, no libraries.
- **Found a border in the wrong place?** Open an issue on GitHub with a screenshot and the output of
  `/subzones debug`.

---

## Screenshots to take

1. **Hero:** Elwynn Forest world map, Lines + tint, names on.
2. Lines only on a busy zone (Stranglethorn or Ashenvale).
3. The minimap while standing on a border, round, with Rotate Minimap on.
4. A partly explored zone: grey names next to gold ones.
5. Tint only on a zone with many small subzones.
6. The Settings panel.
7. The right-click menu on the map's **Subzones** checkbox.

Tips: use a clean UI (hide other addons), 16:9 at 1920×1080, crop to the subject, and scale the UI
so the names are readable.

---

## Release notes for 1.0.0

> First release, for WoW: Forever.
>
> - Subzone borders and names on the world map, in Lines, Lines + tint or Tint styles
> - Subzone borders on the minimap, clipped to its shape and turning with it
> - Unexplored subzones in grey (optional)
> - Settings panel, right-click map menu and `/subzones` (`/sz`) commands
> - Covers Eastern Kingdoms, Kalimdor and Zephras Isle

---

## Before publishing

- Choose a license and add a matching `LICENSE` file to the repo.
- Move the CHANGELOG's Unreleased entries under the version, bump `## Version` in `SUBZONES.toc` if
  needed, and rebuild the zip with `python tools/package.py` (see DEPLOY.md). Upload
  `release/SUBZONES-<version>.zip`.
- Add the project IDs to the `.toc` (`## X-Curse-Project-ID`, `## X-Wago-ID`) once the projects
  exist, then rebuild the zip.
- Check that both upload forms offer WoW: Forever (16001) as a game version, and pick Wago's
  category names from its dropdown.
- Cut the wowforevermap.com sentence if you'd rather not name another project.
- Project icon: `subzones-logo-400.png` from this folder.
