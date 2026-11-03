from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import business
from .clock import today
from .models import Ledger, Order, Product, User
from .transactions import locked


def checkout(db, body, user, commit=True):
    if user.role != "customer":
        raise HTTPException(403, "Realize compras pelo perfil de cliente.")
    counts = {}
    for item in body.items:
        counts[item.product_id] = counts.get(item.product_id, 0) + item.quantity
    payload = {"items": [{"product_id": id, "quantity": q} for id, q in sorted(counts.items())]}
    locked(db, User, user.id)

    def replay():
        existing = (
            db.scalar(select(Order).where(Order.request_key == body.request_key))
            if body.request_key
            else None
        )
        if existing and (existing.customer_id != user.id or existing.request_payload != payload):
            raise HTTPException(409, "Identificador já usado em outro pedido.")
        return existing

    existing = replay()
    if existing:
        return existing
    lines = []
    for id, quantity in sorted(counts.items()):
        product = locked(db, Product, id)
        if not product.active:
            raise HTTPException(409, "Produto indisponível.")
        if product.stock < quantity:
            raise HTTPException(409, f"Estoque insuficiente: {product.name}.")
        lines.append(
            {
                "product_id": id,
                "name": product.name,
                "quantity": quantity,
                "price_cents": product.price_cents,
                "category": product.category,
            }
        )
    total = sum(line["quantity"] * line["price_cents"] for line in lines)
    if total > 100000000:
        raise HTTPException(422, "Total do pedido excede o limite permitido.")
    order = Order(
        customer_id=user.id,
        items=lines,
        total_cents=total,
        request_key=body.request_key,
        request_payload=payload,
    )
    db.add(order)
    try:
        db.flush()
        account = Ledger(
            direction="Receita",
            source="Loja",
            customer_id=user.id,
            order_id=order.id,
            counterparty=user.name,
            description=f"Pedido #{order.id}",
            due_date=today().isoformat(),
            amount_cents=total,
        )
        db.add(account)
        business.audit(db, user, "Financeiro", account)
        for line in lines:
            business.change_stock(
                db,
                line["product_id"],
                -line["quantity"],
                f"Pedido #{order.id}",
                user,
                origin="Estoque",
                destination=f"Cliente #{user.id}",
                reference=f"Pedido #{order.id}",
            )
        business.audit(db, user, "Pedido", order)
        if commit:
            db.commit()
    except IntegrityError:
        db.rollback()
        existing = replay()
        if existing:
            return existing
        raise HTTPException(409, "Pedido conflitante. Atualize os dados e tente novamente.")
    return order
