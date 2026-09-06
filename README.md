# Pokemon Snap PopTracker Pack

An auto-tracking [PopTracker](https://github.com/black-sliver/PopTracker) pack for the
[Pokemon Snap Archipelago world](https://github.com/nielrenned/PokemonSnap_Archipelago).

## Requirements

- **PopTracker 0.28.0** or newer
- **Pokemon Snap apworld 0.4.0 or newer** (0.7.0 recommended)

Anything older used different location ids and will clear the wrong checks.

0.5.x seeds may also contain "bonus" locations - duplicates of random checks, created to hold
surplus items. Which ones exist varies per seed and a seed may have none. Both the base check
and its bonus twin map to the same entry here, which completes on whichever arrives first.

## Install

Drop `SnapTracker-<version>.zip` into your PopTracker `packs/` folder. There is no need to
unzip it — PopTracker reads packs straight out of the archive. Unpacked folders work too, if
you would rather edit the pack.

Then load the pack, choose **Main Tracker**, and connect to your Archipelago room with the
AP button.

## What it tracks

- **Every location** — photos, Good Technique photos, Multiple photos, the 11 special
  poses, the 6 Pokemon Signs, the 3 secret exits, the report score and photo count checks
  added in 0.6.0, plus the bonus duplicates a seed may generate
- **Only the checks your seed contains** — anything your yaml excluded is hidden, worked out
  from the seed's own location list rather than the options
- **The goal** — 0.6.0 makes the Rainbow Cloud requirement configurable (sign pictures or
  Pokemon pictures, and how many), read from slot data
- **Photo scoring** — 0.7.0 can lock Good Technique and Multiple PKMN behind items. Those
  are tracked, and Good Technique / Multiple checks stay out of logic until you have the
  matching unlock. Under `separate` scoring, Multiple no longer requires Good Technique
  first, and the checks that get cheaper are shown as such
- **Film capacity** — 0.7.0 makes film a logic requirement for 13 checks. The displayed
  capacity is derived from your yaml (`starting_film`, `film_upgrade_amount`,
  `maximum_film`) rather than assumed, so a low-film seed reads correctly
- **Map fragments** — with `map_fragments` at 2 or more a course unlocks from that many
  `<Course>: Map Fragment` items instead of one course item; the course lights up when you
  have enough
- **Items** — the six courses, Apple, Pester Ball, PokeFlute, Dash Engine, Pokemon Sign
  Detector, film capacity, and a count of the Pokemon pictures you have been sent
- **Logic** — access rules match the apworld's own rules, so a check shows as reachable
  exactly when Archipelago considers it reachable
- **Your starting course** — the randomly precollected course is detected on connect and its
  map tab is opened automatically
- **The current course** — the map follows you as you move between courses in game
- **A Pokedex tab** — all 63 Pokemon, greyed until you have photographed them
- **The six sign pictures** — tracked individually, so you can see which ones to hint for

Clicking a course item opens its map. Because those items carry autotracked state, they can
no longer be toggled by hand.

Each check shows a closed Pokeball while outstanding and an open one once it is done.

`tools/check_apworld.py` compares the pack against any apworld and reports new or stale
locations, broken section references, wrong-case image references and logic disagreements.
Run it whenever a new apworld is released.

Since 0.7.0 a location's logic depends on the yaml, so it checks the rules under several
option sets rather than one, and fails if it ever ends up comparing almost nothing — an
upstream restructure silently disabled that check twice before.

## Naming

The tracker groups checks under each Pokemon and labels them with the wording from the
original pack, which differs slightly from the names Archipelago uses:

| Tracker | Archipelago |
| --- | --- |
| `Charmeleon / Picture` | `Charmeleon` |
| `Charmeleon / Wonderful Picture` | `Charmeleon: Good Technique` |
| `Vulpix / Same Pkmn` | `Vulpix: Multiple` |
| `Magikarp / Valley Picture` | `Magikarp (Valley)` |
| `Pikachu / Surfing Pikachu` | `Surfing Pikachu` |
| `Tunnel / Secret Exit / Tunnel` | `Tunnel: Secret Exit` |

This only matters if you are typing location names by hand, for example
`/send_location <slot> Charmeleon: Good Technique`. Autotracking is keyed on ids, so the
wording has no effect on it.

## Origin

This pack started as [Fouton/SnapTracker](https://github.com/Fouton/SnapTracker), built for
the older `Manual_PokemonSnap_AliRobotnik` implementation, and has been ported to the native
`Pokemon Snap` apworld:

- `manifest.json` targets game `Pokemon Snap`
- `item_mapping.lua` rebuilt against the apworld's item ids (tools 1000-1004, courses
  2000-2005, film 3000, Pokemon pictures 5000-5062, sign pictures 6000-6005, victory 10000)
- `location_mapping.lua` and `sectionID.lua` rebuilt against the apworld's 400 location ids,
  and kept as exact inverses of each other
- access rules corrected against the apworld's `rules.py`
- locations that only existed in the Manual implementation were removed
- `archipelago.lua` no longer reads Manual-era slot data (the native world sends none) and no
  longer mirrors a cleared section onto sibling courses, since each course is its own location

## Credits

Original pack by **Fouton** — map art, layouts and location data come from that pack.
Ported and maintained by **lighting8282**.

Pokemon Snap is © Nintendo / Creatures Inc. / GAME FREAK inc. / HAL Laboratory. This is an
unofficial fan-made tracker, not affiliated with or endorsed by any of them.
