import io
from concurrent.futures import ThreadPoolExecutor

from app.database import SessionLocal
from app.demo_details import complete_demo, complete_demo_sales, link_demo_projects
from app.models import AuditEvent, Image, Ledger, Order, Product, Project, StockMove
from PIL import Image as PILImage
from sqlalchemy import func, select


def test_checkout_replay_is_atomic_under_concurrency(client, auth):
    body = {"items": [{"product_id": 1, "quantity": 2}], "request_key": "checkout-replay-1234"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda _: client.post("/api/orders", headers=auth["one"], json=body), range(2))
        )
    assert all(r.status_code == 201 for r in responses)
    assert responses[0].json()["id"] == responses[1].json()["id"]
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 3
        assert db.scalar(select(func.count()).select_from(Order)) == 1
        assert db.scalar(select(func.count()).select_from(Ledger)) == 1
        assert db.scalar(select(func.count()).select_from(StockMove)) == 1
    assert client.post("/api/orders", headers=auth["two"], json=body).status_code == 409
    assert (
        client.post(
            "/api/orders",
            headers=auth["one"],
            json={**body, "items": [{"product_id": 1, "quantity": 1}]},
        ).status_code
        == 409
    )


def test_oversized_order_rolls_back_everything(client, auth):
    with SessionLocal() as db:
        db.get(Product, 1).price_cents = 100000000
        db.commit()
    assert (
        client.post(
            "/api/orders", headers=auth["one"], json={"items": [{"product_id": 1, "quantity": 2}]}
        ).status_code
        == 422
    )
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 5
        assert not db.scalar(select(Order.id))
        assert not db.scalar(select(AuditEvent.id))


