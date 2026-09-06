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
              "Tutorial", "ItemClassification", "CollectionState"]:
        setattr(bc, n, type(n, (object,), {"__init__": lambda self, *a, **k: None}))
    sys.modules["BaseClasses"] = bc

    # 0.7.0 made items.py import options.py, which needs Archipelago's Options.
    # Stub it so option classes are readable as plain values (their `default`
    # is a class attribute, which is all this tool looks at).
    opt = types.ModuleType("Options")

    class _Opt:
        default = 0
        option_true = 1
        option_false = 0
        def __init__(self, *a, **k):
            self.value = type(self).default
        def __class_getitem__(cls, item): return cls
        def __init_subclass__(cls, **kw): super().__init_subclass__()

    for n in ["Option", "Choice", "Toggle", "DefaultOnToggle", "Range",
              "NamedRange", "StartInventoryPool", "OptionSet", "OptionList",
              "FreeText", "TextChoice", "DeathLink", "ItemDict"]:
        setattr(opt, n, type(n, (_Opt,), {}))
    opt.DefaultOnToggle.default = 1
    opt.PerGameCommonOptions = type("PerGameCommonOptions", (object,), {})
    opt.OptionGroup = type("OptionGroup", (object,),
                           {"__init__": lambda self, *a, **k: None})
    opt.Visibility = type("Visibility", (object,), {"none": 0, "all": 0xFF})
    sys.modules["Options"] = opt

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
    return version, locs, items, root


# AP item name -> the pack's item code. Keyed on the value, not the python
# identifier, so renaming a constant upstream cannot silently drop a rule.
ITEM_CODE = {"Pester Ball": "pester", "Apple": "food", "PokeFlute": "flute",
             "Dash Engine": "dash", "Pokemon Sign Detector": "sign"}


def _stub_rule_builder():
    """Enough of rule_builder for the world's rules.py to import and be read.

    The world builds its rules as objects in a LOCATION_RULES table. Recording
    what those constructors were called with is far more durable than reading
    the source: upstream has restructured rules.py twice, and both times a
    regex parser kept passing while silently comparing nothing.
    """
    class _Resolved:
        def __init__(self, *a, **k): pass

    class Rule:
        # Rule["PokemonSnapWorld"] and `class X(Rule, game="...")` both appear,
        # and subclasses annotate against Rule.Resolved.
        Resolved = _Resolved
        def __class_getitem__(cls, item): return cls
        def __init_subclass__(cls, **kw): super().__init_subclass__()
        def __init__(self, *a, **k): self.args = a
        # 0.7.0 composes rules with & and |, e.g. _HAS_PESTER & HasFilm(4).
        def __and__(self, other): return mod.And(self, other)
        def __or__(self, other): return mod.Or(self, other)
        def __rand__(self, other): return mod.And(other, self)
        def __ror__(self, other): return mod.Or(other, self)

    def _mk(name):
        return type(name, (Rule,), {})

    mod = types.ModuleType("rule_builder.rules")
    pkg = types.ModuleType("rule_builder")
    names = ["Has", "HasAll", "HasAny", "And", "Or", "CanReachLocation",
             "CollectionState", "False_", "True_", "HasGroup", "NestedRule",
             "FieldResolver", "OptionFilter"]
    for n in names:
        setattr(mod, n, _mk(n))
    mod.Rule = Rule
    mod.resolve_field = lambda *a, **k: None
    pkg.rules = mod
    sys.modules["rule_builder"] = pkg
    sys.modules["rule_builder.rules"] = mod

    nu = types.ModuleType("NetUtils")
    nu.JSONMessagePart = dict
    sys.modules["NetUtils"] = nu

    # future_rules.py pulls these from typing_extensions, which a bare Python
    # install does not have; the stdlib versions are equivalent here.
    if "typing_extensions" not in sys.modules:
        try:
            import typing_extensions  # noqa: F401
        except ImportError:
            import typing
            te = types.ModuleType("typing_extensions")
            for n in ("TypeVar", "override", "Self", "Any", "Protocol"):
                setattr(te, n, getattr(typing, n, object))
            sys.modules["typing_extensions"] = te
    return mod


def to_dnf(rule, rb):
    """A rule object -> alternative requirement sets, or None if not expressible.

    None means "the tracker cannot be checked against this", e.g. HasGroup for
    the goal or CanReachLocation for Oak's rewards. Those are counted and
    reported rather than quietly dropped.
    """
    kind = type(rule).__name__
    if kind == "Has":
        c = ITEM_CODE.get(rule.args[0])
        return {frozenset({c})} if c else None
    if kind in ("HasAny", "HasAll"):
        cs = [ITEM_CODE.get(a) for a in rule.args]
        if any(c is None for c in cs):
            return None
        return {frozenset({c}) for c in cs} if kind == "HasAny" else {frozenset(cs)}
    if kind == "And":
        acc = {frozenset()}
        for sub in rule.args:
            d = to_dnf(sub, rb)
            if not d:
                return None
            acc = {a | b for a in acc for b in d}
        return acc
    if kind == "Or":
        acc = set()
        for sub in rule.args:
            d = to_dnf(sub, rb)
            if not d:
                return None
            acc |= d
        return acc
    return None


