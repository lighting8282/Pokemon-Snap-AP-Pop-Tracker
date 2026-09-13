"""Generate images/multiple.png to pair with the pack's existing wonderful.png.

wonderful.png is Oak over a magenta key colour with the game's dark-green score
plate reading "Wonderful!". Multiple PKMN had no art in the pack, so this builds
a matching plate reading "Multiple!" with three Pokeballs above it, reusing the
pack's own pokeball art so the pair reads as a set in the item grid.

    python make_multiple_icon.py <pack-root>
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PACK = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = PACK / "images" / "multiple.png"

W, H = 108, 98                      # match wonderful.png exactly
KEY = (255, 0, 255, 255)            # the magenta the pack uses as its backdrop
PLATE = (79, 117, 104, 255)         # score-plate green, sampled from wonderful
BORDER = (187, 192, 188, 255)       # its silver edge
TEXT = (246, 250, 248, 255)
SHADOW = (14, 26, 20, 255)

PLATE_TOP = 64                      # where the plate starts in wonderful.png


def find_font():
    """A clean bold face; the game's own font is not something we have."""
    for name, size in (("verdanab.ttf", 15), ("tahomabd.ttf", 15),
                       ("arialbd.ttf", 16), ("segoeuib.ttf", 16)):
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def main():
    img = Image.new("RGBA", (W, H), KEY)

    # --- three Pokeballs, staggered, in the art area -----------------------
    # Outer two first, centre one last, so they overlap into a group rather
    # than sitting apart. Sized to carry roughly the weight Oak's face does.
    ball = Image.open(PACK / "images" / "pokeball_closed.png").convert("RGBA")
    for (x, y, s) in ((3, 20, 38), (67, 20, 38), (33, 8, 44)):
        b = ball.resize((s, s), Image.LANCZOS)
        img.paste(b, (x, y), b)

    d = ImageDraw.Draw(img)

    # --- the score plate ---------------------------------------------------
    d.rectangle([0, PLATE_TOP, W - 1, H - 1], fill=PLATE)
    d.rectangle([3, PLATE_TOP + 4, W - 4, H - 5], outline=BORDER, width=2)

    label = "Multiple!"
    font = find_font()
    box = d.textbbox((0, 0), label, font=font)
    tx = (W - (box[2] - box[0])) // 2 - box[0]
    ty = PLATE_TOP + ((H - PLATE_TOP) - (box[3] - box[1])) // 2 - box[1]
    d.text((tx + 1, ty + 1), label, font=font, fill=SHADOW)
    d.text((tx, ty), label, font=font, fill=TEXT)

    img.save(OUT)
    print("wrote", OUT, img.size)


if __name__ == "__main__":
    main()
