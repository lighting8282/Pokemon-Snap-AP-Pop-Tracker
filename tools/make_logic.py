"""Generate every photo, pose, sign and secret-exit access rule from an apworld.

Up to apworld 0.7.0 the access rules were written by hand and checked against
the world. 0.8.0 threaded two new options through almost every rule - hard
logic, and per-course Apple / Pester Ball / PokeFlute unlocks - which made
hand-editing a few hundred rules the riskiest way to keep up. So the rules are
now compiled straight from the world's own LOCATION_RULES table.

    python tools/make_logic.py "path/to/pokemon_snap.apworld"

What it writes, per section:

    <course code>          region access; Mew uses $goal_unlocked instead
    $can_wonderful         ANDed on Good Technique photos, as set_rules() does
    $can_multiple          ANDed on Multiple photos, likewise
    tool codes             food / pester / flute / dash / sign, and the
                           per-course copies food_beach, pester_cave, ...
    $has_film|N            film capacity of at least N
    $separate_scoring      photo_scoring is separate or separate_unlocks
    $rng_checks_on         rng_checks is on
    $hard_logic_on         hard_logic is on

The world's has(tool, course) is "the global tool OR that course's copy".
Only one kind ever exists in a seed, so listing both as alternatives is right
in either mode without the rule needing to know which mode it is in.

Oak's rewards are left alone: they are not item requirements and oak.lua
answers them. check_apworld.py independently re-derives the world's rules and
compares, so a bug here shows up there rather than being trusted.
"""
import sys, json, re, importlib, importlib.util
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent

COURSE_CODE = {"Beach": "beach", "Tunnel": "tunnel", "Volcano": "volcano",
               "River": "river", "Cave": "cave", "Valley": "valley",
               "Rainbow Cloud": "cloud"}
REGION = {"Beach": "beach", "Tunnel": "tunnel", "Volcano": "volcano",
          "River": "river", "Cave": "cave", "Valley": "valley",
          "Rainbow Cloud": "$goal_unlocked"}

# item name -> pack code. Names, not constants: the world renamed Apple and
# Pester Ball in 0.8.0 and both spellings are accepted here.
TOOL_CODE = {
    "Pester Ball": "pester", "Pester Balls": "pester",
    "Apple": "food", "Apples": "food", "Pokemon Food": "food",
    "PokeFlute": "flute", "Dash Engine": "dash", "Pokemon Sign Detector": "sign",
}

COMPILED = {"NORMAL_PHOTO", "WONDERFUL_PHOTO", "MULTIPLE_PHOTO",
            "SPECIAL_POSE", "POKEMON_SIGN", "SECRET_EXIT"}

FREE = frozenset()


def item_code(name):
    if name in TOOL_CODE:
        return TOOL_CODE[name]
    m = re.match(r"^(.*) \((.*)\)$", name)          # "Pester Balls (Cave)"
    if m and m.group(1) in TOOL_CODE and m.group(2) in COURSE_CODE:
        return TOOL_CODE[m.group(1)] + "_" + COURSE_CODE[m.group(2)]
    raise ValueError(f"no pack code for item {name!r}")


def option_token(rule):
    which = getattr(rule.args[0], "__name__", str(rule.args[0])) if rule.args else ""
    if "PhotoScoring" in which:
        return "$separate_scoring"
    if "RNG" in which:
        return "$rng_checks_on"
    if "HardLogic" in which:
        return "$hard_logic_on"
    raise ValueError(f"unknown option filter {which!r}")


def minimal(sets):
    return {a for a in sets if not any(b < a for b in sets)}


