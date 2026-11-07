"""Add posesanity's pose checks to the pack and regenerate the id mappings.

apworld 0.9.0 added posesanity: up to 141 "regular" poses - the lines Oak says
about a photo that are not one of the eleven Special Poses - each a check of
its own. A seed picks a random subset, so the pack carries all of them and
shows only the ones the seed contains, like every other check.

    python tools/make_poses.py "path/to/pokemon_snap.apworld"
    python tools/make_logic.py "path/to/pokemon_snap.apworld"     # then this

It writes, idempotently:

    locations/pokemon/<species>.json   a section per pose, under its Pokemon,
                                       named after Oak's line:
                                           Pose: It's pretty funny.
                                       or, for a Pokemon on several courses,
                                           Valley Pose: It splashed!
    locations/<course>.json            a ref to each, on that Pokemon's pin,
                                       so poses show on the course map
    items/settings.json                a hidden loc<id> flag per pose (off
                                       until the seed says it contains it)
    scripts/autotracking/location_mapping.lua, sectionID.lua, dex_mapping.lua
                                       rebuilt from the world's location
                                       table, keeping every existing section

Bonus twins. 0.9.0 moved a check's bonus duplicate from id + 1000 to
id + 1,000,000, to make room for pose ids (100000 + 1000 * slot + pose). Both
are mapped: a game generated on 0.8.0 or older still sends the old ids, and
neither range collides with anything in the other version.

Access rules are left empty here; make_logic.py compiles them from the world.
"""
import sys, json, re, importlib, importlib.util
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent

COURSE_FILE = {"Beach": "beach", "Tunnel": "tunnel", "Volcano": "volcano",
               "River": "river", "Cave": "cave", "Valley": "valley",
               "Rainbow Cloud": "oakmew"}
LEVEL_ORDER = ["Beach", "Tunnel", "Volcano", "River", "Cave", "Valley",
               "Rainbow Cloud"]

LEGACY_BONUS = 1_000          # bonus twin offset up to apworld 0.8.0
BONUS = 1_000_000             # and from 0.9.0


def is_base(i):
    """A check's own id, as opposed to one of its bonus twins."""
    return i < LEGACY_BONUS or 100_000 <= i < BONUS


def load():
    spec = importlib.util.spec_from_file_location("_check", PACK / "tools" / "check_apworld.py")
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    version, locs, items, root = check.load_apworld(sys.argv[1])
    L = importlib.import_module("pokemon_snap.locations")
    return version, L


def read_mapping():
    txt = (PACK / "scripts/autotracking/location_mapping.lua").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"\[(\d+)\]\s*=\s*\{\"@([^\"]+)\"", txt):
        out[int(m.group(1))] = m.group(2)
    return out


