"""Compare a Pokemon Snap .apworld against this tracker pack.

Run this whenever a new apworld is released, before touching anything:

    python tools/check_apworld.py "A:/Archipelago/custom_worlds/pokemon_snap.apworld"

It reports four things, in the order they matter:

  1. locations the world has that the tracker does not map    -> new checks
  2. locations the tracker maps that the world does not have   -> stale checks
  3. tracker sections that no longer exist in the pack         -> broken mapping
  4. access rules that disagree with the world's rules.py      -> wrong logic

Exit code is 0 when everything agrees, 1 otherwise, so it can gate a release.

Only needs the standard library. The Lua files are generated with a fixed
shape, so they are read with regexes rather than a Lua runtime.
"""
import sys, os, re, json, zipfile, tempfile, types, importlib.util
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
COURSES = {"beach", "tunnel", "volcano", "river", "cave", "valley", "rainbow"}
TOOLS = {"pester", "food", "flute", "dash", "sign", "allsigns"}


# ---------------------------------------------------------------- apworld ---

def load_apworld(path):
    """Extract the apworld and import its tables with a stubbed BaseClasses."""
    tmp = tempfile.mkdtemp(prefix="apworld_")
    zipfile.ZipFile(path).extractall(tmp)
    root = os.path.join(tmp, "pokemon_snap")

    # BaseClasses only needs to exist; nothing here constructs a real world.
    bc = types.ModuleType("BaseClasses")
    for n in ["Location", "Region", "Item", "MultiWorld", "Entrance",
              "Tutorial", "ItemClassification"]:
        setattr(bc, n, type(n, (object,), {"__init__": lambda self, *a, **k: None}))
    sys.modules["BaseClasses"] = bc

    # addresses.py reads its symbol table via importlib.resources, which needs a
    # genuine package on sys.path. Blank the world's __init__ so importing the
    # package does not drag in worlds.AutoWorld and the rest of Archipelago.
    open(os.path.join(root, "__init__.py"), "w").close()
    sys.path.insert(0, tmp)

    import importlib
    L = importlib.import_module("pokemon_snap.locations")
    I = importlib.import_module("pokemon_snap.items")
    version = json.load(open(os.path.join(root, "archipelago.json"),
                             encoding="utf-8-sig"))["world_version"]

    locs, items = {}, {}
    for table in L.location_tables.values():
        for d in table:
            locs[d.id] = d.name
    for it in I._all_items:
        items[it.ps_code] = it.name
    return version, locs, items, os.path.join(root, "rules.py")


ALIAS = {"_HAS_PESTER": [{"pester"}], "_HAS_APPLE": [{"food"}],
         "_HAS_FLUTE": [{"flute"}],
         "_HAS_APPLE_OR_PESTER": [{"pester"}, {"food"}]}
CONST = {"PESTER_BALL": "pester", "POKEMON_FOOD": "food", "POKEFLUTE": "flute",
         "DASH_ENGINE": "dash", "SIGN_DETECTOR": "sign"}
SIGNS = {"BEACH_SIGN": "Kingler Rock", "TUNNEL_SIGN": "Pinsir's Shadow",
         "VOLCANO_SIGN": "Koffing Smoke", "RIVER_SIGN": "Cubone Tree",
         "CAVE_SIGN": "The Mewtwo Constellation", "VALLEY_SIGN": "Dugtrio Mountain"}
LVL = {"LVL_TUNNEL": "Tunnel", "LVL_RIVER": "River", "LVL_VALLEY": "Valley"}


def dnf(expr):
    """Turn a rule_builder expression into a set of alternative requirement sets."""
    expr = expr.strip().rstrip(")")
    if expr in ALIAS:
        return {frozenset(s) for s in ALIAS[expr]}
    toks = [CONST[t] for t in re.findall(r"\b([A-Z_]+)\b", expr) if t in CONST]
    if expr.startswith("HasAny"):
        return {frozenset({t}) for t in toks}
    if expr.startswith("HasAll"):
        return {frozenset(toks)}
    if expr.startswith("Has("):
        return {frozenset({toks[0]})} if toks else None
    if expr.startswith("And("):
        acc = {frozenset()}
        for part in re.split(r",\s*(?![^()]*\))", expr[4:]):
            sub = dnf(part)
            if not sub:
                return None
            acc = {a | b for a in acc for b in sub}
        return acc
    return None


def parse_rules(path):
    src = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"world\.set_rule\(world\.get_location\((.+?)\),\s*(.+?)\)\n", src):
        loc, rule = m.group(1).strip(), m.group(2).strip()
        lm = re.match(r'^(wdfl|mult)\("(.+?)"\)$', loc)
        if lm:
            name = lm.group(2) + (": Good Technique" if lm.group(1) == "wdfl" else ": Multiple")
        elif loc.startswith("secret_exit("):
            name = LVL.get(loc[12:-1], loc) + ": Secret Exit"
        elif loc.startswith('"'):
            name = loc.strip('"')
        else:
            name = SIGNS.get(loc, loc)
        d = dnf(rule)
        if d:
            out[name] = d
    return out


# ------------------------------------------------------------------- pack ---

