from concurrent.futures import ThreadPoolExecutor
from decimal import ROUND_HALF_UP, Decimal

import pytest
from app.database import SessionLocal
from app.models import AuditEvent, Ledger, Product, StockMove
from sqlalchemy import select


def supplier(client, auth, **values):
    response = client.post(
        "/api/suppliers",
        headers=auth["admin"],
        json={
            "name": "Viveiro Comercial",
            "category": "Plantas",
            "document": "12.345.678/0001-95",
            **values,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def product(client, auth, **values):
    response = client.post(
        "/api/products",
        headers=auth["admin"],
        json={"name": "Muda comercial", "category": "Plantas", "price_cents": 2900, **values},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize(
    "regime,rates,expected",
    [
        ("Carga efetiva", {"effective": 10}, 16667),
        ("Simples Nacional", {"simples": 6}, 15957),
        (
            "Detalhado",
            {"icms": 18, "pis": 1.65, "cofins": 7.6, "ipi": 5},
            int(
                (Decimal(15000) / (1 - Decimal("0.25585")) * Decimal("1.05")).quantize(
                    Decimal(1), rounding=ROUND_HALF_UP
                )
            ),
        ),
    ],
)
def test_pricing_and_sale_use_server_price(client, auth, regime, rates, expected):
    body = {"cost_cents": 10000, "markup_percent": 50, "tax_regime": regime, "tax_rates": rates}
    preview = client.post("/api/admin/pricing/preview", headers=auth["admin"], json=body)
    assert preview.status_code == 200
    assert preview.json()["suggested_price_cents"] == expected
    row = product(client, auth, **body, pricing_mode="Custo + margem", price_cents=1, stock=2)
    assert row["price_cents"] == expected
    assert row["sku"].startswith("PRD-")
    public = next(p for p in client.get("/api/products").json() if p["id"] == row["id"])
    assert not set(public) & {
        "cost_cents",
        "markup_percent",
        "supplier_id",
        "tax_rates",
        "identity_key",
    }
    order = client.post(
        "/api/orders",
        headers=auth["one"],
        json={"items": [{"product_id": row["id"], "quantity": 1, "price_cents": 1}]},
    )
    assert order.status_code == 201
    assert order.json()["total_cents"] == expected


def test_tax_limits_and_manual_price(client, auth):
    for body in [
        {"tax_rates": {"effective": 100}},
        {"tax_rates": {"effective": -1}},
        {"tax_regime": "Simples Nacional", "tax_rates": {"simples": 6, "icms": 18}},
        {"tax_regime": "Detalhado", "tax_rates": {"icms": 90, "other": 10}},
    ]:
        assert (
            client.post("/api/admin/pricing/preview", headers=auth["admin"], json=body).status_code
            == 422
        )
    assert (
        client.post("/api/admin/pricing/preview", headers=auth["one"], json={}).status_code == 403
    )
    row = product(client, auth, cost_cents=1000, markup_percent=50, tax_rates={"effective": 10})
    assert row["price_cents"] == 2900


def test_supplier_duplicates_inactive_and_preserved_links(client, auth):
    partner = supplier(client, auth)
    assert partner["code"] == "FOR-001"
    response = client.post(
        "/api/suppliers",
        headers=auth["admin"],
        json={"name": "  VIVEIRO  COMERCIAL ", "category": "Plantas"},
    )
    assert response.status_code == 409
    assert (
        client.post(
            "/api/suppliers",
            headers=auth["admin"],
            json={"name": "Outro viveiro", "category": "Plantas", "document": "12345678000195"},
        ).status_code
        == 409
    )
    row = product(client, auth, supplier_id=partner["id"])
    assert (
        client.patch(
            f"/api/suppliers/{partner['id']}/status", headers=auth["admin"], json={"active": False}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/products",
            headers=auth["admin"],
            json={
                "name": "Outra muda",
                "category": "Plantas",
                "price_cents": 1000,
                "supplier_id": partner["id"],
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/products/{row['id']}/stock",
            headers=auth["admin"],
            json={"quantity": 1, "reason": "Compra teste", "supplier_id": partner["id"]},
        ).status_code
        == 422
    )
    # An archived supplier remains linked to its existing products.
    assert (
        client.put(
            f"/api/products/{row['id']}",
            headers=auth["admin"],
            json={**row, "description": "Atualizada"},
        ).status_code
        == 200
    )
    assert client.get("/api/suppliers", headers=auth["one"]).status_code == 403


def test_product_identity_barcode_import_and_stock_guards(client, auth):
    row = product(
        client,
        auth,
        name="Vaso cerâmico",
        brand="Verde",
        variant="20 cm",
        barcode="7891234567895",
        stock=4,
        category="Vasos",
    )
    assert (
        client.post(
            "/api/products",
            headers=auth["admin"],
            json={
                "name": "VASO CERAMICO",
                "brand": "verde",
                "variant": "20  cm",
                "category": "Vasos",
                "price_cents": 5000,
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/products",
            headers=auth["admin"],
            json={
                "name": "Outra embalagem",
                "category": "Vasos",
                "price_cents": 5000,
                "barcode": "7891234567895",
            },
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/products/{row['id']}", headers=auth["admin"], json={**row, "stock": 20}
        ).status_code
        == 422
    )
    csv = "name;category;price_cents;stock\nNovo importado;Vasos;1000;3\nVaso cerâmico;Vasos;1000;3\nVaso cerâmico;Vasos;1000;3"
    assert (
        client.post(
            "/api/products-import",
            headers=auth["admin"],
            files={"file": ("p.csv", csv.encode(), "text/csv")},
        ).status_code
        == 409
    )
    assert not any(
        p["name"] == "Novo importado"
        for p in client.get("/api/admin/products", headers=auth["admin"]).json()
    )
    variant = product(
        client, auth, name="Vaso cerâmico", brand="Verde", variant="30 cm", category="Vasos"
    )
    assert variant["sku"] != row["sku"]


def test_stock_purchase_atomic_idempotent_audited(client, auth):
    partner = supplier(client, auth)
    body = {
        "quantity": 3,
        "reason": "Compra de mudas",
        "supplier_id": partner["id"],
        "unit_cost_cents": 1200,
        "record_payable": True,
        "due_date": "2026-11-10",
        "origin": "Viveiro",
        "destination": "A1",
        "reference": "NF-123",
        "request_key": "stock-purchase-123",
    }
    for _ in range(2):
        response = client.post("/api/products/1/stock", headers=auth["admin"], json=body)
        assert response.status_code == 200
        assert response.json()["stock"] == 8
    assert (
        client.post(
            "/api/products/1/stock", headers=auth["admin"], json={**body, "quantity": 2}
        ).status_code
        == 409
    )
    with SessionLocal() as db:
        move = db.scalar(select(StockMove).where(StockMove.request_key == body["request_key"]))
        assert (move.balance_before, move.balance_after) == (5, 8)
        entry = db.scalar(select(Ledger).where(Ledger.stock_move_id == move.id))
        assert entry.amount_cents == 3600 and entry.supplier_id == partner["id"]
        assert len(db.scalars(select(AuditEvent).where(AuditEvent.entity == "Estoque")).all()) == 1
        before = db.get(Product, 1).stock
    # Financial overflow must roll back the receipt and its audit as well.
    invalid = {
        **body,
        "request_key": "stock-overflow-123",
        "quantity": 100,
        "unit_cost_cents": 100000000,
    }
    assert (
        client.post("/api/products/1/stock", headers=auth["admin"], json=invalid).status_code == 422
    )
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == before
        assert not db.scalar(
            select(StockMove.id).where(StockMove.request_key == invalid["request_key"])
        )
    history = client.get(
        "/api/stock-history?product_id=1&kind=Entrada", headers=auth["admin"]
    ).json()
    assert history["total"] == 1 and history["items"][0]["balance_after"] == 8
    assert (
        client.get(
            "/api/stock-history?start=2026-12-01&end=2026-11-30", headers=auth["admin"]
        ).status_code
        == 422
    )


def test_concurrent_receipt_replay_and_automatic_codes(client, auth):
    body = {
        "quantity": 2,
        "reason": "Reposição simultânea",
        "request_key": "concurrent-receipt-123",
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post("/api/products/1/stock", headers=auth["admin"], json=body),
                range(2),
            )
        )
    assert [r.status_code for r in responses] == [200, 200]
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 7
        assert len(db.scalars(select(StockMove)).all()) == 1
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(
            pool.map(
                lambda i: client.post(
                    "/api/products",
                    headers=auth["admin"],
                    json={
                        "name": f"Muda concorrente {i}",
                        "category": "Plantas",
                        "price_cents": 1000,
                    },
                ),
                range(3),
            )
        )
    assert all(r.status_code == 201 for r in responses)
    assert len({r.json()["sku"] for r in responses}) == 3


def test_customer_commercial_registration_duplicate_document_and_portal(client, auth):
    body = {
        "name": "Cliente comercial",
        "email": "COMERCIAL@test.local",
        "customer_type": "Pessoa jurídica",
        "document": "12.345.678/0001-95",
        "postal_code": "01310-100",
        "city": "São Paulo",
        "state": "sp",
    }
    response = client.post("/api/customers", headers=auth["admin"], json=body)
    assert response.status_code == 201
    row = response.json()
    assert row["customer_code"] == "CLI-001" and row["portal_enabled"] is False
    assert (
        row["document"] == "12345678000195"
        and row["postal_code"] == "01310100"
        and row["state"] == "SP"
    )
    assert "password_hash" not in row
    assert (
        client.post(
            "/api/auth/login", json={"email": body["email"], "password": "TestPassword@2026"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/customers", headers=auth["admin"], json={**body, "email": "outro@test.local"}
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/customers/{row['id']}",
            headers=auth["admin"],
            json={"name": body["name"], "notes": "Atendimento mensal"},
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/customers/{row['id']}",
            headers=auth["admin"],
            json={"name": body["name"], "customer_type": "Pessoa física"},
        ).status_code
        == 422
    )
    audit = client.get("/api/audit-events?entity=Cliente", headers=auth["admin"]).json()
    assert audit["total"] == 2 and "password_hash" not in str(audit)
    assert client.get("/api/audit-events", headers=auth["one"]).status_code == 403