def jload(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def jsave(p, data):
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    version, L = load()
    old = read_mapping()

    # every location the world defines: id -> (name, category, level)
    world = {}
    for level, table in L.location_tables.items():
        for d in table:
            if is_base(d.id):
                world[d.id] = (d.name, d.category.name, str(level))

    # Base sections the pack already has keep their paths. Anything new that is
    # not a pose has no section to point at, which is a real gap: stop.
    path = {i: old[i] for i in world if i in old}
    poses = sorted(i for i, (_, cat, _) in world.items() if cat == "REGULAR_POSE")
    unknown = sorted(i for i in world if i not in path and i not in poses)
    if unknown:
        print("!! new non-pose locations with no section in the pack:")
        for i in unknown:
            print(f"     {i} {world[i][0]}")
        return 1

    pokemon_files = {jload(f)[0]["name"]: f for f in (PACK / "locations/pokemon").glob("*.json")}
    edits = {}                     # file -> parsed json, written once at the end

    def doc(f):
        if f not in edits:
            edits[f] = jload(f)
        return edits[f]

    new_flags = []
    for pid in poses:
        name, _, level = world[pid]
        species, phrase = name.split(" Pose: ", 1)
        # Oak's line without the quotes the world puts round it: a '"' in a
        # section name would need escaping in the Lua tables, which the tools
        # here read with plain regexes
        phrase = phrase.strip('"')
        normal = path[L.POKEMON_NAME_TO_ID[species]]          # e.g. Magikarp/Valley Picture
        owner, normal_section = normal.split("/", 1)
        prefix = normal_section[:-len("Picture")] if normal_section.endswith("Picture") else ""
        section = f"{prefix}Pose: {phrase}"
        path[pid] = f"{owner}/{section}"

        # the section itself, under the Pokemon
        node = doc(pokemon_files[owner])[0]
        secs = node.setdefault("sections", [])
        if not any(s.get("name") == section for s in secs):
            secs.append({"name": section, "visibility_rules": [f"loc{pid}"], "access_rules": []})

        # a ref on the course map, on whichever pin already shows this Pokemon
        cdoc = doc(PACK / "locations" / f"{COURSE_FILE[level]}.json")
        pin = None

        def find(n):
            nonlocal pin
            for s in n.get("sections", []) or []:
                if s.get("ref") == normal:
                    pin = n
            for c in n.get("children", []) or []:
                find(c)
        for n in cdoc:
            find(n)
        if pin is None:
            print(f"!! no pin on the {level} map shows {normal}")
            return 1
        ref_name = f"Pose: {phrase}"
        if not any(s.get("ref") == path[pid] for s in pin["sections"]):
            pin["sections"].append({"name": ref_name, "ref": path[pid]})

        new_flags.append(pid)

    # hidden per-location flags; poses start off, as a seed has none by default
    sdoc = doc(PACK / "items/settings.json")
    have = {it.get("codes") for it in sdoc}
    for pid in new_flags:
        if f"loc{pid}" not in have:
            sdoc.append({"name": f"seed contains location {pid}", "type": "toggle",
                         "codes": f"loc{pid}", "initial_active_state": False})

    for f, data in edits.items():
        jsave(f, data)

    # ---- location_mapping.lua / sectionID.lua, rebuilt from the world ----
    def twins(i):
        out = [i]
        if i < LEGACY_BONUS:
            out.append(i + LEGACY_BONUS)
        out.append(i + BONUS)
        return out

    by_level = {}
    for i, (name, cat, level) in world.items():
        by_level.setdefault(level, []).append(i)
    # Oak's rewards live in the world's starting region, whatever it is called;
    # never drop a level just because it is missing from LEVEL_ORDER
    levels = [lv for lv in LEVEL_ORDER if lv in by_level] + \
             [lv for lv in by_level if lv not in LEVEL_ORDER]
    title = {lv: "Oak's Lab" for lv in by_level if lv not in COURSE_FILE}
    cat_order = {"NORMAL_PHOTO": 0, "WONDERFUL_PHOTO": 1, "MULTIPLE_PHOTO": 2, "SPECIAL_POSE": 3,
                 "POKEMON_SIGN": 4, "SECRET_EXIT": 5, "REGULAR_POSE": 6,
                 "REPORT_SCORE": 7, "PHOTO_COUNT": 8}

    lm = ["-- AP location id -> PopTracker section",
          f"-- Generated by tools/make_poses.py from Pokemon Snap apworld {version}.",
          "--",
          "-- Each check may also have a \"bonus\" duplicate, created as a filler slot:",
          "-- id + 1,000,000 from apworld 0.9.0, id + 1000 before it. Both are mapped so",
          "-- games generated on either still track. A twin points at the same section,",
          "-- which completes on whichever arrives first.",
          "LOCATION_MAPPING = {"]
    sid = ["-- PopTracker section -> the AP location ids it covers (the check and its bonus twins).",
           f"-- Generated by tools/make_poses.py from Pokemon Snap apworld {version}.",
           "newSectionIDToAPID = {"]
    for level in levels:
        ids = sorted(by_level.get(level, []), key=lambda i: (cat_order[world[i][1]], i))
        if not ids:
            continue
        lm += ["", f"    -- {title.get(level, level)}"]
        sid += ["", f"    -- {title.get(level, level)}"]
        for i in ids:
            p = lua_str("@" + path[i])
            for t in twins(i):
                note = world[i][0] + ("" if t == i else " 2")
                lm.append(f"    [{t}] = {{{p}}}, -- {note}")
            sid.append(f"    [{lua_str(path[i])}] = {{{', '.join(str(t) for t in twins(i))}}},")
    lm.append("}")
    sid.append("}")
    (PACK / "scripts/autotracking/location_mapping.lua").write_text("\n".join(lm) + "\n", encoding="utf-8")
    (PACK / "scripts/autotracking/sectionID.lua").write_text("\n".join(sid) + "\n", encoding="utf-8")

    # ---- dex_mapping.lua: a bonus twin of a base photo marks the Pokemon too ----
    dpath = PACK / "scripts/autotracking/dex_mapping.lua"
    dtxt = dpath.read_text(encoding="utf-8")
    dex = {}
    for m in re.finditer(r"\[(\d+)\]\s*=\s*\"([^\"]+)\"", dtxt):
        i = int(m.group(1))
        if i < LEGACY_BONUS:
            dex[i] = m.group(2)
    head = dtxt.split("PHOTO_DEX = {")[0]
    rows = []
    for i, code in sorted(dex.items(), key=lambda kv: (kv[1], kv[0])):
        for t in twins(i):
            rows.append(f"    [{t}] = \"{code}\",")
    dpath.write_text(head + "PHOTO_DEX = {\n" + "\n".join(rows) + "\n}\n", encoding="utf-8")

    print(f"apworld {version}: {len(poses)} poses, {len(world)} checks, "
          f"{sum(len(twins(i)) for i in world)} ids mapped")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main())
