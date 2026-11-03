"""Install the botanically reviewed, licensed photographs as versioned siblings."""

import io
import json
import sys
from pathlib import Path
from urllib.parse import quote

from PIL import Image
from qualificar_fotos import read

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
SELECTION = {
    "buxus-sempervirens": [2, 3],
    "crassula-ovata": [2, 6],
    "chlorophytum-comosum": [8, 3],
    "spathiphyllum-wallisii": [4, 7],
    "dracaena-trifasciata": [3, 10],
    "salvia-rosmarinus": [10, 1],
    "chrysalidocarpus-lutescens": [0, 3],
    "cereus-repandus": [5, 6],
    "schlumbergera-truncata": [2, 5],
    "punica-granatum": [3, 0],
    "adenium-obesum": [5, 2],
}


def main():
    base = json.loads((ROOT / "backend/app/photo_manifest.json").read_text(encoding="utf-8"))
    quality = json.loads(
        (ROOT / "backend/app/photo_quality_manifest.json").read_text(encoding="utf-8")
    )
    species = {
        p["slug"]: p
        for p in json.loads(
            (ROOT / "backend/app/botanical_catalog.json").read_text(encoding="utf-8")
        )["species"]
    }
    candidates = {
        slug: json.loads(
            (ROOT / ".local/plant-candidates" / f"{slug}.json").read_text(encoding="utf-8")
        )
        for slug in SELECTION
    }
    selected = [candidates[slug][i] for slug, indices in SELECTION.items() for i in indices]
    titles = "|".join(p["title"] for p in selected)
    request = (
        "https://commons.wikimedia.org/w/api.php?action=query&titles="
        + quote(titles)
        + "&prop=imageinfo&iiprop=url%7Csize&iiurlwidth=1600&format=json"
    )
    response = json.loads(read(request))
    remote = {row["title"]: row["imageinfo"][0] for row in response["query"]["pages"].values()}
    result = []
    for slug, indices in SELECTION.items():
        old = next(row for row in base if row["slug"] == slug)["photos"]
        urls = [p["url"] for p in old]
        urls += [p["url"] for p in quality if p["previous_url"] in urls]
        photos = []
        for number, index in enumerate(indices, 1):
            candidate = candidates[slug][index]
            info = remote[candidate["title"]]
            filename = f"{slug}-catalog-{number}-v1.jpg"
            file = ROOT / "frontend/public/plants" / filename
            if not file.exists():
                raw = read(info.get("thumburl") or info["url"])
                if len(raw) > 10 * 1024 * 1024:
                    raise ValueError("Photo exceeds the asset budget")
                with Image.open(io.BytesIO(raw)) as image:
                    if image.format != "JPEG" or max(image.size) < 1200:
                        raise ValueError("Expected a high-resolution original JPEG photograph")
                file.write_bytes(raw)
            with Image.open(file) as image:
                dimensions = list(image.size)
            photos.append(
                {
                    k: candidate[k]
                    for k in [
                        "author",
                        "license",
                        "license_url",
                        "caption",
                        "source_url",
                        "original_url",
                    ]
                }
                | {
                    "url": "/plants/" + filename,
                    "dimensions": dimensions,
                    "changes": "Fotografia em alta resolução disponibilizada pelo Wikimedia Commons; imagem intacta, centralizada por enquadramento responsivo.",
                }
            )
            print(slug, number, dimensions, flush=True)
        result.append(
            {
                "scientific_name": species[slug]["scientific_name"],
                "previous_urls": urls,
                "photos": photos,
            }
        )
    # These existing photos show the identifying foliage or fruit more clearly.
    for slug in ["monstera-deliciosa", "mentha-spicata", "eugenia-uniflora", "citrus-latifolia"]:
        old = next(row for row in base if row["slug"] == slug)["photos"]
        known = {
            p["previous_url"]: {k: v for k, v in p.items() if k != "previous_url"} for p in quality
        }
        photos = [known.get(p["url"], p) for p in reversed(old)]
        result.append(
            {
                "scientific_name": species[slug]["scientific_name"],
                "previous_urls": [p["url"] for p in old] + [p["url"] for p in photos],
                "photos": photos,
            }
        )
    (ROOT / "backend/app/photo_curated_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