def parse_rules(root):
    """Read LOCATION_RULES out of the world and reduce it to AP name -> DNF.

    Returns (comparable, opaque) - the second is the list of location names
    whose rule this cannot express, so a shrinking comparable set is visible
    instead of looking like a clean pass.
    """
    rb = _stub_rule_builder()
    import importlib
    R = importlib.import_module("pokemon_snap.rules")

    out, opaque = {}, []
    for name, categories in R.LOCATION_RULES.items():
        for category, rule in categories.items():
            try:
                ap_name = R.location_name(name, category)
            except Exception:
                opaque.append(f"{name} [{category}]")
                continue
            d = to_dnf(rule, rb)
            if d:
                out[ap_name] = d
            else:
                opaque.append(ap_name)
    parse_rules.module = R

    # set_oak_rules() gives the six Oak rewards AtLeast/ReportScoreAchievable
    # rules, which are "can you reach N other checks" rather than "do you hold
    # tool X", so there is nothing for a tool-requirement comparison to check.
    # The goal is likewise an entrance rule (HasGroup over picture items),
    # modelled in the pack as $goal_unlocked. Listed so the count below never
    # reads as fuller coverage than it is.
    for n in ("POKEMON_TOTAL_6", "POKEMON_TOTAL_22", "POKEMON_TOTAL_40",
              "REPORT_SCORE_24_000", "REPORT_SCORE_72_500", "REPORT_SCORE_130_000"):
        opaque.append(getattr(R, n, n))
    opaque.append("Rainbow Cloud entrance (goal)")
    return out, opaque


# ------------------------------------------------------------------- pack ---

def load_pack():
    lm, sm, im = {}, {}, {}
    txt = open(PACK / "scripts/autotracking/location_mapping.lua", encoding="utf-8").read()
    for m in re.finditer(r"\[(\d+)\]\s*=\s*\{([^}]*)\}", txt):
        lm[int(m.group(1))] = re.findall(r'"([^"]+)"', m.group(2))
    txt = open(PACK / "scripts/autotracking/sectionID.lua", encoding="utf-8").read()
    head = txt.split("oldSectionIDtoAPID")[0]
    # values may be a bare id or a list of ids (base photo + bonus twin)
    for m in re.finditer(r'\["([^"]+)"\]\s*=\s*(\{[^}]*\}|\d+)', head):
        v = m.group(2)
        sm[m.group(1)] = sorted(int(x) for x in re.findall(r"\d+", v))
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
            # $goal_unlocked mirrors the world's Start -> Rainbow Cloud
            # entrance rule, so like a course code it is region access, not
            # an item requirement.
            if p in COURSES or p == "$goal_unlocked" or not p:
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
    if d is UNREACHABLE:
        return "(unreachable)"
    return " OR ".join("+".join(sorted(x)) or "(free)" for x in sorted(d, key=sorted)) or "(free)"


# ------------------------------------------------------- option-aware sweep ---
#
# Since 0.7.0 a location's rule depends on the yaml: photo scoring can put Good
# Technique and Multiple behind items, film capacity is a real requirement, and
# rng_checks can open an alternative. A single comparison can therefore only
# ever check one yaml. This evaluates both sides under the same option set and
# compares, which is what catches a rule the pack models for one setting only.

UNREACHABLE = "UNREACHABLE"      # no combination of items satisfies the rule
FREE = frozenset()

# name -> (photo_scoring, starting_film, rng_checks)
OPTION_SETS = [
    ("defaults",                 (0, 15, 0)),
    ("separate scoring",         (1, 15, 0)),
    ("progressive unlocks",      (2, 15, 0)),
    ("separate unlocks",         (3, 15, 0)),
    ("separate + rng checks",    (1, 15, 1)),
    ("starting_film 1",          (0,  1, 0)),
    ("starting_film 5",          (0,  5, 0)),
    ("starting_film 8",          (0,  8, 0)),
]


def _scoring_tokens(scoring, category):
    """What holding the scoring unlock looks like, as requirement tokens."""
    wonderful = category == "WONDERFUL_PHOTO"
    if scoring in (0, 1):
        return {FREE}
    if scoring == 2:
        return {frozenset({"progscore1" if wonderful else "progscore2"})}
    return {frozenset({"wdflscore" if wonderful else "multscore"})}


