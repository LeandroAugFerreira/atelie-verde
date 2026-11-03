"""Prepare licensed photographic candidates for manual botanical review."""

import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

from completar_fotos import plain
from qualificar_fotos import read

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / ".local/plant-candidates"
sys.stdout.reconfigure(encoding="utf-8")
SPECIES = {
    "buxus-sempervirens": "Buxus sempervirens",
    "crassula-ovata": "Crassula ovata",
    "chlorophytum-comosum": "Chlorophytum comosum",
    "spathiphyllum-wallisii": "Spathiphyllum wallisii",
    "dracaena-trifasciata": "Sansevieria trifasciata",
    "salvia-rosmarinus": "Rosmarinus officinalis",
    "chrysalidocarpus-lutescens": "Dypsis lutescens",
    "cereus-repandus": "Cereus repandus",
    "schlumbergera-truncata": "Schlumbergera truncata",
    "punica-granatum": "Punica granatum",
    "adenium-obesum": "Adenium obesum",
}


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    for slug, name in SPECIES.items():
        path = FOLDER / f"{slug}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")):
            continue
        url = (
            "https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch="
            + quote('"' + name + '"')
            + "&gsrnamespace=6&gsrlimit=35&prop=imageinfo&iiprop=url%7Cextmetadata%7Csize"
            + "&iiurlwidth=400&format=json"
        )
        rows = []
        try:
            data = json.loads(read(url))
            for page in sorted(
                data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99)
            ):
                info = page.get("imageinfo", [{}])[0]
                meta = info.get("extmetadata", {})
                label = meta.get("LicenseShortName", {}).get("value", "")
                title = page["title"]
                names = [name, slug.replace("-", " ")]
                if not any(
                    all(w.lower() in title.lower() for w in candidate.split())
                    for candidate in names
                ):
                    continue
                if (
                    not label.startswith(("CC BY", "CC0", "Public domain"))
                    or "NC" in label
                    or "ND" in label
                ):
                    continue
                if max(info.get("width", 0), info.get("height", 0)) < 1500:
                    continue
                if (
                    not info.get("url", "")
                    .split("?", 1)[0]
                    .lower()
                    .endswith((".jpg", ".jpeg", ".png"))
                ):
                    continue
                caption = plain(meta.get("ImageDescription", {}).get("value", title))
                if any(
                    w in (title + " " + caption).lower()
                    for w in [
                        "illustration",
                        "botanical plate",
                        "köhler",
                        "koehler",
                        "sturm",
                        "drawing",
                        "botanical illustration",
                    ]
                ):
                    continue
                number = len(rows)
                thumbnail = info.get("thumburl") or info["url"]
                try:
                    raw = read(thumbnail)
                except Exception:
                    continue
                preview = FOLDER / f"{slug}-{number}.jpg"
                preview.write_bytes(raw)
                rows.append(
                    {
                        "index": number,
                        "title": title,
                        "preview": str(preview),
                        "author": plain(
                            meta.get("Artist", {}).get("value", "Autor indicado na fonte")
                        ),
                        "license": label,
                        "license_url": meta.get("LicenseUrl", {}).get("value", ""),
                        "caption": caption,
                        "source_url": info["descriptionurl"],
                        "original_url": info["url"].split("?", 1)[0],
                        "thumbnail_url": thumbnail,
                        "original_dimensions": [info["width"], info["height"]],
                    }
                )
                if len(rows) >= 12:
                    break
                time.sleep(0.2)
            path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            print(slug, len(rows), flush=True)
        except Exception as exc:
            print(slug, type(exc).__name__, getattr(exc, "code", ""), flush=True)
        time.sleep(2)


if __name__ == "__main__":
    main()
