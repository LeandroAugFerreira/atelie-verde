"""Complete known demonstration records once, keeping business values intact."""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from . import business
from .checkout import checkout
from .clock import today
from .models import (
    Appointment,
    CatalogVersion,
    Ledger,
    Product,
    Project,
    ProjectEvent,
    Quote,
    Service,
    Supplier,
    User,
)
from .schemas import OrderInput

VERSION = "demo-details-2026-10-05-v1"
SALES_VERSION = "demo-sales-categories-2026-10-05-v1"
COHERENCE_VERSION = "demo-approved-projects-2026-10-05-v1"
NOTE = "Dados complementares gerados para demonstração; documentos e contatos de teste, sem consulta cadastral."


def cpf(index):
    digits = [int(c) for c in f"99{index:07d}"]
    for size in (10, 11):
        remainder = sum(value * (size - i) for i, value in enumerate(digits)) * 10 % 11
        digits.append(0 if remainder == 10 else remainder)
    return "".join(map(str, digits))


def cnpj(index):
    digits = [int(c) for c in f"99000000{index:04d}"]
    for weights in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        remainder = sum(value * weight for value, weight in zip(digits, weights)) % 11
        digits.append(0 if remainder < 2 else 11 - remainder)
    return "".join(map(str, digits))


def barcode(index):
    base = f"200{index:09d}"
    checksum = (-sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(base))) % 10
    return base + str(checksum)


