import io
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from app.database import SessionLocal
from app.models import Ledger, Order, Product
from PIL import Image
from sqlalchemy import select


def order(client, auth, items=None):
    return client.post(
        "/api/orders",
        headers=auth["one"],
        json={"items": items or [{"product_id": 1, "quantity": 2}]},
    )


def quote(client, auth):
    return client.post(
        "/api/quotes",
        headers=auth["one"],
        json={
            "service_id": 1,
            "area": 85,
            "address": "Rua das Flores, 123",
            "description": "Jardim frontal",
        },
    ).json()


def test_auth_and_roles(client, auth):
    assert (
        client.post(
            "/api/auth/login", json={"email": "admin@test.local", "password": "wrong"}
        ).status_code
        == 401
    )
    assert client.get("/api/customers", headers=auth["one"]).status_code == 403
    assert client.get("/api/ledger", headers=auth["one"]).status_code == 403
    assert client.get("/api/projects", headers={"Authorization": "Bearer fake"}).status_code == 401
    assert "password_hash" not in client.get("/api/auth/me", headers=auth["one"]).json()


def test_registration_never_grants_admin(client):
    body = {
        "name": "Novo cliente",
        "email": "NEW@test.local",
        "password": "TestPassword@2026",
        "role": "admin",
    }
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201 and r.json()["user"]["role"] == "customer"
    assert client.post("/api/auth/register", json=body).status_code == 409


def test_order_price_and_stock_from_database(client, auth):
    r = order(client, auth, [{"product_id": 1, "quantity": 2, "price_cents": 1}])
    assert r.status_code == 201 and r.json()["total_cents"] == 4980
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 3
        assert (
            db.scalar(select(Ledger).where(Ledger.order_id == r.json()["id"])).status == "Pendente"
        )


def test_multiline_order_rolls_back_on_insufficient_stock(client, auth):
    assert (
        order(
            client, auth, [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 2}]
        ).status_code
        == 409
    )
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 5
        assert not db.scalar(select(Order.id))


def test_duplicate_lines_aggregate_stock(client, auth):
    assert (
        order(
            client, auth, [{"product_id": 1, "quantity": 3}, {"product_id": 1, "quantity": 3}]
        ).status_code
        == 409
    )


def test_cancellation_exactly_once_and_ownership(client, auth):
    id = order(client, auth).json()["id"]
    assert client.post(f"/api/orders/{id}/cancel", headers=auth["two"]).status_code == 404
    assert client.post(f"/api/orders/{id}/cancel", headers=auth["one"]).status_code == 200
    assert client.post(f"/api/orders/{id}/cancel", headers=auth["one"]).status_code == 409
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 5
        assert db.scalar(select(Ledger).where(Ledger.order_id == id)).status == "Cancelado"


def test_stock_guard_and_audit(client, auth):
    assert (
        client.post(
            "/api/products/1/stock", headers=auth["admin"], json={"quantity": -6, "reason": "Perda"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/products/1/stock",
            headers=auth["admin"],
            json={"quantity": 3, "reason": "Reposição"},
        ).status_code
        == 200
    )
    assert client.get("/api/stock-moves", headers=auth["admin"]).json()[0]["quantity"] == 3


def test_concurrent_last_unit_is_sold_once(client, auth):
    def buy(_):
        return order(client, auth, [{"product_id": 2, "quantity": 1}]).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(buy, range(2)))
    assert sorted(statuses) == [201, 409]
    with SessionLocal() as db:
        assert db.get(Product, 2).stock == 0


def test_quote_approval_preserves_plan_and_is_unique(client, auth):
    q = quote(client, auth)
    assert client.post(f"/api/quotes/{q['id']}/approve", headers=auth["one"]).status_code == 409
    price = {
        "amount_cents": 180000,
        "plants": [{"species_id": 1, "quantity": 6, "application": "Bordadura"}],
        "materials": [{"name": "Substrato", "quantity": 10, "unit_price_cents": 2990}],
    }
    assert (
        client.patch(f"/api/quotes/{q['id']}/price", headers=auth["admin"], json=price).status_code
        == 200
    )
    assert client.post(f"/api/quotes/{q['id']}/approve", headers=auth["two"]).status_code == 404
    r = client.post(f"/api/quotes/{q['id']}/approve", headers=auth["one"])
    assert r.status_code == 200 and r.json()["plants"][0]["application"] == "Bordadura"
    assert client.post(f"/api/quotes/{q['id']}/approve", headers=auth["one"]).status_code == 409
    assert client.get("/api/projects", headers=auth["two"]).json() == []


def test_project_stages_cannot_be_skipped(client, auth):
    q = quote(client, auth)
    client.patch(
        f"/api/quotes/{q['id']}/price", headers=auth["admin"], json={"amount_cents": 100000}
    )
    p = client.post(f"/api/quotes/{q['id']}/approve", headers=auth["one"]).json()
    assert (
        client.patch(
            f"/api/projects/{p['id']}/status", headers=auth["admin"], json={"status": "Finalizado"}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/projects/{p['id']}/status",
            headers=auth["admin"],
            json={"status": "Planejamento"},
        ).status_code
        == 200
    )
    assert len(client.get(f"/api/projects/{p['id']}/events", headers=auth["one"]).json()) == 2


def test_recommendation_filters(client):
    assert (
        len(
            client.get(
                "/api/species?light=Sol%20pleno&size=Pequeno&objective=flores&difficulty=Baixa"
            ).json()
        )
        == 1
    )
    assert client.get("/api/species?light=Sombra").json() == []


