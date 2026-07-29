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

-- 6 sign pictures all advance the signpics progressive
for id = 6000, 6005 do
    ITEM_MAPPING[id] = {"signpics","progressive"}
end