def dnf(rule):
    """Rule object -> set of alternative token sets. Empty set = unreachable."""
    k = type(rule).__name__
    if k == "True_":
        return {FREE}
    if k == "False_":
        return set()
    if k == "Has":
        return {frozenset({item_code(rule.args[0])})}
    if k == "HasAny":
        return {frozenset({item_code(a)}) for a in rule.args}
    if k == "HasAll":
        return {frozenset(item_code(a) for a in rule.args)}
    if k == "HasFilm":
        return {frozenset({f"$has_film|{rule.film_requirement}"})}
    if k == "OptionFilter":
        return {frozenset({option_token(rule)})}
    if k in ("And", "list"):
        acc = {FREE}
        for sub in (rule if k == "list" else rule.args):
            acc = {a | b for a in acc for b in dnf(sub)}
        return minimal(acc)
    if k == "Or":
        acc = set()
        for sub in rule.args:
            acc |= dnf(sub)
        return minimal(acc)
    raise ValueError(f"cannot compile rule type {k}")


def branch_order(tok):
    # region first, then scoring, then the rest alphabetically: stable output
    if tok in REGION.values():
        return (0, tok)
    if tok in ("$can_wonderful", "$can_multiple"):
        return (1, tok)
    return (2, tok)


def main(apworld):
    spec = importlib.util.spec_from_file_location("_check", PACK / "tools" / "check_apworld.py")
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    version, locs, items, root = check.load_apworld(apworld)
    check._stub_rule_builder()
    L = importlib.import_module("pokemon_snap.locations")
    R = importlib.import_module("pokemon_snap.rules")

    # id -> (category, level)
    meta = {}
    for level, table in L.location_tables.items():
        for d in table:
            meta[d.id] = (d.category.name, str(level))

    # AP location name -> its rule, as set_rules() would apply it
    rule_for = {}
    for name, cats in R.LOCATION_RULES.items():
        for cat, rule in cats.items():
            rule_for[R.location_name(name, cat)] = rule

    lm = {}
    txt = (PACK / "scripts/autotracking/location_mapping.lua").read_text(encoding="utf-8")
    for m in re.finditer(r"\[(\d+)\]\s*=\s*\{\"@([^\"]+)\"", txt):
        lm[int(m.group(1))] = m.group(2)

    want = {}                                      # section path -> rule list
    for lid, (cat, level) in sorted(meta.items()):
        if lid >= 1000 or cat not in COMPILED or lid not in lm:
            continue
        rule = rule_for.get(locs[lid])
        alts = dnf(rule) if rule is not None else {FREE}
        if not alts:
            raise ValueError(f"{locs[lid]} compiles to unreachable")
        head = [REGION[level]]
        if cat == "WONDERFUL_PHOTO":
            head.append("$can_wonderful")
        if cat == "MULTIPLE_PHOTO":
            head.append("$can_multiple")
        branches = sorted(", ".join(sorted(head + sorted(a), key=branch_order))
                          for a in alts)
        want[lm[lid]] = branches

    changed, touched_files, found = 0, 0, set()
    for f in sorted(PACK.glob("locations/**/*.json")):
        data = json.loads(f.read_text(encoding="utf-8-sig"))
        dirty = False

        def walk(node, pre=""):
            nonlocal dirty, changed
            p = (pre + "/" + node.get("name", "")) if pre else node.get("name", "")
            for s in node.get("sections", []) or []:
                if "ref" in s:
                    continue
                key = p + "/" + s.get("name", "")
                if key in want:
                    found.add(key)
                if key in want and s.get("access_rules") != want[key]:
                    s["access_rules"] = want[key]
                    dirty = True
                    changed += 1
            for c in node.get("children", []) or []:
                walk(c, p)

        for node in (data if isinstance(data, list) else [data]):
            walk(node)
        if dirty:
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            touched_files += 1

    print(f"apworld {version}: {len(want)} sections compiled, "
          f"{changed} changed across {touched_files} files")
    # a mapped location whose section does not exist would silently keep no
    # rule at all, so treat it as a failure rather than a quiet skip
    missing = sorted(set(want) - found)
    if missing:
        print(f"!! {len(missing)} mapped section(s) not found in locations/:")
        for m in missing:
            print("     " + m)
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