def load_pack():
    lm, sm, im = {}, {}, {}
    txt = open(PACK / "scripts/autotracking/location_mapping.lua", encoding="utf-8").read()
    for m in re.finditer(r"\[(\d+)\]\s*=\s*\{([^}]*)\}", txt):
        lm[int(m.group(1))] = re.findall(r'"([^"]+)"', m.group(2))
    txt = open(PACK / "scripts/autotracking/sectionID.lua", encoding="utf-8").read()
    head = txt.split("oldSectionIDtoAPID")[0]
    for m in re.finditer(r'\["([^"]+)"\]\s*=\s*(\d+)', head):
        sm[m.group(1)] = int(m.group(2))
    txt = open(PACK / "scripts/autotracking/item_mapping.lua", encoding="utf-8").read()
    for m in re.finditer(r'\[(\d+)\]\s*=\s*\{"([^"]+)"', txt):
        im[int(m.group(1))] = m.group(2)
    for m in re.finditer(r"for id\s*=\s*(\d+),\s*(\d+) do\s*\n\s*ITEM_MAPPING\[id\]\s*=\s*\{\"([^\"]+)\"", txt):
        for i in range(int(m.group(1)), int(m.group(2)) + 1):
            im[i] = m.group(3)

    sections = {}
    for f in (PACK / "locations").rglob("*.json"):
        data = json.load(open(f, encoding="utf-8-sig"))
        def walk(node, pre=""):
            p = (pre + "/" + node.get("name", "")) if pre else node.get("name", "")
            for s in node.get("sections", []) or []:
                if "ref" not in s:
                    sections[p + "/" + s.get("name", "")] = s.get("access_rules", [])
            for c in node.get("children", []) or []:
                walk(c, p)
        for node in (data if isinstance(data, list) else [data]):
            walk(node)
    return lm, sm, im, sections


def tracker_dnf(rules):
    """Reduce a section's access_rules to alternative tool requirement sets.

    Course codes are dropped (the world models those as region access), rules
    in {} are 'checkable but not collectible', and [] marks an optional rule.
    """
    out = set()
    for r in rules:
        parts = [x.strip() for x in r.split(",")]
        if any(p.startswith("{") for p in parts):
            continue
        opts, ok = [[]], True
        for p in parts:
            if p.startswith("[") and p.endswith("]"):
                continue
            if p in COURSES or not p:
                continue
            if p == "@Logic/Throwable":
                opts = [o + [t] for o in opts for t in ("pester", "food")]
                continue
            if p in TOOLS:
                opts = [o + [p] for o in opts]
                continue
            ok = False
            break
        if ok:
            out.update(frozenset(o) for o in opts)
    return {a for a in out if not any(b < a for b in out)}


def show(d):
    return " OR ".join("+".join(sorted(x)) or "(free)" for x in sorted(d, key=sorted)) or "(free)"


# ------------------------------------------------------------------- main ---

def main(apworld):
    version, locs, items, rules_py = load_apworld(apworld)
    rules = parse_rules(rules_py)
    lm, sm, im, sections = load_pack()
    pack_version = json.load(open(PACK / "manifest.json", encoding="utf-8-sig"))["package_version"]

    print(f"apworld world_version {version}   |   pack {pack_version}")
    print(f"world: {len(locs)} locations, {len(items)} items"
          f"   |   pack maps {len(lm)} locations, {len(im)} items\n")
    problems = 0

    new = sorted(set(locs) - set(lm))
    if new:
        problems += len(new)
        print(f"[1] {len(new)} location(s) in the world are NOT mapped by the tracker:")
        for i in new:
            print(f"      {i:<6} {locs[i]}")
        print()

    stale = sorted(set(lm) - set(locs))
    if stale:
        problems += len(stale)
        print(f"[2] {len(stale)} mapped id(s) no longer exist in the world:")
        for i in stale:
            print(f"      {i:<6} -> {lm[i]}")
        print()

    missing = sorted({s for ss in lm.values() for s in ss if s.lstrip('@') not in sections})
    if missing:
        problems += len(missing)
        print(f"[3] {len(missing)} mapped section(s) do not exist in the pack:")
        for s in missing:
            print(f"      {s}")
        print()

    inverse = {s.lstrip('@'): i for i, ss in lm.items() for s in ss}
    if inverse != sm:
        problems += 1
        print("[3b] sectionID.lua is not the exact inverse of location_mapping.lua\n")

    bad_items = sorted(set(im) - set(items))
    if bad_items:
        problems += len(bad_items)
        print(f"[3c] {len(bad_items)} mapped item id(s) not in the world: {bad_items}\n")

    name_to_section = {}
    for i, ss in lm.items():
        if i in locs:
            name_to_section[locs[i]] = ss[0].lstrip('@')

    diffs = []
    for name, want in sorted(rules.items()):
        sec = name_to_section.get(name)
        if not sec:
            continue
        got = tracker_dnf(sections.get(sec, []))
        if got != want:
            diffs.append((name, sec, show(want), show(got)))
    if diffs:
        problems += len(diffs)
        print(f"[4] {len(diffs)} access rule(s) disagree with the world:")
        for n, s, w, g in diffs:
            print(f"      {n}\n          world  : {w}\n          tracker: {g}  [{s}]")
        print()

    if problems:
        print(f"FAIL - {problems} thing(s) to fix")
        return 1
    print("PASS - tracker matches this apworld")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
