"""Assign individual pictures only to the known demo SKUs; preserve uploaded photos."""

import json
from pathlib import Path

from sqlalchemy import select

from .models import CatalogVersion, Product

VERSION = "demo-individual-product-photos-2026-10-10-v1"


def sync_product_media(db):
    if db.get(CatalogVersion, VERSION):
        return False
    manifest = json.loads(
        Path(__file__).with_name("product_media_manifest.json").read_text(encoding="utf-8")
    )
    by_sku = {row["sku"]: row for row in manifest}
    for product in db.scalars(select(Product).where(Product.sku.in_(by_sku))):
        entry = by_sku[product.sku]
        if product.name != entry["name"] or product.image_url:
            continue
        product.image_url = entry["url"]
    db.add(CatalogVersion(version=VERSION))
    db.commit()
    return True
