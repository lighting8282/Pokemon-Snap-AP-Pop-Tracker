-- this is an example/ default implementation for AP autotracking
-- it will use the mappings defined in item_mapping.lua and location_mapping.lua to track items and locations via thier ids
-- it will also load the AP slot data in the global SLOT_DATA, keep track of the current index of on_item messages in CUR_INDEX
-- addition it will keep track of what items are local items and which one are remote using the globals LOCAL_ITEMS and GLOBAL_ITEMS
-- this is useful since remote items will not reset but local items might
ScriptHost:LoadScript("scripts/autotracking/item_mapping.lua")
ScriptHost:LoadScript("scripts/autotracking/location_mapping.lua")
ScriptHost:LoadScript("scripts/autotracking/sectionID.lua")
ScriptHost:LoadScript("scripts/autotracking/dex_mapping.lua")

CUR_INDEX = -1
SLOT_DATA = nil
LOCAL_ITEMS = {}
GLOBAL_ITEMS = {}

-- Course item code -> tab title in layouts/tracker.json. Used to jump to the
-- starting course's map on connect. STARTING_TAB_SET makes sure only the first
-- course we receive wins, so later course unlocks don't yank the view around.
COURSE_TABS = {
    beach   = "Beach",
    tunnel  = "Tunnel",
    volcano = "Volcano",
    river   = "River",
    cave    = "Cave",
    valley  = "Valley",
}
STARTING_TAB_SET = false

TAB_NAMES = {
    COURSE_TABS.beach,
    COURSE_TABS.tunnel,
    COURSE_TABS.volcano,
    COURSE_TABS.river,
    COURSE_TABS.cave,
    COURSE_TABS.valley,
}

-- Course icons are clickable LuaItems created in scripts/course_items.lua.
-- AUTOTRACK_BUSY is kept: onClear and onItem raise it so nothing mistakes a
-- script write for user input.
AUTOTRACK_BUSY = false

-- Which locations does this seed actually contain?
--
-- Archipelago reports every location in the slot, as CheckedLocations plus
-- MissingLocations, so the seed itself says what exists. apworld 0.6.0 added
-- fill_slot_data, but this stays keyed on the location list: it needs no option
-- names, so options added later work with no change here. slot_data is used
-- only for the goal, which is not expressible as a location.
--
-- Each mapped location has a hidden loc<id> flag that its section's visibility
-- rule requires. Working per location rather than per category matters: options
-- like rng_checks and hard_checks drop eight individual Multiple photos while
-- leaving the other twenty-seven in place, which a category-level flag cannot
-- express. This also covers photo_bonuses, special_poses, pokemon_signs and
-- secret_exits, and any future option, without naming any of them.
-- The Rainbow Cloud requirement is per seed since apworld 0.6.0: goal_type
-- picks between sign pictures and Pokemon pictures, and signs_required /
-- pokemon_required set how many. slot_data now carries all three, so Mew's
-- access rule calls this instead of hardcoding "all six signs".
GOAL_TYPE      = 0      -- 0 = sign pictures, 1 = Pokemon pictures
GOAL_REQUIRED  = 6
SIGN_CODES = {"signkingler","signpinsir","signkoffing","signcubone","signmewtwo","signdugtrio"}

function goal_unlocked()
    local have = 0
    if GOAL_TYPE == 1 then
        have = Tracker:ProviderCountForCode("newpic")
    else
        for _, c in ipairs(SIGN_CODES) do
            if Tracker:ProviderCountForCode(c) > 0 then have = have + 1 end
        end
    end
    return have >= GOAL_REQUIRED
end

function readGoalFromSlotData(slot_data)
    if type(slot_data) ~= "table" then return end
    if slot_data["goal_type"] ~= nil then GOAL_TYPE = slot_data["goal_type"] end
    if GOAL_TYPE == 1 then
        GOAL_REQUIRED = slot_data["pokemon_required"] or 50
    else
        GOAL_REQUIRED = slot_data["signs_required"] or 6
    end
    print(string.format("goal: %d %s picture(s) to reach the Rainbow Cloud",
          GOAL_REQUIRED, GOAL_TYPE == 1 and "Pokemon" or "sign"))
end

