"""Fetch higher-resolution licensed photos without altering existing originals."""

import io
import json
import sys
import time
import urllib.request
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "backend/app/photo_quality_manifest.json"
sys.stdout.reconfigure(encoding="utf-8")


def read(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "AtelieVerde/1.0 (educational catalog; attribution retained)"}
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read(10 * 1024 * 1024 + 1)
        except HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                raise
            time.sleep(6)


def candidates(slug):
    name = {"salvia-rosmarinus": "Rosmarinus officinalis"}.get(slug, slug.replace("-", " "))
    url = (
        "https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch="
        + quote('"' + name + '"')
        + "&gsrnamespace=6&gsrlimit=20&prop=imageinfo&iiprop=url%7Cextmetadata%7Csize"
        + "&iiurlwidth=1600&format=json"
    )
    data = json.loads(read(url))
    for page in sorted(
        data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99)
    ):
        info = page.get("imageinfo", [{}])[0]
        meta = info.get("extmetadata", {})
        label = meta.get("LicenseShortName", {}).get("value", "")
        if (
            not label.startswith(("CC BY", "CC0", "Public domain"))
            or "NC" in label
            or "ND" in label
        ):
            continue
        if not all(word in page["title"].lower() for word in name.split()):
            continue
        if info.get("width", 0) < 1200 or info.get("height", 0) < 900:
            continue
        yield info, meta, label


def main():
    from completar_fotos import plain

    manifest = json.loads((ROOT / "backend/app/photo_manifest.json").read_text(encoding="utf-8"))
    upgrades = json.loads(TARGET.read_text(encoding="utf-8")) if TARGET.exists() else []
    known = {p["previous_url"] for p in upgrades}
    for item in manifest:
        low = []
        for photo in item["photos"]:
            with Image.open(ROOT / "frontend/public" / photo["url"].lstrip("/")) as image:
                if max(image.size) < 1000 and photo["url"] not in known:
                    low.append(photo)
        if not low:
            continue
        index = 0
        try:
            for info, meta, label in candidates(item["slug"]):
                if any(p["original_url"] == info["url"].split("?")[0] for p in upgrades):
                    continue
                remote = info.get("thumburl") or info["url"]
                raw = read(remote)
                if len(raw) > 10 * 1024 * 1024:
                    continue
                with Image.open(io.BytesIO(raw)) as image:
                    if max(image.size) < 1200 or min(image.size) < 900:
                        continue
                    suffix = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(image.format)
                    if not suffix:
                        continue
                    dimensions = list(image.size)
                old = low[index]
                number = item["photos"].index(old) + 1
                filename = f"{item['slug']}-hd-{number}{suffix}"
                (ROOT / "frontend/public/plants" / filename).write_bytes(raw)
                upgrades.append(
                    {
                        "previous_url": old["url"],
                        "url": "/plants/" + filename,
                        "author": plain(
                            meta.get("Artist", {}).get("value", "Autor indicado na fonte")
                        ),
                        "license": label,
                        "license_url": meta.get("LicenseUrl", {}).get("value", ""),
                        "caption": plain(
                            meta.get("ImageDescription", {}).get(
                                "value", item["slug"].replace("-", " ")
                            )
                        ),
                        "source_url": info["descriptionurl"],
                        "original_url": info["url"].split("?")[0],
                        "dimensions": dimensions,
                        "changes": "Miniatura em alta resolução disponibilizada pelo Wikimedia Commons; sem edição local.",
                    }
                )
                TARGET.write_text(
                    json.dumps(upgrades, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                print(item["slug"], number, dimensions, flush=True)
                index += 1
                if index == len(low):
                    break
                time.sleep(0.3)
        except Exception as exc:
            print(item["slug"], type(exc).__name__, getattr(exc, "code", ""), flush=True)
        time.sleep(2)
    if not TARGET.exists():
        TARGET.write_text("[]\n", encoding="utf-8")
    print("Fotos melhoradas:", len(upgrades), flush=True)


if __name__ == "__main__":
    main()
