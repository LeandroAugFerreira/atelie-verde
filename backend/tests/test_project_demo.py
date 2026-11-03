from app.database import SessionLocal
from app.models import Project, ProjectEvent, Species, StockMove, User
from app.project_demo import SCENARIOS, seed_project_portfolio
from app.schemas import LandscapeBrief, ProjectInput
from sqlalchemy import func, select


def demo_accounts(db):
    db.get(User, 1).email = "admin@atelieverde.local"
    db.get(User, 2).email = "cliente@atelieverde.local"
    known = set(db.scalars(select(Species.name)))
    for name in {name for row in SCENARIOS for name in row[9]} - known:
        db.add(
            Species(
                name=name,
                scientific_name=name,
                light="Sol pleno",
                watering="Moderada",
                size="Pequeno",
                environment="Externo",
                difficulty="Baixa",
                use="Ornamental",
                description="Espécie demonstrativa",
            )
        )
    db.commit()


def test_demo_projects_are_complete_private_and_added_only_once(client, auth):
    with SessionLocal() as db:
        demo_accounts(db)
        assert seed_project_portfolio(db) == 6
        assert seed_project_portfolio(db) == 0
        rows = list(db.scalars(select(Project)))
        assert {row.status for row in rows} == {
            "Orçamento",
            "Aprovado",
            "Planejamento",
            "Execução",
            "Finalizado",
            "Manutenção",
        }
        for row in rows:
            assert row.customer_id == 2 and row.reference_image_url.startswith("/projects/")
            assert row.plants and row.materials and row.services and len(row.tasks) == 4
            LandscapeBrief.model_validate(row.brief)
            ProjectInput.model_validate(
                {column.name: getattr(row, column.name) for column in row.__table__.columns}
            )
        assert db.scalar(select(func.count()).select_from(ProjectEvent)) == 21
        assert not db.scalars(select(StockMove)).all()
    assert len(client.get("/api/projects", headers=auth["one"]).json()) == 6
    assert not client.get("/api/projects", headers=auth["two"]).json()


def test_demo_seed_requires_demo_accounts_and_preserves_existing_projects(client):
    with SessionLocal() as db:
        assert seed_project_portfolio(db) == 0
        demo_accounts(db)
        name = SCENARIOS[0][0]
        original = Project(
            name=name,
            customer_id=2,
            address="Endereço preservado",
            area=10,
            budget_cents=32100,
            start_date="2026-10-01",
            end_date="2026-10-20",
            status="Orçamento",
            description="Descrição editada",
        )
        db.add(original)
        db.commit()
        assert seed_project_portfolio(db) == 5
        assert original.description == "Descrição editada" and original.budget_cents == 32100
