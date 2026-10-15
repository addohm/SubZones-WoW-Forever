-- SUBZONES: subzone borders, names and optional color fills on the world map.
--
-- SubzoneBorders.lua holds, per continent, every terrain area's label point
-- and the border polylines between areas, extracted from the game's own
-- terrain files (each 33 1/3-yard chunk stores one area ID). In-game, each
-- map's subzones are found by asking the client which map owns each area's
-- label point; the zone-level area itself is then dropped. Points are
-- projected with C_Map.GetWorldPosFromMapPos, and fills are built from the
-- same polylines, so tint and lines always agree.
--
-- Blizzard_MapCanvas is load-on-demand on some clients, so nothing here
-- touches its mixins until the world map has loaded (see Install).

local ADDON_NAME = ...
local TITLE = "SUBZONES"

local GOLDEN_RATIO = 0.618033988749895
local MIN_NEIGHBOUR_HUE_GAP = 0.12 -- subzones that share a border get clearly different hues
local ZONE_AREA_SHARE = 0.35 -- an unnamed area this big a share of the map is the zone itself
local MAX_SUBZONES_PER_MAP = 120 -- more than this means the ownership test failed; don't draw
local LABEL_SIZE = 13
local CASING_COLOR = { 0, 0, 0, 0.85 }

-- SetVertexOffset corner indices (globals on newer clients).
local UPPER_LEFT = UPPER_LEFT_VERTEX or 1
local LOWER_LEFT = LOWER_LEFT_VERTEX or 2
local UPPER_RIGHT = UPPER_RIGHT_VERTEX or 3
local LOWER_RIGHT = LOWER_RIGHT_VERTEX or 4

local MODES = { lines = "Lines only", both = "Lines + tint", tint = "Tint only" }
local MODE_ORDER = { "lines", "both", "tint" }

local DEFAULTS = {
	enabled = true,
	mode = "lines",
	labels = true,
	unexplored = true,
	minimap = true,
	alpha = 0.35,
	blend = "BLEND",
	lineWidth = 1.5,
	lineColor = { 1, 0.95, 0.8, 0.95 },
}

local db
local provider
local overlay -- frame on the map canvas holding all fills, lines and labels
local settingsCategory

local function Print(...)
	print("|cff66ccff" .. TITLE .. "|r:", ...)
end

local function HSVtoRGB(h, s, v)
	local i = math.floor(h * 6)
	local f = h * 6 - i
	local p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
	i = i % 6
	if i == 0 then return v, t, p
	elseif i == 1 then return q, v, p
	elseif i == 2 then return p, v, t
	elseif i == 3 then return p, q, v
	elseif i == 4 then return t, p, v
	end
	return v, p, q
end

-- Golden-ratio hue steps keep consecutive indices visually far apart.
local function HueOf(index)
	return (0.12 + index * GOLDEN_RATIO) % 1
end

local function ColorFor(index)
	return HSVtoRGB(HueOf(index), 0.75, 1)
end

local function AreaName(areaID)
	local name = C_Map.GetAreaInfo(areaID)
	if name and name ~= "" then return name end
	return SubzoneBorders.names[areaID]
end

-- Map context: which areas are this map's subzones -------------------------------

local function WorldPos(mapID, u, v)
	local ok, continentID, pos = pcall(C_Map.GetWorldPosFromMapPos, mapID, CreateVector2D(u, v))
	if ok and pos then return continentID, pos end
end

local function Inside(u, v, margin)
	return u >= -margin and u <= 1 + margin and v >= -margin and v <= 1 + margin
end

-- [areaID] = { line indices }, per continent, built on first use.
local function LinesByArea(continent)
	if not continent.byArea then
		local byArea = {}
		for i, p in ipairs(continent.lines) do
			for side = 1, 2 do
				local area = p[side]
				if area ~= 0 then
					byArea[area] = byArea[area] or {}
					table.insert(byArea[area], i)
				end
			end
		end
		continent.byArea = byArea
	end
	return continent.byArea
end

local contexts = {} -- [uiMapID] = context, or false when the map has no data

-- Affine world -> normalized map projection from three of the map's corners.
-- The API's world vectors are (worldX, worldY), the same order as the data.
local function Projection(mapID)
	local continentID, p00 = WorldPos(mapID, 0, 0)
	local _, p10 = WorldPos(mapID, 1, 0)
	local _, p01 = WorldPos(mapID, 0, 1)
	if not (continentID and p00 and p10 and p01) then return end
	local ox, oy = p00.x, p00.y
	local ax, ay = p10.x - ox, p10.y - oy
	local bx, by = p01.x - ox, p01.y - oy
	local det = ax * by - ay * bx
	if det == 0 then return end
	return function(wx, wy)
		local dx, dy = wx - ox, wy - oy
		return (dx * by - dy * bx) / det, (ax * dy - ay * dx) / det
	end, continentID
end