def test_image_validation_serving_and_privacy(client, auth):
    q = quote(client, auth)
    buffer = io.BytesIO()
    Image.new("RGB", (30, 20), "green").save(buffer, "PNG")
    r = client.post(
        f"/api/images/quotes/{q['id']}",
        headers=auth["one"],
        files={"file": ("jardim.png", buffer.getvalue(), "image/png")},
    )
    assert r.status_code == 201
    url = r.json()["url"]
    assert client.get(url, headers=auth["one"]).status_code == 200
    assert client.get(url, headers=auth["two"]).status_code == 404
    assert (
        client.post(
            "/api/images/products/1",
            headers=auth["one"],
            files={"file": ("img.png", buffer.getvalue(), "image/png")},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/images/quotes/{q['id']}",
            headers=auth["one"],
            files={"file": ("fake.png", b"<script>evil</script>", "image/png")},
        ).status_code
        == 422
    )
    assert client.delete(f"/api/images/{r.json()['id']}", headers=auth["one"]).status_code == 204


def test_import_all_or_nothing(client, auth):
    text = "name,sku,category,price_cents,stock\nNovo vaso,VA-002,Vasos,1000,5\nProduto errado,XX-003,Vasos,-1000,5\n"
    assert (
        client.post(
            "/api/products-import",
            headers=auth["admin"],
            files={"file": ("produtos.csv", text, "text/csv")},
        ).status_code
        == 422
    )
    assert len(client.get("/api/products").json()) == 2
    text = "name;sku;category;price_cents;stock\nNovo vaso;VA-002;Vasos;1000;5\n"
    assert (
        client.post(
            "/api/products-import",
            headers=auth["admin"],
            files={"file": ("produtos.csv", text, "text/csv")},
        ).json()["imported"]
        == 1
    )


def test_agenda_overlap_and_invalid_times(client, auth):
    body = {
        "service_id": 1,
        "customer_id": 2,
        "title": "Visita técnica",
        "date": date.today().isoformat(),
        "start_time": "08:00",
        "end_time": "10:00",
        "responsible": "Equipe um",
        "address": "Rua das Flores, 123",
    }
    assert client.post("/api/appointments", headers=auth["admin"], json=body).status_code == 201
    assert (
        client.post(
            "/api/appointments",
            headers=auth["admin"],
            json={**body, "start_time": "09:00", "end_time": "11:00"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/appointments",
            headers=auth["admin"],
            json={**body, "start_time": "10:00", "end_time": "11:00"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/appointments", headers=auth["admin"], json={**body, "end_time": "07:00"}
        ).status_code
        == 422
    )


def test_finance_only_paid_entries_and_payment_once(client, auth):
    today = date.today().isoformat()
    body = {
        "direction": "Receita",
        "source": "Serviços",
        "counterparty": "Cliente um",
        "description": "Poda",
        "due_date": today,
        "amount_cents": 10000,
    }
    entry = client.post("/api/ledger", headers=auth["admin"], json=body).json()
    assert client.get("/api/analytics", headers=auth["admin"]).json()["income"] == 0
    assert (
        client.patch(
            f"/api/ledger/{entry['id']}/pay?paid_date={today}", headers=auth["admin"]
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/ledger/{entry['id']}/pay?paid_date={today}", headers=auth["admin"]
        ).status_code
        == 409
    )
    assert client.get("/api/analytics", headers=auth["admin"]).json()["income"] == 10000


def test_paid_order_cannot_cancel_without_refund(client, auth):
    id = order(client, auth).json()["id"]
    with SessionLocal() as db:
        entry = db.scalar(select(Ledger).where(Ledger.order_id == id))
        entry_id = entry.id
    client.patch(
        f"/api/ledger/{entry_id}/pay?paid_date={date.today().isoformat()}", headers=auth["admin"]
    )
    assert client.post(f"/api/orders/{id}/cancel", headers=auth["one"]).status_code == 409
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 3
        assert db.get(Order, id).status == "Confirmado"


def test_favorites_are_private_and_review_requires_purchase(client, auth):
    assert client.post("/api/favorites/1", headers=auth["one"]).status_code == 201
    assert client.get("/api/favorites", headers=auth["two"]).json() == []
    assert (
        client.post(
            "/api/products/1/reviews",
            headers=auth["one"],
            json={"rating": 5, "comment": "Excelente"},
        ).status_code
        == 403
    )
    order(client, auth)
    assert (
        client.post(
            "/api/products/1/reviews",
            headers=auth["one"],
            json={"rating": 5, "comment": "Excelente"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/products/1/reviews",
            headers=auth["one"],
            json={"rating": 5, "comment": "Excelente"},
        ).status_code
        == 409
    )


def test_documents_privacy(client, auth):
    body = {
        "name": "Jardim",
        "customer_id": 2,
        "address": "Rua das Flores, 123",
        "area": 85,
        "budget_cents": 100000,
        "start_date": date.today().isoformat(),
        "end_date": date.today().isoformat(),
    }
    p = client.post("/api/projects", headers=auth["admin"], json=body).json()
    pdf = b"%PDF-1.4\n%%EOF"
    d = client.post(
        f"/api/projects/{p['id']}/documents",
        headers=auth["admin"],
        files={"file": ("planta.pdf", pdf, "application/pdf")},
    )
    assert d.status_code == 201
    assert (
        client.get(f"/api/documents/{d.json()['id']}/content", headers=auth["one"]).status_code
        == 200
    )
    assert (
        client.get(f"/api/documents/{d.json()['id']}/content", headers=auth["two"]).status_code
        == 404
    )


def test_customer_disabled_loses_access(client, auth):
    assert (
        client.put(
            "/api/customers/2", headers=auth["admin"], json={"name": "Cliente um", "active": False}
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me", headers=auth["one"]).status_code == 401
