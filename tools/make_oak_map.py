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


def main():
    # first run: preserve the original tall art under its own name
    if not SRC.exists():
        Image.open(CUR).save(SRC)
        print(f"kept the original as {SRC.relative_to(PACK).as_posix()}")

    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    top = im.crop((0, 0, w, SPLIT))          # Prof. Oak's Check
    bottom = im.crop((0, SPLIT, w, h))       # Mew on the Rainbow Cloud

    height = max(top.height, bottom.height)
    out = Image.new("RGB", (w * 2 + GAP, height), (0, 0, 0))
    top_y = (height - top.height) // 2
    out.paste(top, (0, top_y))
    out.paste(bottom, (w + GAP, (height - bottom.height) // 2))
    out.save(OUT)

    print(f"wrote {OUT.relative_to(PACK).as_posix()}  {out.width}x{out.height}"
          f"  (was {w}x{h})")
    print(f"aspect {out.width / out.height:.2f} wide, was {w / h:.2f}")
    print()
    print("pin coordinates for locations/oakmew.json:")
    for name, (x, y) in {
        "Report Scores":       (78, 85),
        "Pokemon Photographed": (130, 85),
        "Mew":                 (104, 155),
    }.items():
        if y < SPLIT:
            nx, ny = x, y + top_y
        else:
            nx, ny = x + w + GAP, (y - SPLIT) + (height - bottom.height) // 2
        print(f"    {name:<22} ({x},{y})  ->  ({nx},{ny})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
