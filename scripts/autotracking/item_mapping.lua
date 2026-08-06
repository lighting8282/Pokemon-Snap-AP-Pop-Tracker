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

    [3000] = {"film","consumable"},

    [10000] = {"complete","toggle"},
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
