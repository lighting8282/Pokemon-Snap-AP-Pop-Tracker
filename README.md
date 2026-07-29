# Pokemon Snap PopTracker Pack

A PopTracker pack for the native [Pokemon Snap Archipelago world](https://github.com/nielrenned/PokemonSnap_Archipelago).

Targets apworld **world_version 0.4.0**.

## Origin

This pack started as [Fouton/SnapTracker](https://github.com/Fouton/SnapTracker), which was
built for the older `Manual_PokemonSnap_AliRobotnik` implementation. It has been ported to the
native `Pokemon Snap` apworld:

- `manifest.json` targets game `Pokemon Snap`
- `item_mapping.lua` rebuilt against the apworld's item ids (tools 1000-1004, courses
  2000-2005, film 3000, Pokemon pictures 5000-5062, sign pictures 6000-6005, victory 10000)
- `location_mapping.lua` and `sectionID.lua` rebuilt against the apworld's 200 location ids
  and kept as exact inverses of each other
- `archipelago.lua` no longer reads Manual-era slot data, and no longer mirrors a cleared
  section onto sibling courses (each course is its own location in the native world)
- the map tab for the randomly precollected starting course is opened automatically on connect

## Install

Clone or unzip into your PopTracker `packs/` directory. PopTracker loads unpacked folders
directly, so no zipping is needed for local use.

## Known gaps

Five locations remain in the pack that the apworld does not define, and will never clear:

- `Oak's Lab & Rainbow Cloud/New Pokemon Pics/Count: 6` / `Count: 22` / `Count: 40`
- `Oak's Lab & Rainbow Cloud/Sign Detector/Reward`
- `Mew/Rare Pokemon`

Some access rules are also more permissive than the apworld's logic, so a few checks may show
as reachable slightly early.

## Credits

Original pack by Fouton. Map art, layouts and location data are from that pack.
