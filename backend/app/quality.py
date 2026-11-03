"""Read-only reconciliation of commercial records and their links."""

from sqlalchemy import func, select

from .models import Appointment, Ledger, Order, Product, Project, Quote, StockMove, User, now


def check_data(db):
    errors = []
    warnings = []
    products = list(db.scalars(select(Product)))
    orders = list(db.scalars(select(Order)))
    accounts = list(db.scalars(select(Ledger)))
    quotes = list(db.scalars(select(Quote)))
    projects = list(db.scalars(select(Project)))
    appointments = list(db.scalars(select(Appointment)))
    roles = dict(db.execute(select(User.id, User.role)).all())
    balances = dict(
        db.execute(
            select(StockMove.product_id, func.sum(StockMove.quantity)).group_by(
                StockMove.product_id
            )
        ).all()
    )
    by_order = {entry.order_id: entry for entry in accounts if entry.order_id}
    for product in products:
        if product.stock != balances.get(product.id, 0):
            errors.append(
                {
                    "entity": "Produto",
                    "id": product.id,
                    "message": f"{product.sku}: saldo não corresponde ao histórico de movimentações.",
                }
            )
    for order in orders:
        expected = sum(item["quantity"] * item["price_cents"] for item in order.items)
        account = by_order.get(order.id)
        if (
            expected != order.total_cents
            or not account
            or account.amount_cents != order.total_cents
        ):
            errors.append(
                {
                    "entity": "Pedido",
                    "id": order.id,
                    "message": "Total dos itens, pedido e conta a receber não coincidem.",
                }
            )
        if roles.get(order.customer_id) != "customer":
            errors.append(
                {
                    "entity": "Pedido",
                    "id": order.id,
                    "message": "Cliente do pedido não corresponde a um cadastro de cliente.",
                }
            )
        if account and (
            account.customer_id != order.customer_id
            or (order.status == "Cancelado" and account.status != "Cancelado")
            or (order.status != "Cancelado" and account.status == "Cancelado")
        ):
            errors.append(
                {
                    "entity": "Pedido",
                    "id": order.id,
                    "message": "Cliente ou situação financeira diverge do pedido.",
                }
            )
    linked = {project.quote_id: project for project in projects if project.quote_id}
    for quote in quotes:
        if quote.status != "Aprovado":
            continue
        project = linked.get(quote.id)
        if not project or project.customer_id != quote.customer_id:
            errors.append(
                {
                    "entity": "Orçamento",
                    "id": quote.id,
                    "message": "Orçamento aprovado sem projeto do mesmo cliente.",
                }
            )
        elif project.budget_cents != quote.amount_cents:
            warnings.append(
                {
                    "entity": "Projeto",
                    "id": project.id,
                    "message": "Orçamento do projeto difere da proposta aprovada; confira se houve revisão do escopo.",
                }
            )
    agenda = {}
    for appointment in appointments:
        if appointment.status == "Cancelado":
            continue
        key = (appointment.date, appointment.responsible.strip().casefold())
        for other in agenda.get(key, []):
            if appointment.start_time < other.end_time and appointment.end_time > other.start_time:
                errors.append(
                    {
                        "entity": "Agenda",
                        "id": appointment.id,
                        "message": "Compromissos sobrepostos para o mesmo responsável.",
                    }
                )
        agenda.setdefault(key, []).append(appointment)
    for entry in accounts:
        if entry.direction == "Receita" and entry.source == "Loja" and not entry.order_id:
            warnings.append(
                {
                    "entity": "Financeiro",
                    "id": entry.id,
                    "message": "Receita manual de loja sem pedido: não participa da contagem de unidades vendidas.",
                }
            )
    return {
        "checked_at": now(),
        "counts": {
            "products": len(products),
            "orders": len(orders),
            "quotes": len(quotes),
            "appointments": len(appointments),
        },
        "errors": errors,
        "warnings": warnings,
    }
