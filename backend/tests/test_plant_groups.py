from app.catalog import sync_catalog
from app.database import SessionLocal
from app.models import Species


def test_catalog_groups_cover_all_species_and_filters(client):
    with SessionLocal() as db:
        sync_catalog(db)
    species = client.get("/api/species").json()
    assert len(species) == 40
    assert all(row["plant_groups"] for row in species)
    groups = {group for row in species for group in row["plant_groups"]}
    assert {
        "Cactos",
        "Frutíferas",
        "Flores",
        "Folhagens",
        "Suculentas",
        "Aromáticas e temperos",
        "Palmeiras",
        "Samambaias",
        "Trepadeiras",
        "Cercas vivas",
        "Ornamentais",
    } <= groups
    for group, count in [("Cactos", 4), ("Frutíferas", 6), ("Palmeiras", 2), ("Samambaias", 1)]:
        filtered = client.get("/api/species", params={"group": group}).json()
        assert len(filtered) == count
        assert all(group in row["plant_groups"] for row in filtered)
    assert "Lavanda" in {
        row["name"]
        for row in client.get("/api/species", params={"group": "Aromáticas e temperos"}).json()
    }


def test_new_species_without_known_group_remains_filterable(client):
    with SessionLocal() as db:
        db.add(
            Species(
                name="Espécie nova",
                scientific_name="Species exemplo",
                light="Sol pleno",
                watering="Moderada",
                size="Pequeno",
                environment="Externo",
                difficulty="Baixa",
                use="Uso especial",
                description="",
            )
        )
        db.commit()
    result = client.get("/api/species", params={"group": "Outras plantas"}).json()
    assert [row["name"] for row in result] == ["Espécie nova"]
