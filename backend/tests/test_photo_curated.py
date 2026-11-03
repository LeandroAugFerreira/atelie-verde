import json
from pathlib import Path

from app import photo_curated
from app.database import SessionLocal
from app.models import Product, Species


def test_botanical_review_replaces_old_demo_photos_and_keeps_uploaded_photos(client):
    entries = json.loads(
        Path(photo_curated.__file__)
        .with_name("photo_curated_manifest.json")
        .read_text(encoding="utf-8")
    )
    entry = entries[0]
    old = entry["previous_urls"][0]
    with SessionLocal() as db:
        species = db.get(Species, 1)
        species.scientific_name = entry["scientific_name"]
        species.image_url = "/api/images/my-buxus/content"
        species.photos = [{"url": old}, {"url": "/api/images/another/content"}]
        species.description = "Minha descrição preservada"
        plant = db.get(Product, 1)
        plant.image_url = old
        plant.description = "Produto específico"
        db.commit()
        assert photo_curated.sync_curated_photos(db)
        assert species.image_url == "/api/images/my-buxus/content"
        assert species.photos[-1]["url"] == "/api/images/another/content"
        assert species.photos[0]["url"] == entry["photos"][0]["url"]
        assert species.description == "Minha descrição preservada"
        assert (
            plant.image_url == entry["photos"][0]["url"]
            and plant.description == "Produto específico"
        )
        assert plant.stock == 5 and plant.price_cents == 2490
        assert not photo_curated.sync_curated_photos(db)


def test_reviewed_photos_exist_have_credits_and_distinct_views():
    root = Path(__file__).resolve().parents[2]
    entries = json.loads(
        Path(photo_curated.__file__)
        .with_name("photo_curated_manifest.json")
        .read_text(encoding="utf-8")
    )
    assert len(entries) == 15
    for entry in entries:
        assert len({p["original_url"] for p in entry["photos"]}) == len(entry["photos"])
        for photo in entry["photos"]:
            assert (
                photo["author"] and photo["license"] and photo["source_url"].startswith("https://")
            )
            assert (root / "frontend/public" / photo["url"].lstrip("/")).is_file()