def complete_demo(db):
    if db.get(CatalogVersion, VERSION):
        return
    clients = list(
        db.scalars(
            select(User)
            .where(
                User.role == "customer",
                User.email.in_(
                    [
                        "cliente@atelieverde.local",
                        *[f"cliente{i}@atelieverde.local" for i in range(2, 11)],
                        *[f"cliente{i}@greenscape.local" for i in range(2, 11)],
                    ]
                ),
            )
            .order_by(User.id)
        )
    )
    demo_suppliers = list(
        db.scalars(
            select(Supplier)
            .where(Supplier.notes.contains("Fornecedor fictício para demonstração"))
            .order_by(Supplier.id)
        )
    )
    supplier_map = {s.id: s for s in demo_suppliers}
    admin = db.scalar(select(User).where(User.role == "admin").order_by(User.id))
    counts = {"clientes": 0, "fornecedores": 0, "produtos": 0, "orçamentos": 0, "agenda": 0}
    used_documents = {v for v in db.scalars(select(User.document)) if v}
    for client in clients:
        before = business.snapshot(client)
        parts = client.city.rsplit(" - ", 1)
        if not client.state:
            client.state = parts[-1] if len(parts) == 2 else "SP"
        if not client.postal_code:
            client.postal_code = f"{13000 + client.id:05d}000"
        if not client.district:
            client.district = "Jardim Primavera"
        if not client.contact_name:
            client.contact_name = client.name
        if not client.document:
            index = client.id
            candidate = cpf(index) if client.customer_type == "Pessoa física" else cnpj(index)
            while candidate in used_documents:
                index += 1000
                candidate = cpf(index) if client.customer_type == "Pessoa física" else cnpj(index)
            client.document = candidate
            used_documents.add(candidate)
        if not client.phone:
            client.phone = f"(11) 5550-{client.id:04d}"
        if not client.address:
            client.address = f"Rua do Jardim, {100 + client.id}"
        if NOTE not in client.notes:
            client.notes = (client.notes + "\n" + NOTE).strip()
        if business.snapshot(client) != before:
            counts["clientes"] += 1
            if admin:
                business.audit(db, admin, "Cliente", client, before, "Completar demonstração")
    used_documents = {v for v in db.scalars(select(Supplier.document)) if v}
    for supplier in demo_suppliers:
        before = business.snapshot(supplier)
        if not supplier.trade_name:
            supplier.trade_name = supplier.name
        if not supplier.document:
            index = supplier.id
            while cnpj(index) in used_documents:
                index += 1000
            supplier.document = cnpj(index)
            used_documents.add(supplier.document)
        if not supplier.contact_name:
            supplier.contact_name = f"Atendimento · {supplier.name}"
        if not supplier.email:
            supplier.email = f"fornecedor{supplier.id}@atelie.example"
        if not supplier.phone:
            supplier.phone = f"(11) 5551-{supplier.id:04d}"
        if not supplier.address:
            supplier.address = f"Rua dos Viveiros, {100 + supplier.id * 20} · Jardim Primavera"
        if not supplier.city:
            supplier.city = "São Paulo"
        if not supplier.state:
            supplier.state = "SP"
        if not supplier.postal_code:
            supplier.postal_code = f"{14000 + supplier.id:05d}000"
        if NOTE not in supplier.notes:
            supplier.notes = (supplier.notes + "\n" + NOTE).strip()
        if business.snapshot(supplier) != before:
            counts["fornecedores"] += 1
            if admin:
                business.audit(db, admin, "Fornecedor", supplier, before, "Completar demonstração")
    used_barcodes = {v for v in db.scalars(select(Product.barcode)) if v}
    for product in db.scalars(
        select(Product)
        .where((Product.demo_asset != "") | Product.image_url.startswith("/plants/"))
        .order_by(Product.id)
    ):
        before = business.snapshot(product)
        supplier = supplier_map.get(product.supplier_id)
        if not product.brand:
            product.brand = supplier.trade_name if supplier else "Cultivo Ateliê Verde"
        if not product.variant:
            product.variant = {
                "Plantas": "Muda em vaso",
                "Vasos": "Modelo natural · unidade",
                "Substratos": "Embalagem de 5 kg",
                "Fertilizantes": "Embalagem de 1 kg",
                "Ferramentas": "Linha jardim · unidade",
                "Acessórios": "Linha jardim · unidade",
            }[product.category]
        if not product.barcode:
            index = product.id
            while barcode(index) in used_barcodes:
                index += 1000
            product.barcode = barcode(index)
            used_barcodes.add(product.barcode)
        if not product.location:
            product.location = f"{product.category[:2].upper()}-{product.id:03d}"
        if product.cost_cents == 0:
            product.cost_cents = max(
                1,
                int(
                    (Decimal(product.price_cents) * Decimal("0.58")).quantize(
                        Decimal(1), rounding=ROUND_HALF_UP
                    )
                ),
            )
            if not product.markup_percent:
                product.markup_percent = round(
                    (product.price_cents / product.cost_cents - 1) * 100, 2
                )
        product.identity_key = business.product_identity(
            product.name, product.brand, product.variant
        )
        if business.snapshot(product) != before:
            counts["produtos"] += 1
            if admin:
                business.audit(db, admin, "Produto", product, before, "Completar demonstração")
    generic = "Gostaria de um projeto paisagístico para a área externa, com espaços de convivência e plantas de baixa manutenção."
    scopes = {
        "Manutenção": "Avaliar poda, limpeza dos canteiros, adubação e cuidados periódicos para manter o jardim saudável.",
        "Implantação": "Preparar o terreno, definir canteiros e executar o plantio com espécies adequadas ao espaço.",
        "Irrigação": "Avaliar pontos de água, dimensionar a irrigação e orientar a programação de rega.",
        "Consultoria": "Realizar visita técnica para avaliar luminosidade, solo, espécies e rotina de cuidados.",
        "Projeto": "Elaborar proposta paisagística com espécies, materiais, áreas de convivência e cronograma.",
    }
    services = list(
        db.scalars(select(Service).where(Service.active.is_(True)).order_by(Service.id))
    )
    service_map = {s.id: s for s in services}
    ids = {c.id for c in clients}
    for quote in db.scalars(select(Quote).where(Quote.customer_id.in_(ids))):
        before = business.snapshot(quote)
        service = service_map.get(quote.service_id)
        if service and (
            quote.description == generic
            or (
                quote.id <= 10
                and quote.description.startswith("Gostaria")
                and "baixa manutenção" in quote.description.lower()
            )
        ):
            quote.description = f"Solicitação de {service.name.lower()} para aproximadamente {quote.area:g} m². {scopes[service.category]} Preferência por atendimento pela manhã. Demonstração."
        if not quote.address:
            quote.address = next(c.address for c in clients if c.id == quote.customer_id)
        if business.snapshot(quote) != before:
            counts["orçamentos"] += 1
            if admin:
                business.audit(db, admin, "Orçamento", quote, before, "Completar demonstração")
    monday = today() - timedelta(days=today().weekday())
    if clients and services:
        for day in range(5):
            for slot, (start, end) in enumerate(
                [("08:00", "09:00"), ("10:00", "12:00"), ("13:30", "15:00"), ("15:30", "17:00")]
            ):
                service = services[(day + slot) % len(services)]
                client = clients[(day + slot) % len(clients)]
                date = (monday + timedelta(days=day)).isoformat()
                conflict = db.scalar(
                    select(Appointment.id).where(
                        Appointment.date == date,
                        Appointment.responsible == service.responsible,
                        Appointment.status != "Cancelado",
                        Appointment.start_time < end,
                        Appointment.end_time > start,
                    )
                )
                if conflict:
                    continue
                row = Appointment(
                    service_id=service.id,
                    customer_id=client.id,
                    title=f"{service.name} · Demonstração",
                    date=date,
                    start_time=start,
                    end_time=end,
                    responsible=service.responsible,
                    status="Agendado",
                    address=client.address,
                    amount_cents=service.price_cents,
                )
                db.add(row)
                counts["agenda"] += 1
                if admin:
                    business.audit(db, admin, "Agenda", row, action="Completar demonstração")
    db.add(CatalogVersion(version=VERSION))
    business.commit(db)
    return counts