function applySeedContents()
    local checked = Archipelago.CheckedLocations
    local missing = Archipelago.MissingLocations
    if not checked and not missing then
        return          -- PopTracker too old to report them; leave everything visible
    end

    local present = {}
    for _, list in ipairs({checked or {}, missing or {}}) do
        for _, id in ipairs(list) do
            present[id] = true
            if id > 1000 then present[id - 1000] = true end   -- a bonus twin proves its base
        end
    end

    local shown, hidden = 0, 0
    for id, _ in pairs(LOCATION_MAPPING) do
        if id < 1000 then
            local obj = Tracker:FindObjectForCode("loc" .. id)
            if obj then
                local has = present[id] and true or false
                obj.Active = has
                if has then shown = shown + 1 else hidden = hidden + 1 end
            end
        end
    end

    local total = (checked and #checked or 0) + (missing and #missing or 0)
    print(string.format("seed has %d locations: %d checks shown, %d hidden as not in this seed",
                        total, shown, hidden))
end

function onClear(slot_data)
    if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
        print(string.format("called onClear, slot_data:\n%s", dump_table(slot_data)))
    end
    SLOT_DATA = slot_data
    CUR_INDEX = -1
    STARTING_TAB_SET = false
    AUTOTRACK_BUSY = true          -- everything below is our own write

    -- reset the Pokedex
    if PHOTO_DEX then
        for _, code in pairs(PHOTO_DEX) do
            local d = Tracker:FindObjectForCode(code)
            if d then d.Active = false end
        end
    end

    -- reset locations
    for _, v in pairs(LOCATION_MAPPING) do
        if v[1] then
            if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
                print(string.format("onClear: clearing location %s", v[1]))
            end
            local obj = Tracker:FindObjectForCode(v[1])
            if obj then
                if v[1]:sub(1, 1) == "@" then
                    obj.AvailableChestCount = obj.ChestCount
                else
                    obj.Active = false
                end
            elseif AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
                print(string.format("onClear: could not find object for code %s", v[1]))
            end
        end
    end
    -- reset items
    for _, v in pairs(ITEM_MAPPING) do
        if v[1] and v[2] then
            if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
                print(string.format("onClear: clearing item %s of type %s", v[1], v[2]))
            end
            local obj = Tracker:FindObjectForCode(v[1])
            if obj then
                if v[2] == "toggle" then
                    obj.Active = false
                elseif v[2] == "progressive" then
                    obj.CurrentStage = 0
                    obj.Active = false
                elseif v[2] == "consumable" then
                    if v[1] == "film" then
                        obj.AcquiredCount = 15
                    else
                        obj.AcquiredCount = 0
                    end
                elseif AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
                    print(string.format("onClear: unknown item type %s for code %s", v[2], v[1]))
                end
            elseif AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
                print(string.format("onClear: could not find object for code %s", v[1]))
            end
        end
    end

    print(dump_table(slot_data))
    
    readGoalFromSlotData(slot_data)
    applySeedContents()

    LOCAL_ITEMS = {}
    GLOBAL_ITEMS = {}
    AUTOTRACK_BUSY = false
    -- manually run snes interface functions after onClear in case we are already ingame
    if PopVersion < "0.20.1" or AutoTracker:GetConnectionState("SNES") == 3 then
        -- add snes interface functions here
    end
end

-- called when an item gets collected
function onItem(index, item_id, item_name, player_number)
    if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
        print(string.format("called onItem: %s, %s, %s, %s, %s", index, item_id, item_name, player_number, CUR_INDEX))
    end
    if index <= CUR_INDEX then
        return
    end
    local is_local = player_number == Archipelago.PlayerNumber
    CUR_INDEX = index;
    local v = ITEM_MAPPING[item_id]
    if not v then
        if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
            print(string.format("onItem: could not find item mapping for id %s", item_id))
        end
        return
    end
    if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
        print(string.format("onItem: code: %s, type %s", v[1], v[2]))
    end
    if not v[1] then
        return
    end
    -- Open the map tab for the first course received (the precollected starting area).
    -- UiHint is PopTracker-only, so check it exists before calling.
    if not STARTING_TAB_SET and COURSE_TABS[v[1]] and Tracker.UiHint then
        STARTING_TAB_SET = true
        if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
            print(string.format("activating starting tab: %s", COURSE_TABS[v[1]]))
        end
        Tracker:UiHint("ActivateTab", COURSE_TABS[v[1]])
    end
    local obj = Tracker:FindObjectForCode(v[1])
    if obj then
        AUTOTRACK_BUSY = true              -- this is autotracking, not a click
        if v[2] == "toggle" then
            obj.Active = true
        elseif v[2] == "progressive" then
            if obj.Active then
                obj.CurrentStage = obj.CurrentStage + 1
            else
                obj.Active = true
            end
        elseif v[2] == "consumable" then
            obj.AcquiredCount = obj.AcquiredCount + obj.Increment
        elseif AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
            print(string.format("onItem: unknown item type %s for code %s", v[2], v[1]))
        end
        AUTOTRACK_BUSY = false
    elseif AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
        print(string.format("onItem: could not find object for code %s", v[1]))
    end
    -- track local items via snes interface
    if is_local then
        if LOCAL_ITEMS[v[1]] then
            LOCAL_ITEMS[v[1]] = LOCAL_ITEMS[v[1]] + 1
        else
            LOCAL_ITEMS[v[1]] = 1
        end
    else
        if GLOBAL_ITEMS[v[1]] then
            GLOBAL_ITEMS[v[1]] = GLOBAL_ITEMS[v[1]] + 1
        else
            GLOBAL_ITEMS[v[1]] = 1
        end
    end
    if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
        print(string.format("local items: %s", dump_table(LOCAL_ITEMS)))
        print(string.format("global items: %s", dump_table(GLOBAL_ITEMS)))
    end
    if PopVersion < "0.20.1" or AutoTracker:GetConnectionState("SNES") == 3 then
        -- add snes interface functions here for local item tracking
    end
end

-- called when a location gets cleared
function onLocation(location_id, location_name)
    local location_array = LOCATION_MAPPING[location_id]
    if not location_array or not location_array[1] then
        print(string.format("onLocation: could not find location mapping for id %s", location_id))
        return
    end

    -- a cleared base photo also marks the Pokemon as photographed
    local dex = PHOTO_DEX and PHOTO_DEX[location_id]
    if dex then
        local d = Tracker:FindObjectForCode(dex)
        if d then d.Active = true end
    end

    for _, location in pairs(location_array) do
        local obj = Tracker:FindObjectForCode(location)
        -- print(location, obj)
        if obj then
            if location:sub(1, 1) == "@" then
                -- Bonus twins are random filler slots: a seed may include one for
                -- this check, or none at all. Both ids map here, so clear on the
                -- first and ignore a second rather than going negative.
                if obj.AvailableChestCount > 0 then
                    obj.AvailableChestCount = obj.AvailableChestCount - 1
                end
            else
                obj.Active = true
            end
        else
            print(string.format("onLocation: could not find object for code %s", location))
        end
    end
end

-- called when a locations is scouted
function onScout(location_id, location_name, item_id, item_name, item_player)
    if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
        print(string.format("called onScout: %s, %s, %s, %s, %s", location_id, location_name, item_id, item_name,
            item_player))
    end
    -- not implemented yet :(
end

-- called when a bounce message is received 
function onBounce(json)
    if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
        print(string.format("called onBounce: %s", dump_table(json)))
    end

    local data = json["data"]
    if data then
        if data["type"] == "MapUpdate" and data["mapId"] ~= nil and Tracker.UiHint then
            tabName = TAB_NAMES[data["mapId"] + 1] -- stupid Lua 1-indexed arrays
            if tabName then
                if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
                    print(string.format("activating tab: %s", tabName))
                end
                Tracker:UiHint("ActivateTab", tabName)
            end
        end
    end
end

-- newSectionIDToAPID values are lists (base photo + bonus twin), so send them all.
function sendSectionChecks(sectionID)
    local ids = newSectionIDToAPID[sectionID]
    if ids == nil then
        print(tostring(sectionID) .. " is not an AP location")
        return
    end
    if type(ids) ~= "table" then ids = {ids} end
    local res = Archipelago:LocationChecks(ids)
    if res then
        print("Sent " .. table.concat(ids, ", ") .. " for " .. tostring(sectionID))
    else
        print("Error sending " .. table.concat(ids, ", ") .. " for " .. tostring(sectionID))
    end
end

ScriptHost:AddOnLocationSectionChangedHandler("manual", function(section)
    local sectionID = section.FullID
    if sectionID == "Mew/Picture (Game Completion)" and section.AvailableChestCount == 0 then
        local res = Archipelago:StatusUpdate(Archipelago.ClientStatus.GOAL)
        if res then
            print("Sent Victory")
            local obj = Tracker:FindObjectForCode("complete")
            obj.Active = true
        else
            print("Error sending Victory")
        end
    elseif sectionID == "Release/Release/Click Here To !release Game" and section.AvailableChestCount == 0 then
        for _, ids in pairs(newSectionIDToAPID) do
            for _, apID in ipairs(ids) do
                onLocation(apID,"")
            end
        end
    elseif section.AvailableChestCount == 0 then
        -- section fully cleared: send every AP location it covers
        sendSectionChecks(section.FullID)
    end

    -- NOTE: the old Manual world had ONE check covering all courses for Bulbasaur,
    -- Zubat, Pikachu and Magikarp, so this handler used to mirror a cleared section
    -- onto its siblings. The native apworld gives each course its own location
    -- (e.g. Bulbasaur (River) = 1, Bulbasaur (Cave) = 64), so mirroring would clear
    -- checks the player has not actually done. Intentionally removed.

end)

-- add AP callbacks
-- un-/comment as needed
Archipelago:AddClearHandler("clear handler", onClear)
Archipelago:AddItemHandler("item handler", onItem)
Archipelago:AddLocationHandler("location handler", onLocation)
-- Archipelago:AddScoutHandler("scout handler", onScout)
Archipelago:AddBouncedHandler("bounce handler", onBounce)
