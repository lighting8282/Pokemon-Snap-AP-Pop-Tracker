"""Build the Poses tab: a sprite board of every Pokemon with a posesanity pose.

    python tools/make_poses_map.py          # after make_poses.py

The course maps already show each pose on its Pokemon's pin, but with a few
dozen poses spread over seven courses they are hard to survey. This tab puts
them on one board: a row per course, a sprite per Pokemon, and a pin on each
sprite holding that Pokemon's poses on that course. A pin only appears when
the seed contains at least one of its poses, so the board shows exactly
what is left to find.

It reads the pose refs make_poses.py put on the course maps, so it never
needs the apworld, and writes:

    images/PosesMap.png      the board (sprites keyed from magenta to black)
    locations/poses.json     a pin per Pokemon per course, of refs
"""
import sys, json
from pathlib import Path
from PIL import Image

PACK = Path(__file__).resolve().parent.parent

ROWS = [("Beach", "beach"), ("Tunnel", "tunnel"), ("Volcano", "volcano"),
        ("River", "river"), ("Cave", "cave"), ("Valley", "valley"),
        ("Rainbow Cloud", "oakmew")]
PLATE = {"Rainbow Cloud": "rainbow"}       # nameplate image, else the course code

SPRITE, PITCH, ROW_H = 64, 68, 72
LABEL_W, PAD = 140, 6
PIN = 18                                   # map location_size
KEY = (255, 0, 255)


def pose_refs(course_file):
    """Pokemon -> [(section name, ref)] for every pose on this course map."""
    data = json.loads((PACK / "locations" / f"{course_file}.json").read_text(encoding="utf-8-sig"))
    out = {}

    def walk(n):
        for s in n.get("sections", []) or []:
            ref = s.get("ref", "")
            owner, _, section = ref.partition("/")
            if "Pose: " in section:
                phrase = section.split("Pose: ", 1)[1]
                out.setdefault(owner, []).append((phrase, ref))
        for c in n.get("children", []) or []:
            walk(c)
    for n in data:
        walk(n)
    return out


def keyed(path):
    im = Image.open(path).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y][:3] == KEY:
                px[x, y] = (0, 0, 0, 0)
    return im


def main():
    rows = [(title, pose_refs(f)) for title, f in ROWS]
    rows = [(t, r) for t, r in rows if r]
    cols = max(len(r) for _, r in rows)
    W = LABEL_W + cols * PITCH + PAD
    H = len(rows) * ROW_H + PAD
    board = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    course_nodes = []
    for i, (title, refs) in enumerate(rows):
        y0 = PAD + i * ROW_H
        plate = keyed(PACK / "images" / f"{PLATE.get(title, title.lower())}.png")
        plate = plate.resize((plate.width * 3 // 2, plate.height * 3 // 2), Image.NEAREST)
        board.alpha_composite(plate, (PAD, y0 + (SPRITE - plate.height) // 2))

        children = []
        for j, owner in enumerate(sorted(refs)):
            x0 = LABEL_W + j * PITCH
            board.alpha_composite(keyed(PACK / "images/pokemon" / f"{owner}.png"), (x0, y0))
            children.append({
                "name": owner,
                "sections": [{"name": phrase, "ref": ref} for phrase, ref in refs[owner]],
                # bottom-right corner, so the sprite stays readable
                "map_locations": [{"map": "poses", "x": x0 + SPRITE - PIN // 2,
                                   "y": y0 + SPRITE - PIN // 2}],
            })
        course_nodes.append({"name": title, "children": children})

    board.convert("RGB").save(PACK / "images/PosesMap.png")
    doc = [{"name": "Poses", "children": course_nodes}]
    (PACK / "locations/poses.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
    pins = sum(len(c["children"]) for c in course_nodes)
    poses = sum(len(k["sections"]) for c in course_nodes for k in c["children"])
    print(f"poses board {W}x{H}: {len(rows)} courses, {pins} pins, {poses} poses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
