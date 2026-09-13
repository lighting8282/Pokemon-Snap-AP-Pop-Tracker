"""Generate the nameplates for the seed-settings readout.

The readout shows one plate per yaml option, lit when the seed enabled it and
dimmed when it did not. The plates are drawn in the same style as the course
nameplates the pack already uses, so the panel looks like part of the tracker
rather than a debug dump.

    python tools/make_setting_labels.py

Output: images/settings/<key>.png, 88x20 to match images/beach.png.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PACK = Path(__file__).resolve().parent.parent
OUT = PACK / "images" / "settings"

W, H = 88, 20
KEY = (255, 0, 255, 255)          # PopTracker renders this pink as transparent
PLATE = (33, 115, 123, 255)       # sampled from images/beach.png
EDGE = (189, 255, 255, 255)
TEXT = (255, 255, 255, 255)

# key -> the words on the plate
LABELS = {
    "goodtechnique": "Good Tech",
    "multiple":      "Multiple",
    "poses":         "Poses",
    "signs":         "Signs",
    "exits":         "Exits",
    "photocount":    "Photos",
    "scoretotal":    "Score",
    "rng":           "RNG",
    "hard":          "Hard",
    "scoring":       "Scoring",
    "fragments":     "Frags",
    "goal":          "Goal",
    "film":          "Film",
}


def find_font(size):
    for name in ("verdanab.ttf", "tahomabd.ttf", "arialbd.ttf"):
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def plate(text):
    img = Image.new("RGBA", (W, H), KEY)
    d = ImageDraw.Draw(img)
    d.rectangle([1, 1, W - 2, H - 2], fill=PLATE, outline=EDGE, width=1)

    # shrink until it fits rather than letting a long label run off the plate
    for size in range(11, 6, -1):
        font = find_font(size)
        box = d.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= W - 8:
            break
    x = (W - (box[2] - box[0])) // 2 - box[0]
    y = (H - (box[3] - box[1])) // 2 - box[1]
    d.text((x, y), text, font=font, fill=TEXT)
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, text in LABELS.items():
        plate(text).save(OUT / f"{key}.png")
    print(f"wrote {len(LABELS)} plates to {OUT.relative_to(PACK).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