-- Returns belongs(worldX, worldY, u, v): whether a point on this map is in
-- this map's own territory rather than a neighbour drawn at the edges or a
-- city map nested inside it.
--
-- Preferred: ask the parent (continent) map which child is at the point, the
-- same lookup its mouseover highlight uses, then make sure no child of this
-- map (a city) sits there. Fallback, for maps without a usable parent on the
-- same continent: C_Map.GetMapPosFromWorldPos, which names the zone directly
-- only where no continent map sits in between.
local function OwnershipTest(mapID, mapInfo, continentID)
	local atPos = C_Map.GetMapInfoAtPosition
	local parentID = mapInfo.parentMapID
	local parentProject, parentContinent
	if atPos and parentID and parentID ~= 0 then
		parentProject, parentContinent = Projection(parentID)
	end
	if parentProject and parentContinent == continentID then
		return function(wx, wy, u, v)
			local pu, pv = parentProject(wx, wy)
			local ok, info = pcall(atPos, parentID, pu, pv)
			if not (ok and info and info.mapID == mapID) then return false end
			local ok2, here = pcall(atPos, mapID, u, v)
			return not (ok2 and here and here.mapID ~= mapID)
		end
	end
	local owner = C_Map.GetMapPosFromWorldPos
	if owner then
		return function(wx, wy)
			local ok, ownerMap = pcall(owner, continentID, CreateVector2D(wx, wy))
			return ok and ownerMap == mapID
		end
	end
	return function() return true end
end

