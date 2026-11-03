import json
from pathlib import Path

from app import product_media
from app.database import SessionLocal
from app.models import Product


def test_demo_images_match_the_sku_without_resetting_sales_or_uploads(client):
    with SessionLocal() as db:
        product = db.get(Product, 2)
        product.name = "Regador verde 2 L"
        product.sku = "AC-016"
        db.commit()
        assert product_media.sync_product_media(db)
        assert product.image_url == "/catalog-media/products/ac-016-v1.png"
        assert product.stock == 1 and product.price_cents == 1000
        product.image_url = "/api/images/own/content"
        db.commit()
        assert not product_media.sync_product_media(db)
        assert product.image_url == "/api/images/own/content"


def test_individual_demo_images_preserve_custom_photos_and_renamed_items(client):
    with SessionLocal() as db:
        pot = db.get(Product, 2)
        pot.sku = "AC-016"
        pot.name = "Regador verde 2 L"
        pot.image_url = "/api/images/my-real-photo/content"
        plant = db.get(Product, 1)
        plant.sku = "FE-015"
        plant.name = "Outro produto com nome alterado"
        db.commit()
        product_media.sync_product_media(db)
        assert pot.image_url == "/api/images/my-real-photo/content"
        assert plant.image_url == ""


def test_every_demo_sku_has_its_own_existing_picture():
    root = Path(__file__).resolve().parents[2]
    entries = json.loads(
        Path(product_media.__file__)
        .with_name("product_media_manifest.json")
        .read_text(encoding="utf-8")
    )
    assert len(entries) == 21 and len({row["url"] for row in entries}) == 21
    for row in entries:
        assert (root / "frontend/public" / row["url"].lstrip("/")).is_file()
