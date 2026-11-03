import io

from app.catalog import sync_catalog
from app.database import SessionLocal
from app.models import Article, LearningProgress, Product, Species
from PIL import Image
from sqlalchemy import select


def test_profile_cannot_change_role_or_another_user(client, auth):
    body = {"name": "Meu nome", "email": "ONE@test.local", "city": "Campinas - SP"}
    assert (
        client.put(
            "/api/auth/profile", headers=auth["one"], json={**body, "role": "admin"}
        ).status_code
        == 422
    )
    result = client.put("/api/auth/profile", headers=auth["one"], json=body)
    assert result.status_code == 200
    assert result.json()["email"] == "one@test.local"
    assert result.json()["role"] == "customer"
    assert client.get("/api/auth/me", headers=auth["two"]).json()["name"] == "Cliente dois"
    assert (
        client.put(
            "/api/auth/profile", headers=auth["one"], json={**body, "email": "two@test.local"}
        ).status_code
        == 409
    )
    assert client.get("/api/auth/me", headers=auth["one"]).json()["email"] == "one@test.local"


def test_avatar_replacement_and_ownership(client, auth):
    buffer = io.BytesIO()
    Image.new("RGB", (30, 20), "green").save(buffer, "PNG")
    files = {"file": ("perfil.png", buffer.getvalue(), "image/png")}
    assert client.get("/api/auth/me", headers=auth["one"]).json()["avatar_url"] == ""
    assert client.post("/api/images/users/3", headers=auth["one"], files=files).status_code == 404
    first = client.post("/api/images/users/2", headers=auth["one"], files=files)
    assert first.status_code == 201
    original = first.json()
    assert client.get(original["url"], headers=auth["two"]).status_code == 404
    replacement = client.post("/api/images/users/2", headers=auth["one"], files=files).json()
    assert replacement["id"] != original["id"]
    assert client.get(original["url"], headers=auth["one"]).status_code == 404
    assert (
        client.get("/api/auth/me", headers=auth["one"]).json()["avatar_url"] == replacement["url"]
    )
    assert client.delete(f"/api/images/{replacement['id']}", headers=auth["two"]).status_code == 404
    assert client.delete(f"/api/images/{replacement['id']}", headers=auth["one"]).status_code == 204
    assert client.get("/api/auth/me", headers=auth["one"]).json()["avatar_url"] == ""


def test_learning_is_idempotent_and_private(client, auth):
    with SessionLocal() as db:
        db.add(
            Article(
                id=1,
                slug="rega",
                title="Rega",
                category="Rega",
                summary="Cuidados",
                minutes=3,
                species_id=1,
                sections=[],
                sources=[],
            )
        )
        db.commit()
    assert client.get("/api/learning").status_code == 200
    assert client.put("/api/learning/1/complete").status_code == 401
    for _ in range(2):
        assert client.put("/api/learning/1/complete", headers=auth["one"]).status_code == 200
    assert len(client.get("/api/learning/progress", headers=auth["one"]).json()) == 1
    assert client.get("/api/learning/progress", headers=auth["two"]).json() == []
    client.delete("/api/learning/1/complete", headers=auth["two"])
    with SessionLocal() as db:
        assert len(list(db.scalars(select(LearningProgress)))) == 1
    assert client.delete("/api/learning/1/complete", headers=auth["one"]).status_code == 204
    assert client.get("/api/learning/progress", headers=auth["one"]).json() == []


def test_catalog_all_species_for_sale_preserves_existing_stock(client):
    with SessionLocal() as db:
        assert sync_catalog(db)
        species = list(db.scalars(select(Species)))
        assert len(species) == 40
        assert len(list(db.scalars(select(Article)))) == 10
        for plant in species:
            product = db.scalar(select(Product).where(Product.species_id == plant.id))
            assert product and product.active and product.price_cents > 0
            assert plant.photos and plant.substrate and plant.care and plant.sources
            assert product.image_url == plant.photos[0]["url"]
            assert all(p["author"] and p["license"] and p["source_url"] for p in plant.photos)
        assert len([s for s in species if "Cactos" in s.use]) == 4
        assert len([s for s in species if "Frutíferas" in s.use]) == 6
        assert db.get(Product, 1).stock == 5
        assert db.get(Product, 1).price_cents == 2490
        db.get(Product, 1).stock = 3
        db.get(Species, 1).care = "Cuidados personalizados"
        db.commit()
        assert not sync_catalog(db)
        assert db.get(Product, 1).stock == 3
        assert db.get(Species, 1).care == "Cuidados personalizados"
