-- Two versions of the items panel, picked by the seed's per_course_items.
--
-- With per_course_items the Apple, Pester Balls and PokeFlute are unlocked a
-- course at a time, and each course nameplate carries its three tool icons.
-- Without it those 21 icons can never light, so the panel drops them. Both
-- files define the same layout key, item_grid; loading one replaces the other
-- in the running tracker.
--
-- The percourseui toggle in the Settings popup holds the choice. Connecting
-- sets it from slot_data (see readOptionsFromSlotData); before that, or when
-- tracking by hand, it can be flipped manually, and it is saved with the rest
-- of the tracker state.
--
-- Loaded after Tracker:AddLayouts, so the per-course panel is already the
-- default and this only ever swaps.

ITEM_LAYOUTS = {
    [true]  = "layouts/item_grid_percourse.json",
    [false] = "layouts/item_grid_global.json",
}
local shown = true

function applyItemLayout()
    local obj = Tracker:FindObjectForCode("percourseui")
    local want = not obj or obj.Active
    if want ~= shown then
        shown = want
        Tracker:AddLayouts(ITEM_LAYOUTS[want])
    end
end

-- Set from slot_data on connect. Writing the toggle fires the watch below.
function setItemLayoutFromSeed(per_course)
    local obj = Tracker:FindObjectForCode("percourseui")
    if obj then obj.Active = per_course end
    applyItemLayout()
end

ScriptHost:AddWatchForCode("percourseui", "percourseui", applyItemLayout)
applyItemLayout()
