"""Show what the tracker would display for a given set of yaml options.

No yaml, no generation, no server, no emulator - it builds the location set the
world would produce and runs it through the same rule the tracker uses, so a
visibility change can be checked in about a second.

    python tools/test_options.py "A:/Archipelago/custom_worlds/pokemon_snap.apworld"
    python tools/test_options.py <apworld> --photo-bonuses none
    python tools/test_options.py <apworld> --no-signs --no-poses
    python tools/test_options.py <apworld> --rng-checks --hard-checks
    python tools/test_options.py <apworld> --all            # every combination

How it works: __init__.py drops a location when its category is not enabled, or
when it is in RNG_LOCATIONS / HARD_LOCATIONS and the matching option is off.
This mirrors exactly that, then applies the pack's own visibility rules - the
loc<id> flag per location, ANDed with the normal/wonderful/multiple toggles.

What it does NOT cover: it reasons about ids and rules, not pixels. It cannot
tell you a section renders wrong, only whether it should be shown.
"""
import sys, os, re, json, zipfile, tempfile, types, itertools, argparse
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent


def load_world(apworld):
    tmp = tempfile.mkdtemp(prefix="opt_")
    zipfile.ZipFile(apworld).extractall(tmp)
    root = os.path.join(tmp, "pokemon_snap")
    bc = types.ModuleType("BaseClasses")
    for n in ["Location", "Region", "Item", "MultiWorld", "Entrance",
              "Tutorial", "ItemClassification"]:
        setattr(bc, n, type(n, (object,), {"__init__": lambda self, *a, **k: None}))
    sys.modules["BaseClasses"] = bc
    open(os.path.join(root, "__init__.py"), "w").close()
    sys.path.insert(0, tmp)
    import importlib
    return importlib.import_module("pokemon_snap.locations")


def seed_locations(L, opts):
    """The ids the world would create, mirroring __init__.py's filter."""
    cats = {"NORMAL_PHOTO"}
    if opts["photo_bonuses"] == "technique_and_multiple":
        cats |= {"WONDERFUL_PHOTO", "MULTIPLE_PHOTO"}
    elif opts["photo_bonuses"] == "technique_only":
        cats |= {"WONDERFUL_PHOTO"}
    if opts["special_poses"]: cats.add("SPECIAL_POSE")
    if opts["pokemon_signs"]: cats.add("POKEMON_SIGN")
    if opts["secret_exits"]:  cats.add("SECRET_EXIT")

    ids = set()
    for table in L.location_tables.values():
        for d in table:
            if d.category.name == "BONUS_LOCATION":
                continue          # created at random per seed, not by option
            if d.category.name not in cats:
                continue
            if d.name in L.RNG_LOCATIONS and not opts["rng_checks"]:
                continue
            if d.name in L.HARD_LOCATIONS and not opts["hard_checks"]:
                continue
            ids.add(d.id)
    return ids


def pack_sections():
    """section -> (its ap id, its visibility rule)"""
    import lupa
    lua = lupa.LuaRuntime()
    lua.execute(open(PACK / "scripts/autotracking/location_mapping.lua", encoding="utf-8").read())
    lm = {int(k): list(v.values())[0].lstrip("@") for k, v in lua.globals().LOCATION_MAPPING.items()}
    sec_id = {s: i for i, s in lm.items() if i < 1000}

    out = {}
    for f in (PACK / "locations").rglob("*.json"):
        data = json.load(open(f, encoding="utf-8-sig"))
        def walk(node, pre=""):
            p = (pre + "/" + node.get("name", "")) if pre else node.get("name", "")
            for s in node.get("sections", []) or []:
                if "ref" in s:
                    continue
                full = p + "/" + s.get("name", "")
                if full in sec_id:
                    out[full] = (sec_id[full], s.get("visibility_rules") or [])
            for c in node.get("children", []) or []:
                walk(c, p)
        for node in (data if isinstance(data, list) else [data]):
            walk(node)
    return out


def visible(rule, present, toggles):
    """A rule is a single comma-separated AND list, e.g. 'multiple, loc223'."""
    for part in [x.strip() for x in rule.split(",")]:
        if part.startswith("loc"):
            if int(part[3:]) not in present:
                return False
        elif part in toggles and not toggles[part]:
            return False
    return True


def report(L, sections, opts, toggles, verbose):
    present = seed_locations(L, opts)
    shown, hidden = [], []
    for sec, (i, rules) in sections.items():
        ok = any(visible(r, present, toggles) for r in rules) if rules else True
        (shown if ok else hidden).append(sec)
    label = ", ".join(f"{k}={v}" for k, v in opts.items())
    print(f"\n{label}")
    print(f"    seed has {len(present)} locations   tracker shows {len(shown)}, hides {len(hidden)}")
    if len(present) != len(shown):
        print(f"    !! mismatch: {len(present)} in seed but {len(shown)} shown")
    if verbose and hidden:
        for h in sorted(hidden)[:12]:
            print(f"       hidden: {h}")
        if len(hidden) > 12:
            print(f"       ... and {len(hidden)-12} more")


DEFAULTS = dict(photo_bonuses="technique_and_multiple", special_poses=True,
                pokemon_signs=True, secret_exits=True, rng_checks=False, hard_checks=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apworld")
    ap.add_argument("--photo-bonuses", choices=["none", "technique_only", "technique_and_multiple"])
    ap.add_argument("--no-poses", action="store_true")
    ap.add_argument("--no-signs", action="store_true")
    ap.add_argument("--no-exits", action="store_true")
    ap.add_argument("--rng-checks", action="store_true")
    ap.add_argument("--hard-checks", action="store_true")
    ap.add_argument("--hide", default="", help="user toggles to turn off, e.g. wonderful,multiple")
    ap.add_argument("--all", action="store_true", help="run every option combination")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    L = load_world(a.apworld)
    sections = pack_sections()
    print(f"pack has {len(sections)} mapped sections")

    off = {x.strip() for x in a.hide.split(",") if x.strip()}
    toggles = {t: t not in off for t in ("normal", "wonderful", "multiple")}

    if a.all:
        for pb in ["none", "technique_only", "technique_and_multiple"]:
            for rng, hard in itertools.product([False, True], repeat=2):
                report(L, sections, dict(DEFAULTS, photo_bonuses=pb, rng_checks=rng, hard_checks=hard),
                       toggles, a.verbose)
        for flag in ["special_poses", "pokemon_signs", "secret_exits"]:
            report(L, sections, dict(DEFAULTS, **{flag: False}), toggles, a.verbose)
        return 0

    opts = dict(DEFAULTS)
    if a.photo_bonuses: opts["photo_bonuses"] = a.photo_bonuses
    if a.no_poses: opts["special_poses"] = False
    if a.no_signs: opts["pokemon_signs"] = False
    if a.no_exits: opts["secret_exits"] = False
    opts["rng_checks"] = a.rng_checks
    opts["hard_checks"] = a.hard_checks
    report(L, sections, opts, toggles, a.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
