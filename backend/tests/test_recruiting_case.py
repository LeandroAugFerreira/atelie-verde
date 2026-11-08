"""Ateliê Verde: dois casos de integração verificáveis para entrevistas.

Fixtures artificiais: catálogo/usuários em banco temporário, sem dinheiro real,
contato com cliente, pagamentos externos ou serviços de IA.
"""
from app.database import SessionLocal
from app.models import Ledger, Order, Product, Project, ProjectEvent, StockMove
from sqlalchemy import select


def test_recrutamento_compra_idempotente_estoque_financeiro_e_cancelamento(client, auth):
    """O preço vem do banco; um replay não vende novamente; o cancelamento repõe."""
    pedido = {
        "request_key": "portfolio-checkout-sintetico-20261108",
        "items": [{"product_id": 1, "quantity": 2}],
    }
    criado = client.post("/api/orders", headers=auth["one"], json=pedido)
    assert criado.status_code == 201, criado.text
    order_id = criado.json()["id"]
    assert criado.json()["total_cents"] == 4980
    assert criado.json()["status"] == "Confirmado"

    repetido = client.post("/api/orders", headers=auth["one"], json=pedido)
    assert repetido.status_code == 201, repetido.text
    assert repetido.json()["id"] == order_id

    assert client.get("/api/ledger", headers=auth["one"]).status_code == 403
    assert not any(x["id"] == order_id for x in client.get("/api/orders", headers=auth["two"]).json())
    assert client.post(f"/api/orders/{order_id}/cancel", headers=auth["two"]).status_code == 404

    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 3
        assert len(db.scalars(select(Order).where(Order.id == order_id)).all()) == 1
        moves = db.scalars(select(StockMove).where(StockMove.reference == f"Pedido #{order_id}")).all()
        assert len(moves) == 1 and moves[0].quantity == -2
        bills = db.scalars(select(Ledger).where(Ledger.order_id == order_id)).all()
        assert len(bills) == 1
        assert bills[0].amount_cents == 4980 and bills[0].status == "Pendente"

    cancelado = client.post(f"/api/orders/{order_id}/cancel", headers=auth["one"])
    assert cancelado.status_code == 200, cancelado.text
    assert cancelado.json()["status"] == "Cancelado"
    assert client.post(f"/api/orders/{order_id}/cancel", headers=auth["one"]).status_code == 409

    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 5
        assert db.get(Order, order_id).status == "Cancelado"
        assert db.scalar(select(Ledger).where(Ledger.order_id == order_id)).status == "Cancelado"
        moves = db.scalars(select(StockMove).where(StockMove.reference == f"Pedido #{order_id}")).all()
        assert sorted(x.quantity for x in moves) == [-2, 2]


def test_recrutamento_orcamento_aprovacao_e_projeto_com_escopo(client, auth):
    """Cliente solicita, admin precifica, somente proprietário aprova uma vez."""
    body = {
        "service_id": 1,
        "area": 85,
        "address": "Rua Sintética, 123",
        "description": "Jardim de demonstração, sem cliente real",
    }
    response = client.post("/api/quotes", headers=auth["one"], json=body)
    assert response.status_code == 201, response.text
    quote_id = response.json()["id"]
    assert not any(q["id"] == quote_id for q in client.get("/api/quotes", headers=auth["two"]).json())

    assert client.post(f"/api/quotes/{quote_id}/approve", headers=auth["one"]).status_code == 409
    assert client.patch(
        f"/api/quotes/{quote_id}/price", headers=auth["one"], json={"amount_cents": 180000}
    ).status_code == 403

    priced = client.patch(
        f"/api/quotes/{quote_id}/price", headers=auth["admin"], json={"amount_cents": 180000}
    )
    assert priced.status_code == 200, priced.text
    assert priced.json()["status"] == "Enviado"
    assert client.post(f"/api/quotes/{quote_id}/approve", headers=auth["two"]).status_code == 404

    approved = client.post(f"/api/quotes/{quote_id}/approve", headers=auth["one"])
    assert approved.status_code == 200, approved.text
    project_id = approved.json()["id"]
    assert approved.json()["quote_id"] == quote_id
    assert approved.json()["budget_cents"] == 180000
    assert client.post(f"/api/quotes/{quote_id}/approve", headers=auth["one"]).status_code == 409
    assert client.patch(
        f"/api/quotes/{quote_id}/price", headers=auth["admin"], json={"amount_cents": 190000}
    ).status_code == 409
    assert not any(p["id"] == project_id for p in client.get("/api/projects", headers=auth["two"]).json())

    with SessionLocal() as db:
        projects = db.scalars(select(Project).where(Project.quote_id == quote_id)).all()
        assert len(projects) == 1 and projects[0].id == project_id
        events = db.scalars(select(ProjectEvent).where(ProjectEvent.project_id == project_id)).all()
        assert len(events) == 1 and events[0].status == "Aprovado"


def test_recrutamento_pedido_pago_nao_pode_cancelar_sem_reembolso(client, auth):
    """A regra exige processo explícito de reembolso; estoque continua baixado."""
    order = client.post("/api/orders", headers=auth["one"], json={
        "items": [{"product_id": 1, "quantity": 1}]
    })
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    with SessionLocal() as db:
        account = db.scalar(select(Ledger).where(Ledger.order_id == order_id))
        ledger_id = account.id

    paid = client.patch(
        f"/api/ledger/{ledger_id}/pay",
        params={"paid_date": "2026-11-08"},
        headers=auth["admin"],
    )
    assert paid.status_code == 200, paid.text
    blocked = client.post(f"/api/orders/{order_id}/cancel", headers=auth["one"])
    assert blocked.status_code == 409
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 4
        assert db.get(Order, order_id).status == "Confirmado"
        assert db.get(Ledger, ledger_id).status == "Pago"