-- Builds the projection for a map and finds its subzones:
--  1. Only zone-level maps and below; continent and world maps show the
--     whole continent's areas, far too many to draw.
--  2. Areas whose label lands on the map and in this map's own territory.
--  3. Drop the zone-level area: the one named like the map, or failing that
--     one covering most of the map.
local function MapContext(mapID)
	if contexts[mapID] ~= nil then return contexts[mapID] or nil end
	contexts[mapID] = false
	if not (C_Map.GetWorldPosFromMapPos and CreateVector2D and SubzoneBorders) then return end

	local mapInfo = C_Map.GetMapInfo(mapID)
	local zoneType = Enum and Enum.UIMapType and Enum.UIMapType.Zone or 3
	if not mapInfo or (mapInfo.mapType and mapInfo.mapType < zoneType) then return end

	local project, continentID = Projection(mapID)
	local continent = continentID and SubzoneBorders.continents[continentID]
	if not (project and continent) then return end

	local mapName = mapInfo.name
	local belongs = OwnershipTest(mapID, mapInfo, continentID)
	local candidates, total = {}, 0
	for areaID, a in pairs(continent.areas) do
		local u, v = project(a[1], a[2])
		if Inside(u, v, 0) and belongs(a[1], a[2], u, v) then
			candidates[#candidates + 1] = { id = areaID, u = u, v = v, cells = a[3] }
			total = total + a[3]
		end
	end
	if #candidates > MAX_SUBZONES_PER_MAP then
		Print(("map %d matched %d areas; skipping it (send /subzones debug output)"):format(mapID, #candidates))
		return
	end

	local zoneArea
	for _, area in ipairs(candidates) do
		if mapName and AreaName(area.id) == mapName then zoneArea = area.id end
	end
	if not zoneArea then
		for _, area in ipairs(candidates) do
			if area.cells > total * ZONE_AREA_SHARE then zoneArea = area.id end
		end
	end

	local members, isMember = {}, {}
	for _, area in ipairs(candidates) do
		if area.id ~= zoneArea then
			members[#members + 1] = area
			isMember[area.id] = true
		end
	end
	table.sort(members, function(a, b) return a.id < b.id end)

	local context = {
		continent = continent, project = project,
		members = members, isMember = isMember, zoneArea = zoneArea,
	}
	contexts[mapID] = context
	return context
end

-- Fills ----------------------------------------------------------------------------

-- Splits one subzone into horizontal trapezoids (even-odd scanline over its
-- border segments), so holes and nested subzones fill correctly. Slabs are cut
-- at every vertex along worldX; a trapezoid keeps growing while it is bounded
-- by the same pair of segments. Each result is
-- { xLo, xHi, leftAtLo, rightAtLo, leftAtHi, rightAtHi } in world coordinates.
local function Trapezoids(segs)
	local stops, seen = {}, {}
	for _, s in ipairs(segs) do
		for _, x in ipairs({ s[1], s[3] }) do
			if not seen[x] then
				seen[x] = true
				stops[#stops + 1] = x
			end
		end
	end
	table.sort(stops)
	table.sort(segs, function(a, b) return a[1] < b[1] end)

	local function yAt(s, x)
		return s[2] + (s[4] - s[2]) * (x - s[1]) / (s[3] - s[1])
	end

	local result, open, active, nextSeg = {}, {}, {}, 1
	for k = 1, #stops - 1 do
		local lo, hi = stops[k], stops[k + 1]
		while nextSeg <= #segs and segs[nextSeg][1] <= lo do
			active[#active + 1] = segs[nextSeg]
			nextSeg = nextSeg + 1
		end
		local current = {}
		for _, s in ipairs(active) do
			if s[3] >= hi then current[#current + 1] = s end
		end
		active = current

		local mid = (lo + hi) / 2
		local order = {}
		for i, s in ipairs(current) do order[i] = { yAt(s, mid), s } end
		table.sort(order, function(a, b) return a[1] < b[1] end)

		local stillOpen = {}
		for j = 1, #order - 1, 2 do
			local left, right = order[j][2], order[j + 1][2]
			local key = left.id * 1048576 + right.id
			local t = open[key]
			if t then
				t.hi = hi
			else
				t = { lo = lo, hi = hi, left = left, right = right }
				result[#result + 1] = t
			end
			stillOpen[key] = t
		end
		open = stillOpen
	end

	for i, t in ipairs(result) do
		result[i] = { t.lo, t.hi, yAt(t.left, t.lo), yAt(t.right, t.lo), yAt(t.left, t.hi), yAt(t.right, t.hi) }
	end
	return result
end

-- Each subzone's fill and color: every subzone gets its own hue, nudged along
-- the sequence until it's clearly different from any subzone it borders.
local function ZoneFills(context)
	if context.fills then return context.fills end
	local continent = context.continent
	local byArea = LinesByArea(continent)
	local fills = {}
	local nextID = 0
	for i, area in ipairs(context.members) do
		local segs, neighbours = {}, {}
		for _, index in ipairs(byArea[area.id] or {}) do
			local p = continent.lines[index]
			local other = p[1] == area.id and p[2] or p[1]
			if context.isMember[other] then neighbours[other] = true end
			for k = 3, #p - 3, 2 do
				local x1, y1, x2, y2 = p[k], p[k + 1], p[k + 2], p[k + 3]
				if x1 ~= x2 then -- segments along a scanline don't bound a slab
					if x1 > x2 then x1, y1, x2, y2 = x2, y2, x1, y1 end
					nextID = nextID + 1
					segs[#segs + 1] = { x1, y1, x2, y2, id = nextID }
				end
			end
		end

		local color = i
		for _ = 1, 32 do
			local clash = false
			for other in pairs(neighbours) do
				if fills[other] then
					local d = math.abs(HueOf(color) - HueOf(fills[other].color))
					if math.min(d, 1 - d) < MIN_NEIGHBOUR_HUE_GAP then clash = true end
				end
			end
			if not clash then break end
			color = color + 1
		end
		fills[area.id] = { pieces = Trapezoids(segs), color = color }
	end
	context.fills = fills
	return fills
end

-- Drawing ------------------------------------------------------------------------

local function Acquire(pool, create)
	pool.used = pool.used + 1
	local obj = pool[pool.used]
	if not obj then
		obj = create()
		pool[pool.used] = obj
	end
	obj:Show()
	return obj
end

local function ReleaseAll(pool)
	for i = 1, pool.used do pool[i]:Hide() end
	pool.used = 0
end

local function ClearOverlay()
	if not overlay then return end
	ReleaseAll(overlay.fills)
	ReleaseAll(overlay.casings)
	ReleaseAll(overlay.lines)
	ReleaseAll(overlay.labels)
end

local function NewFill()
	return overlay:CreateTexture(nil, "ARTWORK")
end

local function NewCasing()
	return overlay:CreateLine(nil, "OVERLAY", nil, 1)
end

local function NewLine()
	return overlay:CreateLine(nil, "OVERLAY", nil, 2)
end

local function NewLabel()
	local label = overlay:CreateFontString(nil, "OVERLAY")
	label:SetDrawLayer("OVERLAY", 7)
	label:SetJustifyH("CENTER")
	return label
end

-- A solid quad with arbitrary (convex) corners: a color texture sized to the
-- bounding box, with each corner pulled onto its point. Corners are given in
-- canvas pixels, y down, in cyclic order.
local function DrawQuad(x1, y1, x2, y2, x3, y3, x4, y4, r, g, b, a)
	if (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1) < 0 then
		x2, y2, x4, y4 = x4, y4, x2, y2 -- make it clockwise on screen
	end
	local minX, maxX = math.min(x1, x2, x3, x4), math.max(x1, x2, x3, x4)
	local minY, maxY = math.min(y1, y2, y3, y4), math.max(y1, y2, y3, y4)
	if maxX - minX < 0.01 or maxY - minY < 0.01 then return end

	local tex = Acquire(overlay.fills, NewFill)
	tex:ClearAllPoints()
	tex:SetPoint("TOPLEFT", overlay, "TOPLEFT", minX, -minY)
	tex:SetSize(maxX - minX, maxY - minY)
	tex:SetColorTexture(r, g, b, a)
	tex:SetBlendMode(db.blend)
	tex:SetVertexOffset(UPPER_LEFT, x1 - minX, minY - y1)
	tex:SetVertexOffset(UPPER_RIGHT, x2 - maxX, minY - y2)
	tex:SetVertexOffset(LOWER_RIGHT, x3 - maxX, maxY - y3)
	tex:SetVertexOffset(LOWER_LEFT, x4 - minX, maxY - y4)
end

local function AddLabel(text, x, y, r, g, b)
	local label = Acquire(overlay.labels, NewLabel)
	label:ClearAllPoints()
	label:SetFont(STANDARD_TEXT_FONT, LABEL_SIZE * overlay.scale, "OUTLINE")
	label:SetPoint("CENTER", overlay, "TOPLEFT", x, -y)
	label:SetText(text)
	label:SetTextColor(r, g, b)
end

-- Lines keep a constant on-screen width: the overlay zooms with the canvas,
-- so divide the configured width by the canvas scale.
local function UpdateLineThickness()
	if not overlay then return end
	local scale = WorldMapFrame.GetCanvasScale and WorldMapFrame:GetCanvasScale()
	if not scale or scale <= 0 then scale = 1 end
	local thickness = db.lineWidth / scale
	local casing = (db.lineWidth + 2) / scale
	for i = 1, overlay.lines.used do overlay.lines[i]:SetThickness(thickness) end
	for i = 1, overlay.casings.used do overlay.casings[i]:SetThickness(casing) end
end

local function AddSegment(x1, y1, x2, y2)
	local casing = Acquire(overlay.casings, NewCasing)
	casing:SetStartPoint("TOPLEFT", overlay, x1, -y1)
	casing:SetEndPoint("TOPLEFT", overlay, x2, -y2)
	casing:SetColorTexture(unpack(CASING_COLOR))

	local line = Acquire(overlay.lines, NewLine)
	line:SetStartPoint("TOPLEFT", overlay, x1, -y1)
	line:SetEndPoint("TOPLEFT", overlay, x2, -y2)
	line:SetColorTexture(unpack(db.lineColor))
end

local function IsExplored(mapID, areaID, u, v)
	local getAreaIDs = C_MapExplorationInfo and C_MapExplorationInfo.GetExploredAreaIDsAtPosition
	local ids = getAreaIDs and getAreaIDs(mapID, CreateVector2D(u, v))
	if ids then
		for _, id in ipairs(ids) do
			if id == areaID then return true end
		end
	end
	return false
end

local function VisibleAreas(mapID, context)
	local visible = {}
	for _, area in ipairs(context.members) do
		local explored = IsExplored(mapID, area.id, area.u, area.v)
		if explored or db.unexplored then
			visible[#visible + 1] = { id = area.id, u = area.u, v = area.v, explored = explored }
		end
	end
	return visible
end

local function DrawFills(context, width, height, visible)
	local fills = ZoneFills(context)
	local project = context.project
	for _, area in ipairs(visible) do
		local info = fills[area.id]
		local r, g, b = ColorFor(info.color)
		local alpha = area.explored and db.alpha or db.alpha * 0.6
		for _, t in ipairs(info.pieces) do
			local u1, v1 = project(t[1], t[3])
			local u2, v2 = project(t[1], t[4])
			local u3, v3 = project(t[2], t[6])
			local u4, v4 = project(t[2], t[5])
			DrawQuad(u1 * width, v1 * height, u2 * width, v2 * height,
				u3 * width, v3 * height, u4 * width, v4 * height, r, g, b, alpha)
		end
	end
end

-- Every border that touches one of this map's subzones, each drawn once.
local function DrawBorders(context, width, height)
	local continent, project = context.continent, context.project
	local byArea = LinesByArea(continent)
	local drawn = {}
	for _, area in ipairs(context.members) do
		for _, index in ipairs(byArea[area.id] or {}) do
			if not drawn[index] then
				drawn[index] = true
				local p = continent.lines[index]
				local u, v = project(p[3], p[4])
				local x1, y1 = u * width, v * height
				for i = 5, #p - 1, 2 do
					u, v = project(p[i], p[i + 1])
					local x2, y2 = u * width, v * height
					AddSegment(x1, y1, x2, y2)
					x1, y1 = x2, y2
				end
			end
		end
	end
	UpdateLineThickness()
end

local function DrawLabels(width, height, visible)
	for _, area in ipairs(visible) do
		local name = AreaName(area.id)
		if name then
			if area.explored then
				AddLabel(name, area.u * width, area.v * height, 1, 0.92, 0.7)
			else
				AddLabel(name, area.u * width, area.v * height, 0.65, 0.65, 0.65)
			end
		end
	end
end

local function DrawOverlay()
	ClearOverlay()
	if not db.enabled then return end

	local mapID = WorldMapFrame:GetMapID()
	local context = mapID and MapContext(mapID)
	if not context or #context.members == 0 then return end

	local canvas = WorldMapFrame:GetCanvas()
	local width, height = canvas:GetWidth(), canvas:GetHeight()
	if width <= 0 or height <= 0 then return end
	local layer = (C_Map.GetMapArtLayers(mapID) or {})[1]
	overlay.scale = layer and width / layer.layerWidth or 1

	-- Just above Blizzard's exploration layer, under every other pin.
	local levels = WorldMapFrame.GetPinFrameLevelsManager and WorldMapFrame:GetPinFrameLevelsManager()
	local ok, level = false, nil
	if levels then
		ok, level = pcall(levels.GetValidFrameLevel, levels, "PIN_FRAME_LEVEL_MAP_EXPLORATION")
	end
	overlay:SetFrameLevel(ok and level and level + 1 or canvas:GetFrameLevel() + 1)

	local visible = VisibleAreas(mapID, context)
	if db.mode ~= "lines" then
		DrawFills(context, width, height, visible)
	end
	if db.mode ~= "tint" then
		DrawBorders(context, width, height)
	end
	if db.labels then
		DrawLabels(width, height, visible)
	end
end

-- Minimap -------------------------------------------------------------------------
-- Borders of the current zone's subzones, drawn around the player. The minimap
-- shows a fixed number of yards per zoom level (indoor and outdoor differ, the
-- same table HereBeDragons uses); lines are clipped to its round or square edge
-- and turn with the player when "Rotate Minimap" is on.

local MINIMAP_DIAMETER = {
	indoor = { [0] = 300, 240, 180, 120, 80, 50 },
	outdoor = { [0] = 466 + 2 / 3, 400, 333 + 1 / 3, 266 + 2 / 3, 200, 133 + 1 / 3 },
}
local MINIMAP_INTERVAL = 0.03 -- seconds between redraws while something changes
local MINIMAP_EDGE_INSET = 2 -- pixels kept clear inside the minimap's edge

local minimapFrame
local minimapLast = {} -- what the last redraw was based on
local minimapElapsed = 0

-- [i] = { minX, maxX, minY, maxY } per line, per continent, built on first use.
local function LineBounds(continent)
	if not continent.bounds then
		local bounds = {}
		for i, p in ipairs(continent.lines) do
			local minX, maxX, minY, maxY = math.huge, -math.huge, math.huge, -math.huge
			for k = 3, #p - 1, 2 do
				local x, y = p[k], p[k + 1]
				if x < minX then minX = x end
				if x > maxX then maxX = x end
				if y < minY then minY = y end
				if y > maxY then maxY = y end
			end
			bounds[i] = { minX, maxX, minY, maxY }
		end
		continent.bounds = bounds
	end
	return continent.bounds
end

-- Caves and other micro maps show their zone's subzones.
local function ZoneMapFor(mapID)
	local zoneType = Enum and Enum.UIMapType and Enum.UIMapType.Zone or 3
	local info = C_Map.GetMapInfo(mapID)
	while info and info.mapType and info.mapType > zoneType and info.parentMapID and info.parentMapID ~= 0 do
		info = C_Map.GetMapInfo(info.parentMapID)
	end
	return info and info.mapID
end

-- Clips a segment to a circle of radius r (or a square of half-size r)
-- centered on the origin; returns nothing when it lies entirely outside.
local function ClipRound(x1, y1, x2, y2, r)
	local dx, dy = x2 - x1, y2 - y1
	local a = dx * dx + dy * dy
	if a == 0 then return end
	local b = 2 * (x1 * dx + y1 * dy)
	local c = x1 * x1 + y1 * y1 - r * r
	local disc = b * b - 4 * a * c
	if disc <= 0 then return end
	local s = math.sqrt(disc)
	local t0, t1 = (-b - s) / (2 * a), (-b + s) / (2 * a)
	if t0 > 1 or t1 < 0 then return end
	if t0 < 0 then t0 = 0 end
	if t1 > 1 then t1 = 1 end
	return x1 + dx * t0, y1 + dy * t0, x1 + dx * t1, y1 + dy * t1
end

local function ClipSquare(x1, y1, x2, y2, r)
	local dx, dy = x2 - x1, y2 - y1
	local t0, t1 = 0, 1
	-- Liang-Barsky against the four edges.
	local p = { -dx, dx, -dy, dy }
	local q = { x1 + r, r - x1, y1 + r, r - y1 }
	for i = 1, 4 do
		if p[i] == 0 then
			if q[i] < 0 then return end
		else
			local t = q[i] / p[i]
			if p[i] < 0 then
				if t > t1 then return end
				if t > t0 then t0 = t end
			else
				if t < t0 then return end
				if t < t1 then t1 = t end
			end
		end
	end
	return x1 + dx * t0, y1 + dy * t0, x1 + dx * t1, y1 + dy * t1
end

local function NewMinimapCasing()
	return minimapFrame:CreateLine(nil, "OVERLAY", nil, 1)
end

local function NewMinimapLine()
	return minimapFrame:CreateLine(nil, "OVERLAY", nil, 2)
end

local function AddMinimapSegment(x1, y1, x2, y2, thickness)
	local casing = Acquire(minimapFrame.casings, NewMinimapCasing)
	casing:SetStartPoint("CENTER", minimapFrame, x1, y1)
	casing:SetEndPoint("CENTER", minimapFrame, x2, y2)
	casing:SetColorTexture(unpack(CASING_COLOR))
	casing:SetThickness(thickness + 2)

	local line = Acquire(minimapFrame.lines, NewMinimapLine)
	line:SetStartPoint("CENTER", minimapFrame, x1, y1)
	line:SetEndPoint("CENTER", minimapFrame, x2, y2)
	line:SetColorTexture(unpack(db.lineColor))
	line:SetThickness(thickness)
end

local function ClearMinimap()
	if not minimapFrame then return end
	ReleaseAll(minimapFrame.casings)
	ReleaseAll(minimapFrame.lines)
end

-- Player position, zone context and minimap geometry, or nil when there is
-- nothing to draw (option off, instance, map without data).
local function MinimapView()
	if not (db.enabled and db.minimap) then return end
	local mapID = C_Map.GetBestMapForUnit("player")
	local pos = mapID and C_Map.GetPlayerMapPosition(mapID, "player")
	if not pos then return end
	local zoneID = ZoneMapFor(mapID)
	local context = zoneID and MapContext(zoneID)
	if not context or #context.members == 0 then return end
	local _, world = WorldPos(mapID, pos.x, pos.y)
	if not world then return end

	local zoom = Minimap:GetZoom() or 0
	local sizes = IsIndoors and IsIndoors() and MINIMAP_DIAMETER.indoor or MINIMAP_DIAMETER.outdoor
	local facing = GetCVar("rotateMinimap") == "1" and GetPlayerFacing and GetPlayerFacing() or 0
	local shape = GetMinimapShape and GetMinimapShape() or "ROUND"
	return {
		context = context, x = world.x, y = world.y, facing = facing or 0,
		diameter = sizes[zoom] or sizes[0], width = Minimap:GetWidth(), square = shape == "SQUARE",
	}
end

local function DrawMinimap(view)
	ClearMinimap()
	if not view then return end
	local continent, context = view.context.continent, view.context
	local byArea, bounds = LinesByArea(continent), LineBounds(continent)
	local scale = view.width / view.diameter -- pixels per yard
	local edge = view.width / 2 - MINIMAP_EDGE_INSET
	local reach = view.diameter * 0.75 -- yards; covers a square minimap's corners
	local px, py = view.x, view.y
	local cos, sin = math.cos(-view.facing), math.sin(-view.facing)
	local clip = view.square and ClipSquare or ClipRound
	local thickness = db.lineWidth

	-- World offset -> minimap pixels, x right and y up: north is +worldX
	-- (up) and west is +worldY (left), then rotate with the player's facing.
	local function toMinimap(wx, wy)
		local x, y = (py - wy) * scale, (wx - px) * scale
		return x * cos - y * sin, x * sin + y * cos
	end

	local drawn = {}
	for _, area in ipairs(context.members) do
		for _, index in ipairs(byArea[area.id] or {}) do
			local b = bounds[index]
			if not drawn[index] and b[2] >= px - reach and b[1] <= px + reach
				and b[4] >= py - reach and b[3] <= py + reach then
				drawn[index] = true
				local p = continent.lines[index]
				local x1, y1 = toMinimap(p[3], p[4])
				for k = 5, #p - 1, 2 do
					local x2, y2 = toMinimap(p[k], p[k + 1])
					local cx1, cy1, cx2, cy2 = clip(x1, y1, x2, y2, edge)
					if cx1 then AddMinimapSegment(cx1, cy1, cx2, cy2, thickness) end
					x1, y1 = x2, y2
				end
			end
		end
	end
end

local function RequestMinimapRedraw()
	wipe(minimapLast)
end

-- Redraws only when position, facing, zoom, size or zone changed.
local function MinimapOnUpdate(_, elapsed)
	minimapElapsed = minimapElapsed + elapsed
	if minimapElapsed < MINIMAP_INTERVAL then return end
	minimapElapsed = 0
	local view = MinimapView()
	local last = minimapLast
	if view then
		if last.x and last.context == view.context and last.diameter == view.diameter and last.width == view.width
			and math.abs(last.x - view.x) < 0.05 and math.abs(last.y - view.y) < 0.05
			and math.abs(last.facing - view.facing) < 0.002 then
			return
		end
		last.context, last.diameter, last.width = view.context, view.diameter, view.width
		last.x, last.y, last.facing = view.x, view.y, view.facing
	elseif last.empty then
		return
	end
	last.empty = not view or nil
	DrawMinimap(view)
end

local function InstallMinimap()
	if minimapFrame or not Minimap then return end
	minimapFrame = CreateFrame("Frame", nil, Minimap)
	minimapFrame:SetAllPoints(Minimap)
	minimapFrame:SetFrameLevel(Minimap:GetFrameLevel() + 5)
	minimapFrame:EnableMouse(false)
	minimapFrame.casings = { used = 0 }
	minimapFrame.lines = { used = 0 }
	minimapFrame:SetScript("OnUpdate", MinimapOnUpdate)
end

local function Refresh()
	if overlay and WorldMapFrame:IsShown() then
		DrawOverlay()
	end
	if SubzonesMapToggle then
		SubzonesMapToggle:SetChecked(db.enabled)
	end
	RequestMinimapRedraw()
end

-- Options panel (Settings > AddOns > SUBZONES) ----------------------------------------

local function OpenSettings()
	if settingsCategory and Settings and Settings.OpenToCategory then
		Settings.OpenToCategory(settingsCategory:GetID())
	else
		Print("options panel unavailable on this client; use /subzones help")
	end
end

local function RegisterSettings()
	if not (Settings and Settings.RegisterVerticalLayoutCategory and Settings.RegisterAddOnSetting) then return end
	local category = Settings.RegisterVerticalLayoutCategory(TITLE)

	local function setting(key, kind, label)
		local s = Settings.RegisterAddOnSetting(category, "SUBZONES_" .. key:upper(), key, db, kind, label, DEFAULTS[key])
		s:SetValueChangedCallback(Refresh)
		return s
	end

	Settings.CreateCheckbox(category, setting("enabled", "boolean", "Show subzones"),
		"Draw subzone borders and names on the world map.")

	local function styles()
		local container = Settings.CreateControlTextContainer()
		for _, mode in ipairs(MODE_ORDER) do container:Add(mode, MODES[mode]) end
		return container:GetData()
	end
	Settings.CreateDropdown(category, setting("mode", "string", "Style"), styles,
		"Borders, color fills, or both.")

	Settings.CreateCheckbox(category, setting("labels", "boolean", "Subzone names"),
		"Label each subzone with its name.")
	Settings.CreateCheckbox(category, setting("unexplored", "boolean", "Unexplored subzones"),
		"Also show subzones you haven't discovered yet (gray names, fainter fills).")
	Settings.CreateCheckbox(category, setting("minimap", "boolean", "Show on minimap"),
		"Draw your current zone's subzone borders on the minimap too.")

	local function slider(key, label, min, max, step, formatter, tooltip)
		local options = Settings.CreateSliderOptions(min, max, step)
		options:SetLabelFormatter(MinimalSliderWithSteppersMixin.Label.Right, formatter)
		Settings.CreateSlider(category, setting(key, "number", label), options, tooltip)
	end
	slider("lineWidth", "Line width", 0.5, 5, 0.5, function(v) return ("%.1f px"):format(v) end,
		"Border line width on screen.")
	slider("alpha", "Tint opacity", 0.05, 1, 0.05, function(v) return ("%d%%"):format(v * 100 + 0.5) end,
		"How strong the color fills are.")

	Settings.RegisterAddOnCategory(category)
	settingsCategory = category
end

-- Map controls -------------------------------------------------------------------

local function SetMode(mode)
	db.mode = mode
	Refresh()
end

local function NextMode()
	for i, mode in ipairs(MODE_ORDER) do
		if mode == db.mode then
			return MODE_ORDER[i % #MODE_ORDER + 1]
		end
	end
	return MODE_ORDER[1]
end

-- Right-click menu on the map checkbox; cycles the style if the modern menu
-- API isn't available.
local function ShowOptionsMenu(owner)
	if not (MenuUtil and MenuUtil.CreateContextMenu) then
		SetMode(NextMode())
		Print(MODES[db.mode])
		return
	end
	MenuUtil.CreateContextMenu(owner, function(_, root)
		root:CreateTitle(TITLE)
		for _, mode in ipairs(MODE_ORDER) do
			root:CreateRadio(MODES[mode], function() return db.mode == mode end, function() SetMode(mode) end)
		end
		root:CreateDivider()
		root:CreateCheckbox("Subzone names", function() return db.labels end, function()
			db.labels = not db.labels
			Refresh()
		end)
		root:CreateCheckbox("Unexplored subzones", function() return db.unexplored end, function()
			db.unexplored = not db.unexplored
			Refresh()
		end)
		root:CreateCheckbox("Show on minimap", function() return db.minimap end, function()
			db.minimap = not db.minimap
			Refresh()
		end)
		root:CreateDivider()
		root:CreateButton("Options...", OpenSettings)
	end)
end

local function CreateToggle()
	local container = WorldMapFrame.ScrollContainer or WorldMapFrame
	local check = CreateFrame("CheckButton", "SubzonesMapToggle", WorldMapFrame, "UICheckButtonTemplate")
	check:SetSize(24, 24)
	check:SetPoint("BOTTOMLEFT", container, "BOTTOMLEFT", 6, 6)
	check:SetFrameLevel(container:GetFrameLevel() + 2000)
	check:SetChecked(db.enabled)

	local text = check:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
	text:SetPoint("LEFT", check, "RIGHT", 0, 1)
	text:SetText("Subzones")

	check:RegisterForClicks("LeftButtonUp", "RightButtonUp")
	check:SetScript("OnClick", function(self, button)
		if button == "RightButton" then
			self:SetChecked(db.enabled) -- right-click shouldn't toggle
			ShowOptionsMenu(self)
			return
		end
		db.enabled = self:GetChecked() and true or false
		Refresh()
	end)
	check:SetScript("OnEnter", function(self)
		GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
		GameTooltip:SetText(TITLE)
		GameTooltip:AddLine("Style: " .. MODES[db.mode], 1, 1, 1)
		GameTooltip:AddLine("Right-click for options, /subzones help for commands", 0.7, 0.7, 0.7)
		GameTooltip:Show()
	end)
	check:SetScript("OnLeave", GameTooltip_Hide)
end

local function Install()
	if overlay or not db or not WorldMapFrame or not MapCanvasDataProviderMixin then return end

	local canvas = WorldMapFrame:GetCanvas()
	overlay = CreateFrame("Frame", nil, canvas)
	overlay:SetAllPoints(canvas)
	overlay:EnableMouse(false)
	overlay.scale = 1
	overlay.fills = { used = 0 }
	overlay.casings = { used = 0 }
	overlay.lines = { used = 0 }
	overlay.labels = { used = 0 }

	provider = CreateFromMixins(MapCanvasDataProviderMixin)
	provider.RemoveAllData = ClearOverlay
	provider.RefreshAllData = DrawOverlay
	provider.OnMapChanged = DrawOverlay
	provider.OnCanvasScaleChanged = UpdateLineThickness
	WorldMapFrame:AddDataProvider(provider)

	CreateToggle()
end

-- Slash commands -----------------------------------------------------------------

local function PrintDebug()
	local mapID = (WorldMapFrame and WorldMapFrame:IsShown() and WorldMapFrame:GetMapID())
		or C_Map.GetBestMapForUnit("player")
	if not mapID then
		Print("no map")
		return
	end
	local info = C_Map.GetMapInfo(mapID)
	Print(("map %d (%s) | style %s | data: %s"):format(mapID, info and info.name or "?", MODES[db.mode],
		SubzoneBorders and SubzoneBorders.source or "missing"))
	local context = MapContext(mapID)
	if not context then
		Print("no subzone data for this map")
		return
	end
	local pieces = 0
	for _, fill in pairs(ZoneFills(context)) do pieces = pieces + #fill.pieces end
	Print(("%d subzones, zone area %s (%s), %d fill pieces"):format(#context.members,
		tostring(context.zoneArea), context.zoneArea and AreaName(context.zoneArea) or "-", pieces))
	local first = context.members[1]
	if first then
		Print(("%s label at %.3f, %.3f (should be within 0-1)"):format(AreaName(first.id) or first.id, first.u, first.v))
	end
	Print("installed", overlay and "yes" or "no", "| interface", (select(4, GetBuildInfo())))
end

local function Toggle(key, label)
	db[key] = not db[key]
	Print(label, db[key] and "on" or "off")
end

local function HandleSlash(msg)
	local cmd, arg = strsplit(" ", strtrim(msg or ""):lower(), 2)
	if cmd == "" or cmd == "toggle" then
		Toggle("enabled", "overlay")
	elseif MODES[cmd] then
		db.mode = cmd
		Print("style", MODES[cmd])
	elseif cmd == "mode" then
		db.mode = MODES[arg or ""] and arg or NextMode()
		Print("style", MODES[db.mode])
	elseif cmd == "labels" then
		Toggle("labels", "labels")
	elseif cmd == "unexplored" then
		Toggle("unexplored", "unexplored subzones")
	elseif cmd == "minimap" then
		Toggle("minimap", "minimap borders")
	elseif cmd == "alpha" or cmd == "width" then
		local value = tonumber(arg)
		local max = cmd == "alpha" and 1 or 10
		if value and value > 0 and value <= max then
			db[cmd == "alpha" and "alpha" or "lineWidth"] = value
			Print(cmd, value)
		else
			Print(("usage: /subzones %s <0-%d>"):format(cmd, max))
		end
	elseif cmd == "blend" then
		db.blend = db.blend == "ADD" and "BLEND" or "ADD"
		Print("blend mode", db.blend)
	elseif cmd == "options" or cmd == "config" then
		OpenSettings()
		return
	elseif cmd == "debug" then
		PrintDebug()
		return
	else
		Print("/subzones [toggle] | options | lines | both | tint | labels | unexplored | minimap | alpha <0-1> | width <px> | blend | debug")
		return
	end
	Refresh()
end

SLASH_SUBZONES1 = "/subzones"
SLASH_SUBZONES2 = "/sz"
SlashCmdList.SUBZONES = HandleSlash

-- Events -------------------------------------------------------------------------

local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:RegisterEvent("PLAYER_LOGIN")
events:RegisterEvent("MAP_EXPLORATION_UPDATED")
events:SetScript("OnEvent", function(_, event, arg1)
	if event == "ADDON_LOADED" and arg1 == ADDON_NAME then
		SubzonesDB = SubzonesDB or {}
		db = SubzonesDB
		for key, value in pairs(DEFAULTS) do
			if db[key] == nil then
				db[key] = value
			end
		end
		if not MODES[db.mode] then db.mode = DEFAULTS.mode end
		local ok, err = pcall(RegisterSettings)
		if not ok then Print("couldn't add the options panel:", err) end
	elseif event == "ADDON_LOADED" and arg1 == "Blizzard_WorldMap" then
		Install()
	elseif event == "PLAYER_LOGIN" then
		Install()
		InstallMinimap()
	elseif event == "MAP_EXPLORATION_UPDATED" then
		if db then Refresh() end
	end
end)
