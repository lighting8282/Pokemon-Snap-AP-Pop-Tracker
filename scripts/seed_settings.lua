-- A readout of the options the connected seed was generated with.
--
-- Everywhere else the tracker deliberately avoids option names and works from
-- the seed's location list instead, because that stays correct when upstream
-- renames or reshuffles options. This panel is the one place the names are the
-- point: it is telling you what your yaml said, so it reads slot_data directly.
--
-- Each plate is lit when the option is on and dimmed when it is off. The four
-- that are not on/off carry their value as an overlay instead, and every plate
-- spells the setting out in its tooltip.
--
-- Must be loaded before Tracker:AddLayouts, since the layout places these.

SEED_SETTING_ITEMS = {}

local PLATES = {
    -- code suffix,     image key,        tooltip title
    {"goodtechnique", "goodtechnique", "Good Technique photos"},
    {"multiple",      "multiple",      "Multiple PKMN photos"},
    {"poses",         "poses",         "Special poses"},
    {"signs",         "signs",         "Pokemon Signs"},
    {"exits",         "exits",         "Secret exits"},
    {"photocount",    "photocount",    "Photo count rewards"},
    {"scoretotal",    "scoretotal",    "Report score rewards"},
    {"rng",           "rng",           "RNG checks"},
    {"hard",          "hard",          "Hard checks"},
    {"scoring",       "scoring",       "Photo scoring"},
    {"fragments",     "fragments",     "Map fragments"},
    {"goal",          "goal",          "Rainbow Cloud goal"},
    {"film",          "film",          "Film capacity"},
}

for _, p in ipairs(PLATES) do
    local key, image, title = p[1], p[2], p[3]
    local item = ScriptHost:CreateLuaItem()
    item.Name = title
    item.Icon = ImageReference:FromPackRelativePath("images/settings/" .. image .. ".png")
    item.IconMods = "@disabled"
    item.CanProvideCodeFunc = function(self, code) return code == "seed" .. key end
    item.ProvidesCodeFunc = function(self, code) return false end
    -- nothing to persist and nothing to click: this only reflects slot_data
    item.SaveFunc = function(self) return {} end
    item.LoadFunc = function(self, data) end
    SEED_SETTING_ITEMS[key] = item
end

local SCORING_NAME = {
    [0] = "vanilla", [1] = "separate",
    [2] = "progressive unlocks", [3] = "separate unlocks",
}
local SCORING_SHORT = {[0] = "van", [1] = "sep", [2] = "prog", [3] = "s.unl"}

local function set(key, lit, tooltip, overlay)
    local item = SEED_SETTING_ITEMS[key]
    if not item then return end
    item.IconMods = lit and "" or "@disabled"
    item.Name = tooltip
    if item.SetOverlay then
        item:SetOverlay(overlay or "")
        if overlay then
            if item.SetOverlayFontSize then item:SetOverlayFontSize(9) end
            if item.SetOverlayBackground then item:SetOverlayBackground("#c0000000") end
        end
    end
end

local function onoff(v) return v and "enabled" or "disabled" end

-- Called once slot_data has arrived. Without a connection every plate stays
-- dimmed, which is honest: the tracker does not know the seed's options yet.
function refreshSeedSettings(slot_data)
    local d = slot_data or {}
    local function opt(name, default)
        local v = d[name]
        if v == nil then return default end
        return v
    end

    local bonuses = opt("photo_bonuses", 2)
    set("goodtechnique", bonuses >= 1,
        "Good Technique photos: " .. onoff(bonuses >= 1))
    set("multiple", bonuses >= 2,
        "Multiple PKMN photos: " .. onoff(bonuses >= 2))

    for _, t in ipairs({
        {"poses",      "special_poses",      1, "Special poses"},
        {"signs",      "pokemon_signs",      1, "Pokemon Signs"},
        {"exits",      "secret_exits",       1, "Secret exits"},
        {"photocount", "report_photo_count", 1, "Photo count rewards"},
        {"scoretotal", "report_score_total", 1, "Report score rewards"},
        {"rng",        "rng_checks",         0, "RNG checks"},
        {"hard",       "hard_checks",        0, "Hard checks"},
    }) do
        local on = opt(t[2], t[3]) ~= 0
        set(t[1], on, t[4] .. ": " .. onoff(on))
    end

    local scoring = opt("photo_scoring", 0)
    set("scoring", true,
        "Photo scoring: " .. (SCORING_NAME[scoring] or scoring),
        SCORING_SHORT[scoring])

    local frags = opt("map_fragments", 1)
    set("fragments", frags > 1,
        frags > 1
            and string.format("Map fragments: %d per course", frags)
            or "Map fragments: off, courses use their own item",
        tostring(frags))

    local goal_type = opt("goal_type", 0)
    local needed = goal_type == 1 and opt("pokemon_required", 50)
                                  or opt("signs_required", 6)
    set("goal", true,
        string.format("Rainbow Cloud: %d %s", needed,
            goal_type == 1 and "Pokemon pictures" or "sign pictures"),
        tostring(needed))

    set("film", true,
        string.format("Film: starts at %d, +%d per upgrade, max %d",
            FILM_START or 15, FILM_STEP or 5, FILM_CAP or 60),
        tostring(FILM_START or 15))
end
