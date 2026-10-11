-- Access-rule helpers for the options apworld 0.7.0 added.
--
-- Three things stopped being constants in 0.7.0:
--
--   photo_scoring   Good Technique and Multiple can be locked behind items
--   starting_film   film capacity is a logic requirement for 13 checks
--   map_fragments   a course can need N fragments instead of one course item
--
-- All of them arrive in slot_data, so these read the values archipelago.lua
-- parked in globals. The defaults below are the apworld's own defaults, which
-- is what an unconnected tracker and a default yaml both look like.

-- photo_scoring: 0 vanilla, 1 separate, 2 progressive_unlocks, 3 separate_unlocks
PHOTO_SCORING = PHOTO_SCORING or 0

FILM_START = FILM_START or 15
FILM_STEP  = FILM_STEP  or 5
FILM_CAP   = FILM_CAP   or 60

MAP_FRAGMENTS = MAP_FRAGMENTS or 1
RNG_CHECKS    = RNG_CHECKS    or 0

local function count(code)
    return Tracker:ProviderCountForCode(code) or 0
end

-- Good Technique scoring. Free unless the seed locks it behind an item.
function can_wonderful()
    if PHOTO_SCORING == 2 then return count("progscore") >= 1 and 1 or 0 end
    if PHOTO_SCORING == 3 then return count("wdflscore") >= 1 and 1 or 0 end
    return 1
end

-- Multiple PKMN scoring. progressive_unlocks needs the second copy.
function can_multiple()
    if PHOTO_SCORING == 2 then return count("progscore") >= 2 and 1 or 0 end
    if PHOTO_SCORING == 3 then return count("multscore") >= 1 and 1 or 0 end
    return 1
end

-- True when Multiple can be scored without first earning Good Technique,
-- which is what makes a handful of Multiple checks cheaper than they look.
function separate_scoring()
    return (PHOTO_SCORING == 1 or PHOTO_SCORING == 3) and 1 or 0
end

function rng_checks_on()
    return RNG_CHECKS ~= 0 and 1 or 0
end

-- Total film capacity, mirroring the apworld:
--     min(cap, start + upgrades * step)
function film_capacity()
    local total = FILM_START + count("filmup") * FILM_STEP
    if total > FILM_CAP then total = FILM_CAP end
    return total
end

-- Access rules call this as $has_film|5. PopTracker passes rule arguments
-- as strings, hence tonumber. apworld 0.8.0's hard logic added thresholds of
-- 2 and 3 to the existing 4, 5, 7 and 9, so a single function with an
-- argument replaced the one-function-per-threshold names below, which stay
-- only so an older layout of the rules still resolves.
function has_film(n)
    n = tonumber(n) or 0
    return film_capacity() >= n and 1 or 0
end

-- apworld 0.8.0 hard_logic: about a dozen checks come into logic earlier,
-- some with lower film requirements. Off unless slot_data turns it on.
HARD_LOGIC = HARD_LOGIC or 0
function hard_logic_on()
    return (HARD_LOGIC ~= 0) and 1 or 0
end

function has_film_4() return has_film(4) end
function has_film_5() return has_film(5) end
function has_film_7() return has_film(7) end
function has_film_9() return has_film(9) end

-- A course counts as unlocked on either the plain course item or enough map
-- fragments. archipelago.lua sets the course toggle when the fragments land,
-- so the existing course codes in access rules keep working untouched; this
-- is here for the item handler to call.
function fragments_satisfy(course_code)
    local frag = FRAGMENT_OF and FRAGMENT_OF[course_code]
    if not frag then return false end
    return count(frag) >= MAP_FRAGMENTS
end
