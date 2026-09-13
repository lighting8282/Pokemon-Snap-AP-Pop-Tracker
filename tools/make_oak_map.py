"""Rebuild the Oak's Lab map as a wide image instead of a tall one.

The original art stacks Prof. Oak's Check above the Mew scene, giving a picture
208x246 - taller than it is wide. The slot it lives in, under the Items panel,
is the opposite shape: wide and short. A picture that keeps its proportions can
only be as wide as the available height allows, so the tall art renders small
no matter what the layout does.

Placing the two scenes side by side turns it into a wide picture that fits the
wide slot, so it draws several times larger from the same source pixels. No
upscaling is involved; the scenes are cut from the original and moved.

    python tools/make_oak_map.py            # writes images/OakLand.png

The original is kept as images/OakLand-tall.png so this can be reversed.
"""
import sys
from pathlib import Path
from PIL import Image

PACK = Path(__file__).resolve().parent.parent
SRC = PACK / "images" / "OakLand-tall.png"
CUR = PACK / "images" / "OakLand.png"
OUT = CUR

SPLIT = 119          # first row of the Mew scene; the banner's red edge ends at 118
GAP = 2              # a thin seam so the two scenes read as separate panels

# How wide the picture ends up decides how large it draws. The slot is roughly
# 2:1, so a very wide picture uses only a band of it and leaves black above and
# below. Trimming narrows the picture, which makes it render taller and bigger
# in the same width.
#
# The banner cannot give much: its red border runs x=7..200. The Mew scene is
# mostly empty starfield, with the ring only at x=49..158, so it can lose a
# lot from both sides and stay centred on the ring.
TOP_CROP = (4, 203)        # keeps the red border with a 3px margin
BOTTOM_CROP = (40, 168)    # centred on the ring


def main():
    # first run: preserve the original tall art under its own name
    if not SRC.exists():
        Image.open(CUR).save(SRC)
        print(f"kept the original as {SRC.relative_to(PACK).as_posix()}")

    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    top = im.crop((TOP_CROP[0], 0, TOP_CROP[1], SPLIT))         # Prof. Oak's Check
    bottom = im.crop((BOTTOM_CROP[0], SPLIT, BOTTOM_CROP[1], h))  # Mew on the Cloud

    height = max(top.height, bottom.height)
    out = Image.new("RGB", (top.width + GAP + bottom.width, height), (0, 0, 0))
    top_y = (height - top.height) // 2
    bottom_x = top.width + GAP
    bottom_y = (height - bottom.height) // 2
    out.paste(top, (0, top_y))
    out.paste(bottom, (bottom_x, bottom_y))
    out.save(OUT)

    print(f"wrote {OUT.relative_to(PACK).as_posix()}  {out.width}x{out.height}"
          f"  (source was {w}x{h})")
    print(f"aspect {out.width / out.height:.2f} wide, was {w / h:.2f}")
    print()
    print("pin coordinates:")
    for name, (x, y) in {
        "Report Scores":        (78, 85),
        "Pokemon Photographed": (130, 85),
        "Mew":                  (104, 155),
    }.items():
        if y < SPLIT:
            nx, ny = x - TOP_CROP[0], y + top_y
        else:
            nx = (x - BOTTOM_CROP[0]) + bottom_x
            ny = (y - SPLIT) + bottom_y
        inside = 0 <= nx < out.width and 0 <= ny < out.height
        print(f"    {name:<22} ({x},{y})  ->  ({nx},{ny})"
              f"{'' if inside else '   OFF-CANVAS'}")
    # the release button is not anchored to any art, so it just sits in the
    # bottom-right of the Mew panel rather than being mapped from the original
    print(f"    {'Release button':<22} -> ({out.width - 12},{out.height - 14})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
