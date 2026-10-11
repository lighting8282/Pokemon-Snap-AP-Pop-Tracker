ITEM_MAPPING = {
    -- Apple and Pester Ball were renamed in apworld 0.8.0 ("Pokemon Food",
    -- "Pester Balls") but kept their ids, so these still match every version.
    [1000] = {"food","toggle"},
    [1001] = {"pester","toggle"},
    [1002] = {"flute","toggle"},
    [1003] = {"dash","toggle"},
    [1004] = {"sign","toggle"},

    -- apworld 0.8.0. pokemon_food_name picks which name the Apple ships under,
    -- and its default ("apples") uses this id, not 1000. Same item, same code.
    [1101] = {"food","toggle"},
    -- left_bumper_to_start_stop can put the ability in the pool. No logic
    -- depends on it; mapped so it is tracked rather than silently ignored.
    [1005] = {"lstop","toggle"},

    [2000] = {"beach","toggle"},
    [2001] = {"tunnel","toggle"},
    [2002] = {"volcano","toggle"},
    [2003] = {"river","toggle"},
    [2004] = {"cave","toggle"},
    [2005] = {"valley","toggle"},

    -- apworld 0.7.0 photo scoring. Only one of these exists in a given seed:
    -- separate_unlocks sends 1500/1501, progressive_unlocks sends 1502 twice.
    [1500] = {"wdflscore","toggle"},
    [1501] = {"multscore","toggle"},
    [1502] = {"progscore","consumable"},

    -- apworld 0.7.0 map fragments. Present instead of the plain course item
    -- when map_fragments is 2 or more; the course unlocks at that many.
    [2100] = {"fragbeach","consumable"},
    [2101] = {"fragtunnel","consumable"},
    [2102] = {"fragvolcano","consumable"},
    [2103] = {"fragriver","consumable"},
    [2104] = {"fragcave","consumable"},
    [2105] = {"fragvalley","consumable"},

    -- Counts upgrades rather than film. The displayed Film Capacity is derived
    -- from this in refreshDerivedItems(), because starting_film, the step and
    -- the cap are all per-seed since 0.7.0.
    [3000] = {"filmup","consumable"},

    [10000] = {"complete","toggle"},
}

-- course code -> its fragment counter, for the map_fragments unlock path
FRAGMENT_OF = {
    beach = "fragbeach", tunnel = "fragtunnel", volcano = "fragvolcano",
    river = "fragriver", cave  = "fragcave",   valley  = "fragvalley",
}

-- apworld 0.8.0 per_course_items: the Apple, Pester Balls and PokeFlute are
-- unlocked one course at a time. Ids follow 10<course><tool>, plus 11<course>0
-- for the Apple under its "Apples" name. The world's rule for a tool in a
-- course is "the global tool OR that course's copy", and only one kind ever
-- exists in a seed, so the generated access rules list both and need no
-- option check.
PER_COURSE_COURSES = {"beach", "tunnel", "volcano", "river", "cave", "valley", "cloud"}
PER_COURSE_TOOLS = {"food", "pester", "flute"}
for c, course in ipairs(PER_COURSE_COURSES) do
    for t, tool in ipairs(PER_COURSE_TOOLS) do
        ITEM_MAPPING[1000 + 10 * c + (t - 1)] = {tool .. "_" .. course, "toggle"}
    end
    ITEM_MAPPING[1100 + 10 * c] = {"food_" .. course, "toggle"}
end

-- Pokemon pictures all feed the single newpic counter: the 63 specific ones,
-- and since 0.8.0 the generic "Pokemon Picture" that goal_item_names: generic
-- (the default) hands out instead. Before this, a 0.8.0 seed never moved it.
for id = 5000, 5062 do
    ITEM_MAPPING[id] = {"newpic","consumable"}
end
ITEM_MAPPING[5500] = {"newpic","consumable"}

-- the six sign pictures, tracked individually so you can see which are missing
ITEM_MAPPING[6000] = {"signkingler","toggle"}   -- Sign Picture: Kingler Rock
ITEM_MAPPING[6001] = {"signpinsir","toggle"}    -- Sign Picture: Pinsir's Shadow
ITEM_MAPPING[6002] = {"signkoffing","toggle"}   -- Sign Picture: Koffing Smoke
ITEM_MAPPING[6003] = {"signcubone","toggle"}    -- Sign Picture: Cubone Tree
ITEM_MAPPING[6004] = {"signmewtwo","toggle"}    -- Sign Picture: The Mewtwo Constellation
ITEM_MAPPING[6005] = {"signdugtrio","toggle"}   -- Sign Picture: Dugtrio Mountain
-- The generic "Sign Picture" (0.8.0 default) does not say which sign it is.
-- onItem counts it and lights the sign icons in order; see countSignPicture.
ITEM_MAPPING[6500] = {"signcount","consumable"}

-- Every sign picture, specific or generic, also counts towards the goal. The
-- world's goal is HasGroup over the whole group, so duplicates and generic
-- copies count too - counting lit icons would undercount both.
SIGN_PICTURE_IDS = {}
for id = 6000, 6005 do SIGN_PICTURE_IDS[id] = true end
SIGN_PICTURE_IDS[6500] = true
SIGN_ORDER = {"signkingler", "signpinsir", "signkoffing", "signcubone", "signmewtwo", "signdugtrio"}
