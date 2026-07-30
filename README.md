# Pokemon Snap PopTracker Pack

An auto-tracking [PopTracker](https://github.com/black-sliver/PopTracker) pack for the
[Pokemon Snap Archipelago world](https://github.com/nielrenned/PokemonSnap_Archipelago).

## Requirements

- **PopTracker 0.28.0** or newer
- **Pokemon Snap apworld `world_version` 0.4.0**

The apworld version matters. Location ids changed between 0.3.2 and 0.4.0 (signs moved to
400-405, poses to 301-312, and the three secret exits were added), so running this pack
against an older world will clear the wrong checks.

## Install

Drop `SnapTracker-<version>.zip` into your PopTracker `packs/` folder. There is no need to
unzip it — PopTracker reads packs straight out of the archive. Unpacked folders work too, if
you would rather edit the pack.

Then load the pack, choose **Main Tracker**, and connect to your Archipelago room with the
AP button.

## What it tracks

- **All 200 locations** — photos, Good Technique photos, Multiple photos, the 11 special
  poses, the 6 Pokemon Signs and the 3 secret exits
- **Items** — the six courses, Apple, Pester Ball, PokeFlute, Dash Engine, Pokemon Sign
  Detector, film capacity, and counters for Pokemon and Sign pictures
- **Logic** — access rules match the apworld's own rules, so a check shows as reachable
  exactly when Archipelago considers it reachable
- **Your starting course** — the randomly precollected course is detected on connect and its
  map tab is opened automatically

Checks use PopTracker's standard chest icons: closed while outstanding, open once submitted
to Prof. Oak.

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
- `location_mapping.lua` and `sectionID.lua` rebuilt against the apworld's 200 location ids,
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
