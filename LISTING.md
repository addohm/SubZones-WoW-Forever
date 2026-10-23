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
| License | GNU General Public License version 3 (GPLv3) |
| Source | https://github.com/addohm/SubZones-WoW-Forever |
| Issues | https://github.com/addohm/SubZones-WoW-Forever/issues |

**Categories**
- CurseForge: Map & Minimap (main), Quests & Leveling
- Wago: Map & Minimap (main), Quests & Leveling

**Summary** (the one-liner under the name; 105 characters)

> See every subzone on your map: borders, names and optional color tints, straight from the game's
> terrain.

**Short tagline** (for images or a Discord post)

> Know exactly where Goldshire ends.

**Art** (in [art/](art))
- Project icon: `art/subzones-logo-400.png` (`art/subzones-logo-1024.png` for larger sizes,
  `art/subzones-logo-round-1024.png` with a transparent background)
- Header or banner image: `art/subzones-banner.png` (1920×480)

---

## Description

*(Paste as Markdown. Both sites accept it.)*

### SUBZONES

**Built for WoW: Forever, where the map shows you the zone but not where its subzones begin and
end.**

SUBZONES draws every subzone's borders and name on your world map, with optional color tints, and
puts the borders around you on the minimap. The borders aren't hand-drawn or guessed: they come
from the game's own terrain files, the same data the client uses to decide which subzone you're
standing in. When you cross a SUBZONES line, your subzone changes.

#### On the world map

- Smoothed outlines for every subzone of the zone you're viewing.
- Each subzone's name at its center. Ones you haven't explored yet show in grey, or you can hide
  them.
- Three styles: **Lines only** (the default), **Lines + tint**, or **Tint only**. Neighbouring
  subzones always get clearly different colors.
- A **Subzones** checkbox at the bottom-left of the map turns it on and off. Right-click it for the
  style, names, unexplored subzones and the options.

#### On the minimap

- Your current zone's subzone borders, drawn around you as you move.
- Clipped to a round or square minimap, and turning with **Rotate Minimap**.
- Redraws only when you move, turn or zoom.

#### From the game's own terrain

- WoW has no subzone shapes. Instead, the world is a grid of 33-yard terrain chunks, and each chunk
  is tagged with one area. SUBZONES reads that grid from the client, traces the edges between areas
  and smooths the 33-yard staircase into curves.
- It matches **99.95%** of the subzone chunks published by wowforevermap.com. The only differences
  are where Forever itself changed the map (Dalaran and Windstead).
- Names come from the game, in your client's language.

#### Make it yours

- Style, subzone names, unexplored subzones, minimap borders, line width and tint opacity.
- All in **Settings → AddOns → SUBZONES**, the right-click menu on the map checkbox, or by command.

#### Commands

- `/subzones`: turn the overlay on or off. `/subzones options`: the settings panel.
- `/subzones lines`, `/subzones both`, `/subzones tint`: pick the style.
- `/subzones labels`, `/subzones unexplored`, `/subzones minimap`, `/subzones alpha [0-1]`,
  `/subzones width [px]`, `/subzones blend`
- `/subzones debug`: a short report to paste when something looks wrong. `/sz` works for all of
  them.

#### Good to know

- Covers Eastern Kingdoms, Kalimdor and Zephras Isle.
- Draws on zone maps only, never whole continents, so the map stays fast.
- Display only: SUBZONES never acts for you.
- Everything stays on your computer in the game's own saved data. No network access, no libraries.
- Free and open source under the GNU GPL v3: the code is on GitHub.
- Found a border in the wrong place? Open an issue on GitHub with a screenshot, and include what
  `/subzones debug` shows.

---

## Screenshots to take

1. **Hero:** Elwynn Forest world map, Lines + tint, names on.
2. Lines only on a busy zone (Stranglethorn Vale or Ashenvale).
3. The minimap while standing on a border, round, with Rotate Minimap on.
4. A partly explored zone: grey names next to gold ones.
5. Tint only on a zone with many small subzones.
6. Settings → AddOns → SUBZONES.
7. The right-click menu on the map's **Subzones** checkbox.

Tips: use a clean UI (hide other addons), 16:9 at 1920×1080, crop to the subject, and scale the UI
so the names are readable.

---

## Release notes for 1.0.0

> First public release, for WoW: Forever.
>
> - Subzone borders and names on the world map, in Lines, Lines + tint or Tint styles
> - Subzone borders on the minimap, clipped to its shape and turning with it
> - Unexplored subzones in grey, or hidden
> - Borders from the game's own terrain data, covering Eastern Kingdoms, Kalimdor and Zephras Isle
> - Settings panel, right-click map menu and `/subzones` (`/sz`) commands

---

## Before publishing

- Test the packaged `release/SUBZONES-1.0.0.zip` in game: the icon in the AddOns list, and
  `/subzones debug` saying build `release`.
- The package is ready at 1.0.0. For later versions, bump `## Version` in `SUBZONES/SUBZONES.toc`,
  move the CHANGELOG's Unreleased entries under the version, then `python tools/package.py` and
  commit the new zip in `release/` (see DEPLOY.md).
- Add the project IDs to `SUBZONES/SUBZONES.toc` (`## X-Curse-Project-ID`, `## X-Wago-ID`) once the
  projects exist, then rebuild the zip.
- Check that CurseForge and Wago list a Forever game version (Interface 16001) at launch, Nov 4,
  2026.
- Cut the wowforevermap.com line if you'd rather not name another project.
- Project icon: `art/subzones-logo-400.png`. The same logo is the addon's in-game icon
  (`SUBZONES/icon.tga`, in the AddOns list).
