from app.customer_activity_demo import VERSION, seed_customer_activity
from app.database import SessionLocal
from app.models import Appointment, CatalogVersion, Ledger, Project, StockMove, User
from app.schemas import LandscapeBrief, ProjectInput
from sqlalchemy import func, select


def accounts(db):
    db.get(User, 1).email = "admin@atelieverde.local"
    db.get(User, 2).email = "cliente@atelieverde.local"
    db.commit()


def test_only_demo_profiles_are_completed_once_and_keep_private_access(client, auth):
    with SessionLocal() as db:
        assert seed_customer_activity(db) == {"projetos": 0, "servicos": 0, "recebimentos": 0}
        assert db.get(CatalogVersion, VERSION) is None
        accounts(db)
        other = db.get(User, 3)
        before = (other.name, other.email, other.notes, other.password_hash)
        assert seed_customer_activity(db) == {"projetos": 1, "servicos": 1, "recebimentos": 1}
        assert seed_customer_activity(db) == {"projetos": 0, "servicos": 0, "recebimentos": 0}
        project = db.scalar(select(Project))
        LandscapeBrief.model_validate(project.brief)
        ProjectInput.model_validate(
            {column.name: getattr(project, column.name) for column in project.__table__.columns}
        )
        assert project.customer_id == 2 and project.status == "Orçamento"
        appointment = db.scalar(select(Appointment))
        receipt = db.scalar(select(Ledger))
        assert appointment.customer_id == receipt.customer_id == 2
        assert receipt.amount_cents == appointment.amount_cents and receipt.status == "Pago"
        assert (other.name, other.email, other.notes, other.password_hash) == before
        assert db.scalar(select(func.count()).select_from(StockMove)) == 0
    assert len(client.get("/api/projects", headers=auth["one"]).json()) == 1
    assert client.get("/api/projects", headers=auth["two"]).json() == []


def test_existing_payments_are_used_without_generating_duplicate_income(client):
    with SessionLocal() as db:
        accounts(db)
        for source, amount in [("Projetos", 120000), ("Serviços", 35000)]:
            db.add(
                Ledger(
                    direction="Receita",
                    source=source,
                    customer_id=2,
                    counterparty="Cliente um",
                    description=f"Histórico de {source}",
                    due_date="2026-10-01",
                    paid_date="2026-10-01",
                    amount_cents=amount,
                    status="Pago",
                )
            )
        db.commit()
        before = [
            (r.id, r.description, r.amount_cents, r.paid_date)
            for r in db.scalars(select(Ledger).order_by(Ledger.id))
        ]
        assert seed_customer_activity(db) == {"projetos": 1, "servicos": 1, "recebimentos": 0}
        project = db.scalar(select(Project))
        assert project.budget_cents == 120000 and project.status == "Finalizado"
        assert project.end_date == "2026-10-01"
        assert db.scalar(select(Appointment)).amount_cents == 35000
        assert [
            (r.id, r.description, r.amount_cents, r.paid_date)
            for r in db.scalars(select(Ledger).order_by(Ledger.id))
        ] == before


def test_inactive_demo_clients_are_not_populated(client):
    with SessionLocal() as db:
        accounts(db)
        db.get(User, 2).active = False
        db.commit()
        assert seed_customer_activity(db) == {"projetos": 0, "servicos": 0, "recebimentos": 0}
        assert db.get(CatalogVersion, VERSION) is None