def test_tax_rounding_never_creates_negative_components(client, auth):
    response = client.post(
        "/api/admin/pricing/preview",
        headers=auth["admin"],
        json={
            "cost_cents": 100,
            "tax_regime": "Detalhado",
            "tax_rates": {name: 0.6 for name in ["icms", "pis", "cofins", "other", "ipi"]},
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert all(value >= 0 for value in result["taxes"].values())
    assert sum(result["taxes"].values()) == result["tax_cents"]
    assert (
        result["cost_cents"] + result["markup_cents"] + result["tax_cents"]
        == result["suggested_price_cents"]
    )


def test_payment_and_cancellation_remain_consistent(client, auth):
    order = client.post(
        "/api/orders", headers=auth["one"], json={"items": [{"product_id": 1, "quantity": 1}]}
    ).json()
    with SessionLocal() as db:
        ledger_id = db.scalar(select(Ledger.id).where(Ledger.order_id == order["id"]))
    with ThreadPoolExecutor(max_workers=2) as pool:
        pay = pool.submit(
            client.patch, f"/api/ledger/{ledger_id}/pay?paid_date=2026-10-05", headers=auth["admin"]
        )
        cancel = pool.submit(client.post, f"/api/orders/{order['id']}/cancel", headers=auth["one"])
        assert sorted([pay.result().status_code, cancel.result().status_code]) == [200, 409]
    with SessionLocal() as db:
        row = db.get(Order, order["id"])
        account = db.get(Ledger, ledger_id)
        assert (row.status, account.status) in [("Confirmado", "Pago"), ("Cancelado", "Cancelado")]
        assert db.get(Product, 1).stock == (4 if row.status == "Confirmado" else 5)
        assert db.scalar(
            select(AuditEvent.id).where(
                AuditEvent.entity == "Financeiro", AuditEvent.action.in_(["Pagar", "Cancelar"])
            )
        )


def make_project(db, stage="Execução"):
    row = Project(
        name="Projeto integrado",
        customer_id=2,
        address="Rua Jardim, 10",
        area=85,
        budget_cents=300000,
        start_date="2026-10-01",
        end_date="2026-12-01",
        description="",
        status=stage,
    )
    db.add(row)
    db.commit()
    return row.id


def test_project_consumption_integrates_stock_cost_and_audit(client, auth):
    with SessionLocal() as db:
        id = make_project(db)
        db.get(Product, 1).cost_cents = 1000
        db.commit()
    body = {
        "quantity": -2,
        "reason": "Plantio no jardim frontal",
        "project_id": id,
        "request_key": "project-consume-123",
    }
    assert client.post("/api/products/1/stock", headers=auth["admin"], json=body).status_code == 200
    assert client.post("/api/products/1/stock", headers=auth["admin"], json=body).status_code == 200
    result = client.get(f"/api/projects/{id}/stock-usage", headers=auth["admin"]).json()
    assert result["total"] == 1 and result["cost_cents"] == 2000 and result["uncosted_moves"] == 0
    assert result["items"][0]["total_cost_cents"] == 2000
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 3
        assert not db.scalar(
            select(Ledger.id)
        )  # Using already purchased stock is not a second purchase.
        db.get(Product, 1).cost_cents = 2000
        db.commit()
    assert (
        client.get(f"/api/projects/{id}/stock-usage", headers=auth["admin"]).json()["cost_cents"]
        == 2000
    )
    assert client.get(f"/api/projects/{id}/stock-usage", headers=auth["one"]).status_code == 403
    # Unknown costs remain explicit; they are never silently treated as complete totals.
    assert (
        client.post(
            "/api/products/2/stock",
            headers=auth["admin"],
            json={"quantity": -1, "reason": "Vaso utilizado", "project_id": id},
        ).status_code
        == 200
    )
    result = client.get(f"/api/projects/{id}/stock-usage", headers=auth["admin"]).json()
    assert result["uncosted_moves"] == 1 and result["cost_cents"] == 2000


def test_project_consumption_requires_execution_and_available_stock(client, auth):
    with SessionLocal() as db:
        id = make_project(db, "Planejamento")
    body = {"quantity": -1, "reason": "Plantio planejado", "project_id": id}
    assert client.post("/api/products/1/stock", headers=auth["admin"], json=body).status_code == 409
    with SessionLocal() as db:
        db.get(Project, id).status = "Execução"
        db.commit()
    assert (
        client.post(
            "/api/products/1/stock", headers=auth["admin"], json={**body, "quantity": -6}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/products/1/stock", headers=auth["admin"], json={**body, "quantity": 1}
        ).status_code
        == 422
    )
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 5
        assert not db.scalar(select(StockMove.id))


def test_rejected_quote_cannot_be_reopened_by_pricing(client, auth):
    q = client.post(
        "/api/quotes",
        headers=auth["one"],
        json={"service_id": 1, "area": 20, "address": "Rua Jardim, 10"},
    ).json()
    assert (
        client.patch(
            f"/api/quotes/{q['id']}/status", headers=auth["one"], json={"status": "Rejeitado"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/quotes/{q['id']}/price", headers=auth["admin"], json={"amount_cents": 10000}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/quotes",
            headers=auth["one"],
            json={
                "service_id": 1,
                "area": 20,
                "address": "Rua Jardim, 10",
                "plants": [{"species_id": 999, "quantity": 1}],
            },
        ).status_code
        == 404
    )


def test_phone_photo_orientation_and_missing_file(client, auth):
    output = io.BytesIO()
    image = PILImage.new("RGB", (40, 20), "green")
    exif = image.getexif()
    exif[274] = 6
    image.save(output, "JPEG", exif=exif)
    result = client.post(
        "/api/images/users/2",
        headers=auth["one"],
        files={"file": ("portrait.jpg", output.getvalue(), "image/jpeg")},
    )
    assert result.status_code == 201
    content = client.get(result.json()["url"], headers=auth["one"]).content
    assert PILImage.open(io.BytesIO(content)).size == (20, 40)
    with SessionLocal() as db:
        db.add(Image(owner_id=2, entity="users", entity_id=2, filename="missing-test.jpg"))
        db.commit()
        id = db.scalar(select(Image.id).where(Image.filename == "missing-test.jpg"))
    assert client.get(f"/api/images/{id}/content", headers=auth["one"]).status_code == 404


def test_demo_completion_preserves_values_and_is_once_only(client, auth):
    from app.models import Appointment, Supplier, User

    with SessionLocal() as db:
        customer = db.get(User, 2)
        customer.email = "cliente@atelieverde.local"
        product = db.get(Product, 1)
        product.demo_asset = "lavender"
        supplier = Supplier(
            code="FOR-001",
            name="Viveiro de teste",
            category="Plantas",
            identity_key="viveiro de teste",
            notes="Fornecedor fictício para demonstração",
        )
        db.add(supplier)
        db.commit()
        product.supplier_id = supplier.id
        db.commit()
        old = (product.price_cents, product.stock, product.sku, customer.password_hash)
        result = complete_demo(db)
        assert result["clientes"] == 1 and result["fornecedores"] == 1 and result["produtos"] == 1
        assert (product.price_cents, product.stock, product.sku, customer.password_hash) == old
        assert customer.document and customer.state and customer.postal_code
        assert supplier.phone and supplier.email and supplier.document
        assert product.brand and product.variant and product.cost_cents > 0 and product.barcode
        assert db.scalar(select(func.count()).select_from(Appointment)) == 20
        customer.phone = "Meu contato"
        product.cost_cents = 123
        db.commit()
        assert complete_demo(db) is None
        assert customer.phone == "Meu contato" and product.cost_cents == 123


def test_demo_sales_categories_match_orders_stock_and_finance(client, auth):
    from app.models import User

    with SessionLocal() as db:
        db.get(User, 2).email = "cliente@atelieverde.local"
        for category in ["Substratos", "Fertilizantes", "Ferramentas", "Acessórios"]:
            db.add(
                Product(
                    name=category,
                    category=category,
                    sku="DEMO-" + category,
                    description="",
                    price_cents=3000,
                    stock=20,
                )
            )
        db.commit()
        old_stocks = {p.id: p.stock for p in db.scalars(select(Product))}
        added = complete_demo_sales(db)
        assert len(added) == 5
        for item in added:
            order = db.get(Order, item["pedido"])
            account = db.scalar(select(Ledger).where(Ledger.order_id == order.id))
            assert account.status == "Pago" and account.amount_cents == order.total_cents
            for line in order.items:
                assert (
                    db.get(Product, line["product_id"]).stock
                    == old_stocks[line["product_id"]] - line["quantity"]
                )
        assert complete_demo_sales(db) is None
        assert db.scalar(select(func.count()).select_from(Order)) == 5
    from app.clock import today

    result = client.get(
        f"/api/analytics?start={today().year}-01-01&end={today().year}-12-31", headers=auth["admin"]
    ).json()
    assert all(
        result["categories"].get(category, 0) > 0
        for category in ["Vasos", "Substratos", "Fertilizantes", "Ferramentas", "Acessórios"]
    )
    assert result["products_sold"] == sum(result["categories"].values())


def test_sales_category_is_a_historical_snapshot(client, auth):
    from app.clock import today

    response = client.post(
        "/api/orders", headers=auth["one"], json={"items": [{"product_id": 1, "quantity": 1}]}
    )
    assert response.status_code == 201 and response.json()["items"][0]["category"] == "Plantas"
    with SessionLocal() as db:
        db.get(Product, 1).category = "Vasos"
        db.commit()
    result = client.get(
        f"/api/analytics?start={today().year}-01-01&end={today().year}-12-31", headers=auth["admin"]
    ).json()
    assert result["categories"] == {"Plantas": 1}


def test_approved_demo_quote_has_one_matching_project(client, auth):
    from app.models import Quote, User

    with SessionLocal() as db:
        db.get(User, 2).email = "cliente@atelieverde.local"
        quote = Quote(
            customer_id=2,
            service_id=1,
            area=32,
            address="Rua Jardim, 12",
            description="Proposta aprovada",
            status="Aprovado",
            amount_cents=100000,
            plants=[{"species_id": 1, "quantity": 4}],
        )
        db.add(quote)
        db.commit()
        added = link_demo_projects(db)
        assert len(added) == 1
        project = db.get(Project, added[0])
        assert (
            project.customer_id,
            project.quote_id,
            project.area,
            project.address,
            project.budget_cents,
        ) == (2, quote.id, 32, quote.address, 100000)
        assert project.plants == quote.plants and project.status == "Aprovado"
        assert link_demo_projects(db) is None
        assert db.scalar(select(func.count()).select_from(Project)) == 1


def test_data_quality_reconciles_and_is_admin_only(client, auth):
    with SessionLocal() as db:
        for product in db.scalars(select(Product)):
            db.add(
                StockMove(
                    product_id=product.id,
                    quantity=product.stock,
                    reason="Saldo inicial",
                    actor_id=1,
                )
            )
        db.commit()
    response = client.post(
        "/api/orders", headers=auth["one"], json={"items": [{"product_id": 1, "quantity": 1}]}
    )
    assert response.status_code == 201
    assert client.get("/api/admin/data-quality", headers=auth["one"]).status_code == 403
    assert client.get("/api/admin/data-quality", headers=auth["admin"]).json()["errors"] == []
    with SessionLocal() as db:
        db.get(Product, 1).stock += 1
        account = db.scalar(select(Ledger).where(Ledger.order_id == response.json()["id"]))
        account.amount_cents += 1
        db.commit()
    errors = client.get("/api/admin/data-quality", headers=auth["admin"]).json()["errors"]
    assert {error["entity"] for error in errors} == {"Produto", "Pedido"}
