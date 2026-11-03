"""Versioned, source-based botanical catalog. Never resets business records."""

import json
import os
from pathlib import Path

from sqlalchemy import select

from .models import Article, CatalogVersion, Product, Service, Setting, Species, StockMove, User

VERSION = "atelie-verde-botany-2026-10-04-v1"


def sync_catalog(db):
    if db.get(CatalogVersion, VERSION):
        return False
    content = json.loads(
        Path(__file__).with_name("botanical_catalog.json").read_text(encoding="utf-8")
    )
    photos = {
        p["slug"]: p["photos"]
        for p in json.loads(
            Path(__file__).with_name("photo_manifest.json").read_text(encoding="utf-8")
        )
    }
    species_by_name = {}
    for item in content["species"]:
        fields = dict(item)
        slug = fields.pop("slug")
        row = db.scalar(select(Species).where(Species.scientific_name == fields["scientific_name"]))
        if not row:
            row = db.scalar(select(Species).where(Species.name == fields["name"]))
        if not row:
            row = Species(**fields)
            db.add(row)
        else:
            for key, value in fields.items():
                setattr(row, key, value)
        row.photos = photos.get(slug, [])
        if row.photos and not (row.image_url or "").startswith("/api/images/"):
            row.image_url = row.photos[0]["url"]
            row.demo_asset = ""
        db.flush()
        species_by_name[row.name] = row.id
        products = list(db.scalars(select(Product).where(Product.species_id == row.id)))
        for product in products:
            if not product.image_url.startswith("/api/images/"):
                product.image_url = row.image_url
                product.demo_asset = ""
            product.description = row.description
        if not products:
            demo = (
                os.getenv("SEED_DEMO", "false").lower() == "true"
                and os.getenv("APP_ENV", "development") != "production"
            )
            actor = db.scalar(select(User).where(User.role == "admin").order_by(User.id))
            stock = 12 if demo and actor else 0
            price = 7990 if "Frutíferas" in row.use else 2490 if "Cactos" in row.use else 2990
            product = Product(
                name=row.name,
                category="Plantas",
                description=row.description,
                price_cents=price,
                stock=stock,
                low_stock=5,
                species_id=row.id,
                sku=f"AV-{slug.upper()}",
                location="Viveiro",
                image_url=row.image_url,
            )
            db.add(product)
            db.flush()
            if stock:
                db.add(
                    StockMove(
                        product_id=product.id,
                        quantity=stock,
                        reason="Cadastro inicial de demonstração · catálogo botânico",
                        actor_id=actor.id,
                    )
                )
    for entry in content["articles"]:
        fields = dict(entry)
        fields["species_id"] = species_by_name[fields.pop("species_name")]
        row = db.scalar(select(Article).where(Article.slug == fields["slug"]))
        if not row:
            db.add(Article(**fields))
        else:
            for key, value in fields.items():
                setattr(row, key, value)
    for service in db.scalars(select(Service)):
        service.responsible = service.responsible.replace("GreenScape", "Ateliê Verde")
    for setting in db.scalars(select(Setting)):
        value = dict(setting.value)
        if value.get("name") == "GreenScape":
            value["name"] = "Ateliê Verde"
        setting.value = value
    from .security import passwords

    for account in db.scalars(
        select(User).where(User.email.in_(["admin@greenscape.local", "cliente@greenscape.local"]))
    ):
        account.email = account.email.replace("@greenscape.local", "@atelieverde.local")
        if passwords.verify("GreenScape@2026", account.password_hash):
            account.password_hash = passwords.hash("AtelieVerde@2026")
    db.add(CatalogVersion(version=VERSION))
    db.commit()
    return True


if __name__ == "__main__":
    from .database import SessionLocal

    with SessionLocal() as session:
        changed = sync_catalog(session)
        print("Catálogo atualizado." if changed else "Catálogo já atualizado.")