def world_dnf(rule, cfg):
    """Reduce a world rule to requirement sets under one option configuration."""
    scoring, film, rng = cfg
    k = type(rule).__name__
    if k == "True_":
        return {FREE}
    if k == "False_":
        return UNREACHABLE
    if k == "HasFilm":
        return {FREE} if film >= rule.film_requirement else UNREACHABLE
    if k == "OptionFilter":
        # the world uses exactly two: separate scoring, and rng checks on
        which = str(rule.args[0]) if rule.args else ""
        on = (scoring in (1, 3)) if "PhotoScoring" in which else bool(rng)
        return {FREE} if on else UNREACHABLE
    if k == "Has":
        c = ITEM_CODE.get(rule.args[0])
        return {frozenset({c})} if c else UNREACHABLE
    if k in ("HasAny", "HasAll"):
        cs = [ITEM_CODE.get(a) for a in rule.args]
        if any(c is None for c in cs):
            return UNREACHABLE
        return {frozenset({c}) for c in cs} if k == "HasAny" else {frozenset(cs)}
    if k in ("And", "list"):
        # a bare list where a rule is expected is an AND of its members
        parts = rule if k == "list" else rule.args
        acc = {FREE}
        for sub in parts:
            d = world_dnf(sub, cfg)
            if d is UNREACHABLE:
                return UNREACHABLE
            acc = {a | b for a in acc for b in d}
        return acc
    if k == "Or":
        acc = set()
        for sub in rule.args:
            d = world_dnf(sub, cfg)
            if d is not UNREACHABLE:
                acc |= d
        return acc or UNREACHABLE
    return None                                    # not expressible


def pack_dnf(rules, cfg):
    """The same reduction for a section's access_rules."""
    scoring, film, rng = cfg
    out = set()
    for r in rules:
        parts = [x.strip() for x in r.split(",")]
        if any(p.startswith("{") for p in parts):
            continue
        opts, ok = [[]], True
        for p in parts:
            if p.startswith("[") and p.endswith("]"):
                continue
            if p in COURSES or p == "$goal_unlocked" or not p:
                continue
            if p == "@Logic/Throwable":
                opts = [o + [t] for o in opts for t in ("pester", "food")]
                continue
            if p in TOOLS:
                opts = [o + [p] for o in opts]
                continue
            if p.startswith("$has_film_"):
                if film < int(p.rsplit("_", 1)[1]):
                    ok = False
                    break
                continue
            if p == "$separate_scoring":
                if scoring not in (1, 3):
                    ok = False
                    break
                continue
            if p == "$rng_checks_on":
                if not rng:
                    ok = False
                    break
                continue
            if p in ("$can_wonderful", "$can_multiple"):
                tok = _scoring_tokens(scoring,
                                      "WONDERFUL_PHOTO" if p.endswith("wonderful")
                                      else "MULTIPLE_PHOTO")
                opts = [o + sorted(t) for o in opts for t in tok]
                continue
            ok = False
            break
        if ok:
            out.update(frozenset(o) for o in opts)
    if not rules:
        return {FREE}
    if not out:
        return UNREACHABLE
    return {a for a in out if not any(b < a for b in out)}


def applicable_option_sets(R):
    """Only sweep settings this apworld actually has.

    The pack supports several apworld versions at once, so it carries rules for
    options an older world never had. Replaying 0.7.0's option sets against
    0.6.0 would report those as disagreements when at runtime the option simply
    never arrives in slot_data and the tracker falls back to vanilla.
    """
    src = ""
    try:
        src = open(os.path.join(os.path.dirname(R.__file__), "rules.py"),
                   encoding="utf-8").read()
    except Exception:
        pass
    has_scoring = "PhotoScoring" in src
    has_film = "HasFilm" in src
    out = []
    for label, cfg in OPTION_SETS:
        scoring, film, rng = cfg
        if scoring and not has_scoring:
            continue
        if film != 15 and not has_film:
            continue
        out.append((label, cfg))
    return out


def sweep(R, sections, name_to_section):
    """Compare every world rule against the pack under each option set."""
    results = []
    for label, cfg in applicable_option_sets(R):
        diffs, compared, skipped = [], 0, 0
        for name, categories in R.LOCATION_RULES.items():
            for category, rule in categories.items():
                try:
                    ap_name = R.location_name(name, category)
                except Exception:
                    continue
                sec = name_to_section.get(ap_name)
                if not sec:
                    continue
                want = world_dnf(rule, cfg)
                if want is None:
                    skipped += 1
                    continue
                # set_rules() ANDs the scoring unlock onto these two categories
                cat = getattr(category, "name", str(category))
                if cat in ("WONDERFUL_PHOTO", "MULTIPLE_PHOTO") and want is not UNREACHABLE:
                    tok = _scoring_tokens(cfg[0], cat)
                    want = {a | b for a in want for b in tok}
                if want is not UNREACHABLE:
                    want = {a for a in want if not any(b < a for b in want)}
                got = pack_dnf(sections.get(sec, []), cfg)
                compared += 1
                if got != want:
                    diffs.append((ap_name, sec, show(want), show(got)))
        results.append((label, compared, skipped, diffs))
    return results


