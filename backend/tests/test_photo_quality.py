import json
from pathlib import Path

from app import photo_quality
from app.database import SessionLocal
from app.models import Product, Species


def test_resolution_upgrade_preserves_business_records_and_custom_uploads(client):
    manifest = json.loads(
        Path(photo_quality.__file__)
        .with_name("photo_quality_manifest.json")
        .read_text(encoding="utf-8")
    )
    old = manifest[0]["previous_url"]
    new = manifest[0]["url"]
    with SessionLocal() as db:
        species = db.get(Species, 1)
        species.image_url = "/api/images/custom/content"
        species.description = "Descrição editada pelo administrador"
        species.photos = [{"url": old}, {"url": "/api/images/custom/content", "author": "Cliente"}]
        plant = db.get(Product, 1)
        plant.image_url = old
        plant.description = "Outra descrição editada"
        pot = db.get(Product, 2)
        pot.image_url = "/api/images/pot/content"
        db.commit()
        assert photo_quality.sync_photo_quality(db)
        assert species.image_url == "/api/images/custom/content"
        assert species.photos[0]["url"] == new and species.photos[0]["license"]
        assert species.photos[1] == {"url": "/api/images/custom/content", "author": "Cliente"}
        assert plant.image_url == new and plant.description == "Outra descrição editada"
        assert plant.stock == 5 and plant.price_cents == 2490
        assert pot.image_url == "/api/images/pot/content"
        species.photos = []
        db.commit()
        assert not photo_quality.sync_photo_quality(db)
        assert species.photos == []
