-- Clickable course icons.
--
-- A plain toggle cannot report a left-click that does not change its state, so
-- clicking a course you already own produced no event and the map never moved.
-- LuaItem has a real OnLeftClickFunc, which fires whatever the state is.
--
-- These items are display and clicking only. The JSON toggles in items.json keep
-- their codes (beach, tunnel, ...) and are still what autotracking sets and what
-- every access rule reads, so the logic is untouched by this file. Each Lua item
-- just mirrors the matching toggle's state into its icon.
--
-- Must be loaded before Tracker:AddLayouts, since LuaItems have to exist before
-- the layout that places them.

COURSE_ITEMS = {}

local COURSES = {
    { code = "beach",   tab = "Beach",   img = "images/beach.png",   name = "Beach" },
    { code = "tunnel",  tab = "Tunnel",  img = "images/tunnel.png",  name = "Tunnel" },
    { code = "volcano", tab = "Volcano", img = "images/volcano.png", name = "Volcano" },
    { code = "river",   tab = "River",   img = "images/river.png",   name = "River" },
    { code = "cave",    tab = "Cave",    img = "images/cave.png",    name = "Cave" },
    { code = "valley",  tab = "Valley",  img = "images/valley.png",  name = "Valley" },
}

for _, c in ipairs(COURSES) do
    local course = c
    local item = ScriptHost:CreateLuaItem()

    item.Name = course.name .. " (click to open its map)"
    item.Icon = ImageReference:FromPackRelativePath(course.img)
    item.IconMods = "@disabled"

    -- addressed in the layout as gobeach, gotunnel, ...
    item.CanProvideCodeFunc = function(self, code)
        return code == "go" .. course.code
    end

    -- deliberately provides nothing to access rules: the JSON toggle still does that
    item.ProvidesCodeFunc = function(self, code)
        return false
    end

    local function jump(self)
        if Tracker.UiHint then
            Tracker:UiHint("ActivateTab", course.tab)
        end
    end
    item.OnLeftClickFunc = jump
    item.OnRightClickFunc = jump

    -- nothing to persist: the icon is derived from the toggle on load
    item.SaveFunc = function(self) return {} end
    item.LoadFunc = function(self, data) end

    COURSE_ITEMS[course.code] = item

    local function refresh()
        local owned = Tracker:ProviderCountForCode(course.code) > 0
        item.IconMods = owned and "" or "@disabled"
    end
    refresh()
    ScriptHost:AddWatchForCode("courseicon_" .. course.code, course.code, refresh)
end
