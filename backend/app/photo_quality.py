"""Upgrade bundled catalog photos while preserving customer uploads and business data."""

import json
from pathlib import Path

from sqlalchemy import select

from .models import CatalogVersion, Product, Species

VERSION = "atelie-verde-photos-2026-10-10-v1"


def sync_photo_quality(db):
    if db.get(CatalogVersion, VERSION):
        return False
    manifest = json.loads(
        Path(__file__).with_name("photo_quality_manifest.json").read_text(encoding="utf-8")
    )
    replacements = {
        item["previous_url"]: {k: v for k, v in item.items() if k != "previous_url"}
        for item in manifest
    }
    for species in db.scalars(select(Species)):
        photos = species.photos or []
        if any(photo.get("url") in replacements for photo in photos):
            species.photos = [replacements.get(photo.get("url"), photo) for photo in photos]
        if species.image_url in replacements:
            species.image_url = replacements[species.image_url]["url"]
    for product in db.scalars(select(Product)):
        if product.image_url in replacements:
            product.image_url = replacements[product.image_url]["url"]
    db.add(CatalogVersion(version=VERSION))
    db.commit()
    return True
