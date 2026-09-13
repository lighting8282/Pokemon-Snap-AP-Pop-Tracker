"""Generate the partially-lit course nameplates used for map fragments.

apworld 0.7.0 can require N map fragments to unlock a course. The course
nameplate fills left to right as they arrive: with 2 of 5 held, the left two
fifths are in colour and the rest carries the pack's disabled look, with tick
marks on the divisions so the fraction can be counted at a glance.

PopTracker cannot composite images at runtime, so every state is baked here:
for each course, every (held, required) pair with required 2..6 and held
1..required-1. The 0 and full states are the plain icon with and without
IconMods, so they are not generated.

    python tools/make_fragment_icons.py            # from the pack root

Output: images/fragments/<course>_<held>of<required>.png
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

PACK = Path(__file__).resolve().parent.parent
OUT = PACK / "images" / "fragments"
COURSES = ["beach", "tunnel", "volcano", "river", "cave", "valley"]
MAX_REQUIRED = 6                     # options.py: MapFragments range_end

TICK = (0, 0, 0, 170)                # division marks
EDGE = (255, 255, 255, 190)          # the lit/unlit boundary, brighter


KEY = (255, 0, 255)                  # PopTracker renders this pink as transparent


def keyed(im):
    """Source icons use pink as their backdrop; make it genuinely transparent.

    Baking it out matters here: PopTracker keys the pink itself, but only on
    the image it is given. Greyscaling first would turn it into a grey block,
    which is exactly what a naive 'dim the unlit half' pass produces.
    """
    im = im.convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if (r, g, b) == KEY:
                px[x, y] = (0, 0, 0, 0)
    return im


def disabled(im):
    """The pack's own unlit look: settings.json is 'grayscale, dim'."""
    src = keyed(im)
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    px, sp = out.load(), src.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = sp[x, y]
            if a == 0:
                continue
            v = int(0.299 * r + 0.587 * g + 0.114 * b) // 2
            px[x, y] = (v, v, v, a)
    return out


def build(base, held, required):
    lit = keyed(base)
    dark = disabled(base)
    w, h = lit.size
    cut = round(w * held / required)

    img = dark.copy()
    img.paste(lit.crop((0, 0, cut, h)), (0, 0))

    # Ticks only where the plate actually is, so nothing floats in the
    # transparent margin around it.
    px = img.load()
    for i in range(1, required):
        x = round(w * i / required)
        if x >= w:
            continue
        colour = EDGE if i == held else TICK
        for y in range(h):
            if px[x, y][3] != 0:
                px[x, y] = colour
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    made = 0
    for course in COURSES:
        src = PACK / "images" / f"{course}.png"
        if not src.exists():
            print("missing", src)
            return 1
        base = Image.open(src)
        for required in range(2, MAX_REQUIRED + 1):
            for held in range(1, required):
                build(base, held, required).save(
                    OUT / f"{course}_{held}of{required}.png")
                made += 1
    print(f"wrote {made} images to {OUT.relative_to(PACK).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
