# Subzone data: wowforevermap.com vs game client

Game build 1.60.1.70334. Every terrain chunk (33⅓ yd square) the site marks as a subzone
is checked against the area ID stored in that chunk's header in the game's terrain files.

## Overall

**125,338 of 125,396 subzone chunks match (99.95%).**

Diff images (green = match, red = different, gray = terrain the site leaves unassigned): comparison_0.png, comparison_1.png, comparison_2991.png

## Continent 0

- Terrain tiles: 736 (188,416 chunks, 449 distinct area IDs)
- Site subzone chunks checked: **47,230**
- Matching: **47,172 (99.88%)**
- Different area in game: 58

Largest disagreements (site area → game area: chunks):

- Old Dalaran Ruins (17707) → Dalaran (279): 31
- Windstead (16731) → #17847: 20
- Lordamere Internment Camp (278) → Dalaran (279): 6
- Hillsbrad Fields (286) → Dalaran (279): 1

Game areas the site doesn't draw (44; mostly zone-level areas, i.e. parts of a zone that belong to no subzone): #2399×13585, #139×10596, #2338×8105, #2364×7989, #2398×5982, #2365×5881, #2402×5824, #2403×5710, #16820×5342, #1×3969, #2339×3040, #2400×3032, #11×2900, #16591×2688, #2401×2437, #17065×2270, #33×2235, #85×2090, #45×2090, #51×1968, #47×1895, #17066×1850, #130×1802, #46×1778, #12×1762, #16361×1714, #408×1536, #28×1422, #38×1371, #2397×1082, #267×1080, #10×1035, #3×929, #4×822, #44×812, #8×755, #40×725, #1519×693, #41×483, #36×361 …

## Continent 1

- Terrain tiles: 988 (252,928 chunks, 416 distinct area IDs)
- Site subzone chunks checked: **74,470**
- Matching: **74,470 (100.00%)**
- Different area in game: 0

Game areas the site doesn't draw (37; mostly zone-level areas, i.e. parts of a zone that belong to no subzone): #2322×21138, #2317×16418, #2326×13097, #2477×12958, #2321×6431, #1377×6343, #2323×5689, #2318×5627, #141×5285, #17×5115, #2320×4385, #2324×4215, #440×3315, #2325×3092, #618×2876, #405×2804, #406×2790, #876×2304, #331×2300, #215×2265, #616×2237, #357×2210, #361×1963, #14×1923, #490×1803, #148×1761, #400×1607, #493×1456, #16×1399, #15×1278, #2319×683, #16651×619, #1637×546, #3478×240, #1638×160, #1657×105, #332×35

## Continent 2991

- Terrain tiles: 72 (18,432 chunks, 25 distinct area IDs)
- Site subzone chunks checked: **3,696**
- Matching: **3,696 (100.00%)**
- Different area in game: 0

Game areas the site doesn't draw (2; mostly zone-level areas, i.e. parts of a zone that belong to no subzone): #17221×8031, #16593×5436

