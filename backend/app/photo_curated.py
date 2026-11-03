"""Apply reviewed botanical pictures without overwriting a customer's own images."""

import json
from pathlib import Path

from sqlalchemy import select

from .models import CatalogVersion, Product, Species

VERSION = "botanical-photo-review-2026-10-10-v1"


def sync_curated_photos(db):
    if db.get(CatalogVersion, VERSION):
        return False
    entries = json.loads(
        Path(__file__).with_name("photo_curated_manifest.json").read_text(encoding="utf-8")
    )
    for entry in entries:
        row = db.scalar(select(Species).where(Species.scientific_name == entry["scientific_name"]))
        if not row:
            continue
        old = set(entry["previous_urls"])
        existing = row.photos or []
        # Keep other photos in their original order. Removing or replacing the
        # demo gallery in the admin is also respected.
        if any(p.get("url") in old for p in existing):
            row.photos = entry["photos"] + [p for p in existing if p.get("url") not in old]
        if row.image_url in old:
            row.image_url = entry["photos"][0]["url"]
        for product in db.scalars(select(Product).where(Product.species_id == row.id)):
            if product.image_url in old:
                product.image_url = entry["photos"][0]["url"]
    db.add(CatalogVersion(version=VERSION))
    db.commit()
    return True
