import io

import pytest
from app.database import SessionLocal
from app.models import Document, Service
from PIL import Image as PILImage
from sqlalchemy import select


@pytest.fixture
def virtual(client):
    with SessionLocal() as db:
        row = Service(
            name="Paisagista virtual",
            description="Planejamento remoto",
            category="Projeto",
            price_cents=90000,
            unit="projeto",
            delivery_mode="Virtual",
        )
        db.add(row)
        db.commit()
        return row.id


def brief():
    return {
        "width": 10,
        "length": 8,
        "light": "Sol pleno",
        "soil": "Solo arenoso",
        "plantings": [
            {
                "species_id": 1,
                "quantity": 4,
                "x": 2,
                "y": 3,
                "diameter": 1,
                "application": "Canteiro",
            }
        ],
        "zones": [{"name": "Caminho", "kind": "Caminho", "x": 5, "y": 0, "width": 1, "length": 8}],
    }


def request(client, auth, id):
    response = client.post(
        "/api/quotes",
        headers=auth["one"],
        json={
            "service_id": id,
            "area": 999,
            "address": "Rua do jardim, 10",
            "description": "Jardim de flores",
            "brief": brief(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_services_describe_work_and_virtual_requires_brief(client, auth, virtual):
    service = next(s for s in client.get("/api/services").json() if s["id"] == virtual)
    assert service["delivery_mode"] == "Virtual"
    assert (
        service["details"]["includes"]
        and service["details"]["documents"]
        and service["details"]["deliverables"]
    )
    assert (
        client.post(
            "/api/quotes",
            headers=auth["one"],
            json={"service_id": virtual, "area": 80, "address": "Rua do jardim, 10"},
        ).status_code
        == 422
    )


def test_virtual_plan_is_preserved_on_approval(client, auth, virtual):
    quote = request(client, auth, virtual)
    assert quote["area"] == 80 and quote["plants"][0]["quantity"] == 4
    assert (
        client.patch(
            f"/api/quotes/{quote['id']}/price", headers=auth["admin"], json={"amount_cents": 150000}
        ).status_code
        == 200
    )
    response = client.post(f"/api/quotes/{quote['id']}/approve", headers=auth["one"])
    assert response.status_code == 200
    project = response.json()
    assert project["delivery_mode"] == "Virtual" and project["brief"] == quote["brief"]
    assert project["area"] == 80 and project["plants"] == quote["plants"]


def test_plan_validates_geometry_species_owner_and_revision(client, auth, virtual):
    quote = request(client, auth, virtual)
    url = f"/api/quotes/{quote['id']}/brief"
    assert client.put(url, headers=auth["two"], json={"brief": brief()}).status_code == 404
    bad = brief()
    bad["plantings"][0]["x"] = 20
    assert client.put(url, headers=auth["one"], json={"brief": bad}).status_code == 422
    bad = brief()
    bad["plantings"][0]["species_id"] = 999
    assert client.put(url, headers=auth["one"], json={"brief": bad}).status_code == 422
    good = brief()
    good["plantings"][0]["quantity"] = 6
    response = client.put(url, headers=auth["one"], json={"brief": good, "expected_revision": 0})
    assert response.status_code == 200 and response.json()["brief_revision"] == 1
    assert (
        client.put(
            url, headers=auth["one"], json={"brief": good, "expected_revision": 0}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/quotes/{quote['id']}/price", headers=auth["admin"], json={"amount_cents": 150000}
        ).status_code
        == 200
    )
    assert (
        client.put(
            url, headers=auth["one"], json={"brief": good, "expected_revision": 1}
        ).status_code
        == 409
    )


def test_private_quote_documents_follow_project_without_copying(client, auth, virtual):
    quote = request(client, auth, virtual)
    base = f"/api/quotes/{quote['id']}/documents"
    pdf = ("medidas.pdf", b"%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF", "application/pdf")
    assert client.post(base, headers=auth["two"], files={"file": pdf}).status_code == 404
    assert (
        client.post(
            base, headers=auth["one"], files={"file": ("bad.pdf", b"not pdf", "application/pdf")}
        ).status_code
        == 422
    )
    response = client.post(base, headers=auth["one"], files={"file": pdf})
    assert response.status_code == 201
    document = response.json()
    assert (
        client.get(f"/api/documents/{document['id']}/content", headers=auth["two"]).status_code
        == 404
    )
    assert (
        client.get(f"/api/documents/{document['id']}/content", headers=auth["one"]).status_code
        == 200
    )
    image = io.BytesIO()
    PILImage.new("RGB", (20, 20), "green").save(image, "PNG")
    photo = client.post(
        f"/api/images/quotes/{quote['id']}",
        headers=auth["one"],
        files={"file": ("local.png", image.getvalue(), "image/png")},
    )
    assert photo.status_code == 201
    client.patch(
        f"/api/quotes/{quote['id']}/price", headers=auth["admin"], json={"amount_cents": 150000}
    )
    project = client.post(f"/api/quotes/{quote['id']}/approve", headers=auth["one"]).json()
    assert (
        client.get(f"/api/projects/{project['id']}/documents", headers=auth["one"]).json()[0]["id"]
        == document["id"]
    )
    assert (
        client.get(f"/api/images/projects/{project['id']}", headers=auth["one"]).json()[0]["id"]
        == photo.json()["id"]
    )
    assert client.delete(f"/api/documents/{document['id']}", headers=auth["one"]).status_code == 409
    assert client.post(base, headers=auth["one"], files={"file": pdf}).status_code == 409
    assert (
        client.get(f"/api/projects/{project['id']}/documents", headers=auth["two"]).status_code
        == 404
    )
    with SessionLocal() as db:
        assert len(db.scalars(select(Document)).all()) == 1


def test_only_team_can_revise_project_plan(client, auth, virtual):
    quote = request(client, auth, virtual)
    client.patch(
        f"/api/quotes/{quote['id']}/price", headers=auth["admin"], json={"amount_cents": 150000}
    )
    project = client.post(f"/api/quotes/{quote['id']}/approve", headers=auth["one"]).json()
    body = {"brief": brief(), "expected_revision": 0}
    url = f"/api/projects/{project['id']}/brief"
    assert client.put(url, headers=auth["one"], json=body).status_code == 403
    assert client.put(url, headers=auth["admin"], json=body).status_code == 200
    assert client.put(url, headers=auth["admin"], json=body).status_code == 409
