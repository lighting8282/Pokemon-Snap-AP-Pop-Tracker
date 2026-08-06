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
NEW_VERSION = false

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

-- The course items also jump to their map when clicked. They hold autotracked
-- state, so COURSE_OWNED shadows what the server has actually sent: a click
-- flips the toggle, we switch tabs and put the state straight back. This means
-- the course items cannot be toggled by hand - autotracking is the only thing
-- that sets them.
COURSE_OWNED = {}
JUMP_BUSY = false

for code, tab in pairs(COURSE_TABS) do
    ScriptHost:AddWatchForCode("coursewatch_" .. code, code, function(c)
        if JUMP_BUSY then return end
        local obj = Tracker:FindObjectForCode(c)
        if not obj then return end
        local owned = COURSE_OWNED[c] and true or false
        if obj.Active == owned then return end   -- autotracking, not a click
        JUMP_BUSY = true
        if Tracker.UiHint then
            Tracker:UiHint("ActivateTab", COURSE_TABS[c])
        end
        obj.Active = owned                       -- undo the click
        JUMP_BUSY = false
    end)
end

function onClear(slot_data)
    if AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
        print(string.format("called onClear, slot_data:\n%s", dump_table(slot_data)))
    end
    SLOT_DATA = slot_data
    CUR_INDEX = -1
    STARTING_TAB_SET = false
    COURSE_OWNED = {}

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
                    if COURSE_TABS[v[1]] then COURSE_OWNED[v[1]] = nil end
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
    
    -- The native "Pokemon Snap" apworld defines no options and sends empty slot_data.
    -- Every seed always contains the normal, wonderful and multiple photo checks, so
    -- both visibility toggles are simply turned on. NEW_VERSION selects the current
    -- (non-Manual) id tables further down.
    NEW_VERSION = true

    local obj = Tracker:FindObjectForCode("normal")
    if obj then obj.Active = true end

    obj = Tracker:FindObjectForCode("wonderful")
    if obj then obj.Active = true end

    LOCAL_ITEMS = {}
    GLOBAL_ITEMS = {}
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
        if v[2] == "toggle" then
            -- shadow first, so the watch reads this as autotracking not a click
            if COURSE_TABS[v[1]] then COURSE_OWNED[v[1]] = true end
            obj.Active = true
        elseif v[2] == "progressive" then
            if obj.Active then
                obj.CurrentStage = obj.CurrentStage + 1
            else
                if v[1] == "signpics" then
                    obj.CurrentStage = obj.CurrentStage + 1
                end
                obj.Active = true
            end
        elseif v[2] == "consumable" then
            obj.AcquiredCount = obj.AcquiredCount + obj.Increment
        elseif AUTOTRACKER_ENABLE_DEBUG_LOGGING_AP then
            print(string.format("onItem: unknown item type %s for code %s", v[2], v[1]))
        end
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
                obj.AvailableChestCount = obj.AvailableChestCount - 1
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
    elseif sectionID == "Release/Release/Click Here To !release Game" and section.AvailableChestCount == 0 and NEW_VERSION then
        for _, apID in pairs(newSectionIDToAPID) do
            if apID ~= nil then
                onLocation(apID,"")
            else
                print(tostring(sectionID) .. " is not an AP location")
            end
        end
    elseif sectionID == "Release/Release/Click Here To !release Game" and section.AvailableChestCount == 0 then
        for _, apID in pairs(oldSectionIDtoAPID) do
            if apID ~= nil then
                onLocation(apID,"")
            else
                print(tostring(sectionID) .. " is not an AP location")
            end
        end
    elseif (section.AvailableChestCount == 0) and NEW_VERSION then  -- this only works for 1 chest per section
        -- AP location cleared
        local sectionID = section.FullID
        local apID = newSectionIDToAPID[sectionID]
        if apID ~= nil then
            local res = Archipelago:LocationChecks({apID})
            if res then
                print("Sent " .. tostring(apID) .. " for " .. tostring(sectionID))
            else
                print("Error sending " .. tostring(apID) .. " for " .. tostring(sectionID))
            end
        else
            print(tostring(sectionID) .. " is not an AP location")
        end
    elseif (section.AvailableChestCount == 0) then  -- this only works for 1 chest per section
        -- AP location cleared
        local sectionID = section.FullID
        local apID = oldSectionIDtoAPID[sectionID]
        if apID ~= nil then
            local res = Archipelago:LocationChecks({apID})
            if res then
                print("Sent " .. tostring(apID) .. " for " .. tostring(sectionID))
            else
                print("Error sending " .. tostring(apID) .. " for " .. tostring(sectionID))
            end
        else
            print(tostring(sectionID) .. " is not an AP location")
        end
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
