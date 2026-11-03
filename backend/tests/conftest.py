import os
import tempfile
from pathlib import Path

# TEST_DATABASE_URL points only to a disposable database; never touch DATABASE_URL.
TEST_DATA = tempfile.TemporaryDirectory(prefix="greenscape-tests-")
os.environ["DATA_DIR"] = TEST_DATA.name
os.environ["RAFINHA_CREDENTIALS_DIR"] = str(Path(TEST_DATA.name) / "credentials")
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", f"sqlite:///{Path(TEST_DATA.name).as_posix()}/tests.db"
)
os.environ["SEED_DEMO"] = "false"
os.environ["RAFINHA_PROVIDER"] = "catalog"
os.environ["RAFINHA_MODE"] = "hybrid"
os.environ["RAFINHA_ALLOW_DEV_API_KEYS"] = "false"
os.environ["JWT_SECRET"] = "isolated-test-secret-with-more-than-32-characters"

import pytest
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Product, Service, Species, User
from app.security import passwords
from fastapi.testclient import TestClient

HASH = passwords.hash("TestPassword@2026")


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    TEST_DATA.cleanup()


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # Let both PostgreSQL sequences and SQLite allocate the initial IDs.
    # Explicit IDs leave PostgreSQL sequences behind and break later inserts.
    with SessionLocal() as db:
        db.add_all(
            [
                User(
                    name="Admin", email="admin@test.local", role="admin", password_hash=HASH
                ),
                User(name="Cliente um", email="one@test.local", password_hash=HASH),
                User(name="Cliente dois", email="two@test.local", password_hash=HASH),
            ]
        )
        db.add(
            Species(
                name="Lavanda",
                scientific_name="Lavandula dentata",
                light="Sol pleno",
                watering="Baixa",
                size="Pequeno",
                environment="Externo",
                difficulty="Baixa",
                use="Flores",
                description="Espécie de teste",
            )
        )
        db.flush()
        db.add_all(
            [
                Product(
                    name="Lavanda",
                    sku="PL-001",
                    category="Plantas",
                    description="",
                    price_cents=2490,
                    stock=5,
                    low_stock=2,
                    species_id=1,
                ),
                Product(
                    name="Vaso",
                    sku="VA-001",
                    category="Vasos",
                    description="",
                    price_cents=1000,
                    stock=1,
                    low_stock=2,
                ),
                Service(name="Poda", description="", price_cents=25000, unit="visita"),
            ]
        )
        db.commit()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth(client):
    return {
        key: {
            "Authorization": "Bearer "
            + client.post(
                "/api/auth/login", json={"email": email, "password": "TestPassword@2026"}
            ).json()["access_token"]
        }
        for key, email in [
            ("admin", "admin@test.local"),
            ("one", "one@test.local"),
            ("two", "two@test.local"),
        ]
    }