# ------------------------------------------------------------------- main ---

def main(apworld):
    version, locs, items, root = load_apworld(apworld)
    rules, opaque = parse_rules(root)
    lm, sm, im, sections = load_pack()
    pack_version = json.load(open(PACK / "manifest.json", encoding="utf-8-sig"))["package_version"]

    print(f"apworld world_version {version}   |   pack {pack_version}")
    print("   (world_version is read from archipelago.json, which upstream has shipped"
          " stale before; hash the file against the GitHub releases if it matters)")
    print(f"world: {len(locs)} locations, {len(items)} items"
          f"   |   pack maps {len(lm)} locations, {len(im)} items")
    print()
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

    inverse = {}
    for i, ss in lm.items():
        inverse.setdefault(ss[0].lstrip('@'), []).append(i)
    inverse = {k: sorted(v) for k, v in inverse.items()}
    if inverse != sm:
        problems += 1
        print("[3b] sectionID.lua is not the exact inverse of location_mapping.lua\n")

    # Item ids the pack maps but this world does not have. Not a failure: the
    # pack supports several apworld versions, and an id that never arrives does
    # nothing. Contrast with location ids, where a stale mapping clears the
    # wrong check - that stays a failure above.
    bad_items = sorted(set(im) - set(items))
    if bad_items:
        print(f"[3c] note: {len(bad_items)} mapped item id(s) absent from this world"
              f" (fine if they are newer than it): {bad_items}\n")

    name_to_section = {}
    for i, ss in lm.items():
        if i in locs:
            name_to_section[locs[i]] = ss[0].lstrip('@')

    # [4] Logic, swept across option sets. Since 0.7.0 a rule's meaning depends
    # on the yaml, so one comparison can only ever vouch for one configuration.
    results = sweep(parse_rules.module, sections, name_to_section)
    total_compared = min(r[1] for r in results)
    print("[4] logic, per option set:")
    for label, compared, skipped, diffs in results:
        mark = "ok" if not diffs else f"{len(diffs)} DISAGREE"
        print(f"      {label:<24} compared {compared:3d}   {mark}")
        for n, s, w, g in diffs[:6]:
            print(f"          {n}\n              world  : {w}\n              tracker: {g}  [{s}]")
        if len(diffs) > 6:
            print(f"          ... and {len(diffs) - 6} more")
        problems += len(diffs)
    skipped = results[0][2]
    if skipped:
        print(f"      ({skipped} rule(s) not expressible as tool requirements)")

    # A logic check that compares nothing has passed silently twice before, so
    # treat "almost nothing compared" as a failure in its own right.
    if total_compared < 50:
        problems += 1
        print(f"    !! only {total_compared} rules compared - the reader has probably"
              " stopped understanding this apworld's rules.py; fix it before"
              " trusting this run")
    print()

    # [5] Image references, compared case-sensitively. Windows resolves
    # "new.png" to "New.png" happily, so a wrong-case reference works in the
    # unpacked working copy and then fails for everyone loading the zip, where
    # entries are matched exactly. 1.4.0.2 shipped one of these.
    on_disk = set()
    for root_dir, _, files in os.walk(PACK / "images"):
        for f in files:
            rel = os.path.relpath(os.path.join(root_dir, f), PACK)
            on_disk.add(rel.replace("\\", "/"))
    bad = {}
    for f in list((PACK).rglob("*.json")) + list((PACK / "scripts").rglob("*.lua")):
        if ".git" in f.parts or "tools" in f.parts:
            continue
        for m in re.finditer(r'"(images/[^"]+\.png)"',
                             f.read_text(encoding="utf-8-sig", errors="ignore")):
            if m.group(1) not in on_disk:
                bad.setdefault(m.group(1), set()).add(f.relative_to(PACK).as_posix())
    if bad:
        problems += len(bad)
        print(f"[5] {len(bad)} image reference(s) do not match a file exactly:")
        for img, where in sorted(bad.items()):
            near = [d for d in on_disk if d.lower() == img.lower()]
            hint = f"  (did you mean {near[0]}?)" if near else "  (no such file)"
            print(f"      {img}{hint}\n          from {', '.join(sorted(where))}")
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