def complete_demo_sales(db):
    if db.get(CatalogVersion, SALES_VERSION):
        return
    emails = ["cliente@atelieverde.local"] + [
        f"cliente{i}@{domain}"
        for i in range(2, 11)
        for domain in ["atelieverde.local", "greenscape.local"]
    ]
    clients = list(
        db.scalars(
            select(User)
            .where(User.role == "customer", User.active.is_(True), User.email.in_(emails))
            .order_by(User.id)
        )
    )
    if not clients:
        return
    added = []
    for i, (category, quantity) in enumerate(
        [
            ("Vasos", 12),
            ("Substratos", 8),
            ("Fertilizantes", 6),
            ("Ferramentas", 4),
            ("Acessórios", 5),
        ]
    ):
        product = db.scalar(
            select(Product)
            .where(Product.category == category, Product.active.is_(True), Product.stock > 0)
            .order_by(Product.stock.desc(), Product.id)
        )
        if not product:
            continue
        amount = min(quantity, max(1, product.stock - 1))
        customer = clients[i % len(clients)]
        body = OrderInput(
            items=[{"product_id": product.id, "quantity": amount}],
            request_key=f"demo-sale-2026-10-05-{product.id}",
        )
        order = checkout(db, body, customer, commit=False)
        account = db.scalar(select(Ledger).where(Ledger.order_id == order.id))
        before = business.snapshot(account)
        account.status = "Pago"
        account.paid_date = today().isoformat()
        account.description = f"Venda demonstrativa · pedido #{order.id} · {category}"
        business.audit(db, customer, "Financeiro", account, before, "Pagamento demonstrativo")
        added.append({"pedido": order.id, "categoria": category, "quantidade": amount})
    db.add(CatalogVersion(version=SALES_VERSION))
    business.commit(db)
    return added


def link_demo_projects(db):
    if db.get(CatalogVersion, COHERENCE_VERSION):
        return
    admin = db.scalar(select(User).where(User.role == "admin").order_by(User.id))
    emails = ["cliente@atelieverde.local"] + [
        f"cliente{i}@{domain}"
        for i in range(2, 11)
        for domain in ["atelieverde.local", "greenscape.local"]
    ]
    client_ids = select(User.id).where(User.email.in_(emails), User.role == "customer")
    if not admin:
        return
    added = []
    for quote in db.scalars(
        select(Quote).where(Quote.status == "Aprovado", Quote.customer_id.in_(client_ids))
    ):
        if db.scalar(select(Project.id).where(Project.quote_id == quote.id)):
            continue
        customer = db.get(User, quote.customer_id)
        service = db.get(Service, quote.service_id)
        row = Project(
            name=f"{service.name} · {customer.name}",
            customer_id=customer.id,
            quote_id=quote.id,
            address=quote.address,
            area=quote.area,
            budget_cents=quote.amount_cents,
            status="Aprovado",
            start_date=today().isoformat(),
            end_date=(today() + timedelta(days=30)).isoformat(),
            description=quote.description,
            plants=quote.plants,
            materials=quote.materials,
        )
        db.add(row)
        db.flush()
        db.add(ProjectEvent(project_id=row.id, status="Aprovado", actor_id=admin.id))
        business.audit(db, admin, "Projeto", row, action="Vincular demonstração")
        added.append(row.id)
    db.add(CatalogVersion(version=COHERENCE_VERSION))
    business.commit(db)
    return added
