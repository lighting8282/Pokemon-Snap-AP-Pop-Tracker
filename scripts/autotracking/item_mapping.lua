ITEM_MAPPING = {
    [1000] = {"food","toggle"},
    [1001] = {"pester","toggle"},
    [1002] = {"flute","toggle"},
    [1003] = {"dash","toggle"},
    [1004] = {"sign","toggle"},

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

-- 63 Pokemon pictures all feed the single newpic counter
for id = 5000, 5062 do
    ITEM_MAPPING[id] = {"newpic","consumable"}
end

-- the six sign pictures, tracked individually so you can see which are missing
ITEM_MAPPING[6000] = {"signkingler","toggle"}   -- A Picture of Kingler Rock
ITEM_MAPPING[6001] = {"signpinsir","toggle"}   -- A Picture of Pinsir's Shadow
ITEM_MAPPING[6002] = {"signkoffing","toggle"}   -- A Picture of Koffing Smoke
ITEM_MAPPING[6003] = {"signcubone","toggle"}   -- A Picture of Cubone Tree
ITEM_MAPPING[6004] = {"signmewtwo","toggle"}   -- A Picture of The Mewtwo Constellation
ITEM_MAPPING[6005] = {"signdugtrio","toggle"}   -- A Picture of Dugtrio Mountain
