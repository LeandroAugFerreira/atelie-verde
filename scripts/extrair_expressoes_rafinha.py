"""Extract the twelve official stickers, retaining the original drawing pixels.

The user supplied the sprite sheet and requested faithful extraction, rather
than a new illustration. Background removal follows only light pixels connected
to the cell perimeter, protecting the cream shirt and face inside dark outlines.
"""

import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/referencias/rafinha/Espressões do Rafinha.jpeg"
DESTINATION = ROOT / "frontend/public/rafinha/official"
POSES = [
    ("happy", (0, 0, 298, 470), (147, 254)),
    ("sad", (298, 0, 555, 470), (425, 265)),
    ("serious", (555, 0, 837, 470), (682, 285)),
    ("angry", (837, 0, 1122, 470), (978, 280)),
    ("thinking", (0, 470, 290, 909), (130, 700)),
    ("sleepy", (290, 470, 554, 909), (418, 730)),
    ("greeting", (554, 470, 838, 909), (688, 710)),
    ("surprised", (838, 470, 1122, 909), (975, 720)),
    ("shy", (0, 909, 290, 1402), (136, 1144)),
    ("skeptical", (290, 909, 560, 1402), (429, 1154)),
    ("delighted", (560, 909, 836, 1402), (684, 1157)),
    ("celebrating", (836, 909, 1122, 1402), (982, 1160)),
]


def remove_background(image):
    image = image.convert("RGB")
    region = Image.new("L", image.size, 255)
    region.putdata(
        [
            0 if min(rgb) > 214 and max(rgb) - min(rgb) < 39 else 255
            for rgb in image.get_flattened_data()
        ]
    )
    w, h = image.size
    for point in [(x, y) for x in range(w) for y in (0, h - 1)] + [
        (x, y) for y in range(h) for x in (0, w - 1)
    ]:
        if region.getpixel(point) == 0:
            ImageDraw.floodfill(region, point, 128)
    alpha = region.point(lambda value: 0 if value == 128 else 255)
    result = image.convert("RGBA")
    result.putalpha(alpha)
    return result


def main():
    original = Image.open(SOURCE)
    if original.size != (1122, 1402):
        raise ValueError("A folha oficial mudou de tamanho; revise os recortes antes de executar.")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    # Segment on the whole sheet so a rectangular cell never clips hair or hands
    # and cannot retain fragments of the neighboring sticker.
    transparent = remove_background(original)
    width, height = original.size
    original_alpha = transparent.getchannel("A")
    visible = bytearray(original_alpha.filter(ImageFilter.MinFilter(5)).tobytes())
    components = []
    for start, alpha in enumerate(visible):
        if not alpha:
            continue
        points = []
        queue = deque([start])
        visible[start] = 0
        while queue:
            index = queue.popleft()
            points.append(index)
            x, y = index % width, index // width
            neighbors = (
                ([index - 1] if x else [])
                + ([index + 1] if x < width - 1 else [])
                + ([index - width] if y else [])
                + ([index + width] if y < height - 1 else [])
            )
            for other in neighbors:
                if visible[other]:
                    visible[other] = 0
                    queue.append(other)
        if len(points) > 8:
            components.append(points)
    bodies = [component for component in components if len(component) > 8000]
    assigned = []
    covered = Image.new("L", original.size)
    for _, _, mouth in POSES:
        body = min(
            bodies,
            key=lambda points: min(
                (point % width - mouth[0]) ** 2 + (point // width - mouth[1]) ** 2
                for point in points
            ),
        )
        raw = bytearray(width * height)
        for point in body:
            raw[point] = 255
        restored = ImageChops.multiply(
            Image.frombytes("L", original.size, bytes(raw)).filter(ImageFilter.MaxFilter(7)),
            original_alpha,
        )
        assigned.append(bytearray(restored.tobytes()))
        covered = ImageChops.lighter(covered, restored)
    remaining = bytearray(ImageChops.subtract(original_alpha, covered).tobytes())
    for start, value in enumerate(remaining):
        if not value:
            continue
        queue = deque([start])
        remaining[start] = 0
        component = []
        while queue:
            point = queue.popleft()
            component.append(point)
            x, y = point % width, point // width
            for other in (
                ([point - 1] if x else [])
                + ([point + 1] if x < width - 1 else [])
                + ([point - width] if y else [])
                + ([point + width] if y < height - 1 else [])
            ):
                if remaining[other]:
                    remaining[other] = 0
                    queue.append(other)
        if len(component) < 8:
            continue
        cx = sum(point % width for point in component) / len(component)
        cy = sum(point // width for point in component) / len(component)
        target = min(
            range(12), key=lambda i: (cx - POSES[i][2][0]) ** 2 + (cy - POSES[i][2][1]) ** 2
        )
        if 909 < cy < 1040 and cx > 800:
            target = 11  # Raised celebration marks belong to the last sticker.
        if (cx - POSES[target][2][0]) ** 2 + (cy - POSES[target][2][1]) ** 2 < 240**2:
            for point in component:
                assigned[target][point] = 255
    records = []
    for number, (name, box, mouth) in enumerate(POSES, 1):
        alpha = assigned[number - 1]
        silhouette = Image.frombytes("L", original.size, bytes(alpha))
        isolated = original.convert("RGBA")
        isolated.putalpha(silhouette)
        bounds = silhouette.getbbox()
        cutout = isolated.crop(bounds)
        scale = 0.8
        cutout = cutout.resize(
            (round(cutout.width * scale), round(cutout.height * scale)), Image.Resampling.LANCZOS
        )
        offset = (
            round(160 - (mouth[0] - bounds[0]) * scale),
            round(210 - (mouth[1] - bounds[1]) * scale),
        )
        canvas = Image.new("RGBA", (320, 400))
        canvas.alpha_composite(cutout, offset)
        canvas.save(DESTINATION / f"rafinha_{name}.webp", lossless=True, method=6)
        records.append(
            {
                "index": number,
                "name": name,
                "file": f"rafinha_{name}.webp",
                "source_box": box,
                "source_mouth": mouth,
                "mouth": [0.5, 0.525],
                "canvas": [320, 400],
                "alpha_bounds": canvas.getbbox(),
            }
        )
    manifest = {
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "method": "faithful extraction; perimeter-connected background; shared scale and mouth anchor",
        "poses": records,
    }
    (DESTINATION / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Checkerboard overview for visual QA; the public assets retain their alpha.
    sheet = Image.new("RGB", (960, 1200), "#dce9df")
    draw = ImageDraw.Draw(sheet)
    for y in range(0, 1200, 16):
        for x in range(0, 960, 16):
            if (x // 16 + y // 16) % 2:
                draw.rectangle((x, y, x + 15, y + 15), fill="#f2f6f2")
    for i, record in enumerate(records):
        asset = Image.open(DESTINATION / record["file"])
        point = (i % 3 * 320, i // 3 * 300)
        preview = asset.resize((240, 300), Image.Resampling.LANCZOS)
        sheet.paste(preview, (point[0] + 40, point[1]), preview)
        draw.text((point[0] + 8, point[1] + 280), record["name"], fill="#133626")
    overview = ROOT / ".local/rafinha-official-overview.png"
    overview.parent.mkdir(exist_ok=True)
    sheet.save(overview)
    print(
        json.dumps(
            {"count": len(records), "assets": str(DESTINATION), "preview": str(overview)},
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
