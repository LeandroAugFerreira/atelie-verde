from app.database import SessionLocal
from app.models import Image, Project
from app.project_references import REFERENCES, sync_project_references
from sqlalchemy import select


def test_project_references_preserve_business_and_uploaded_photos(client, auth):
    with SessionLocal() as db:
        for name in [*REFERENCES, "Novo projeto real"]:
            db.add(
                Project(
                    name=name,
                    customer_id=2,
                    address="Endereço real",
                    area=45,
                    budget_cents=321000,
                    status="Execução",
                    start_date="2026-10-01",
                    end_date="2026-11-01",
                    plants=[{"species_id": 1, "quantity": 3}],
                )
            )
        db.flush()
        first = db.scalar(select(Project).order_by(Project.id))
        db.add(Image(owner_id=1, entity="projects", entity_id=first.id, filename="foto-real.png"))
        db.commit()
        assert sync_project_references(db)
        projects = db.scalars(select(Project).order_by(Project.id)).all()
        assert len({p.reference_image_url for p in projects[:5]}) == 5
        assert all(
            p.reference_image_note and "ilustrativa" in p.reference_image_note for p in projects[:5]
        )
        assert projects[-1].reference_image_url == ""
        assert all(
            p.budget_cents == 321000 and p.status == "Execução" and p.plants[0]["quantity"] == 3
            for p in projects
        )
        assert db.scalar(select(Image)).filename == "foto-real.png"
        first.reference_image_url = "/projects/referencia-personalizada.png"
        db.commit()
        assert not sync_project_references(db)
        assert first.reference_image_url.endswith("referencia-personalizada.png")
    own = client.get("/api/projects", headers=auth["one"]).json()
    assert len(own) == 6
    assert (
        next(p for p in own if p["name"] == "Varanda viva · Pinheiros")["reference_image_url"]
        == "/projects/varanda-pinheiros.png"
    )
    assert client.get("/api/projects", headers=auth["two"]).json() == []
