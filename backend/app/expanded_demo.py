"""One-time expansion of the fictitious shop, using actual commercial operations."""

from datetime import timedelta

from sqlalchemy import select

from . import business
from .checkout import checkout
from .clock import today
from .demo_details import barcode
from .models import CatalogVersion, Ledger, Product, Project, Quote, Supplier, User
from .schemas import OrderInput, ProductInput

VERSION = "expanded-nonplants-2026-10-05-v1"
PROFILES_VERSION = "demo-rafael-leandro-2026-10-05-v1"
ITEMS = {
    "Vasos": [
        ("Vaso de terracota 18 cm", "18 cm", 1100),
        ("Vaso autoirrigável 3 L", "3 L", 2200),
        ("Jardineira retangular 60 cm", "60 cm", 1800),
    ],
    "Substratos": [
        ("Substrato para cactos e suculentas 2 kg", "2 kg", 850),
        ("Casca de pinus 1 kg", "1 kg", 550),
        ("Fibra de coco 2 L", "2 L", 900),
    ],
    "Fertilizantes": [
        ("Húmus de minhoca 2 kg", "2 kg", 700),
        ("Bokashi orgânico 1 kg", "1 kg", 1250),
        ("Fertilizante NPK 10-10-10 500 g", "500 g", 650),
    ],
    "Ferramentas": [
        ("Tesoura de poda 20 cm", "20 cm", 1800),
        ("Pazinha de jardinagem em aço", "Manual", 850),
        ("Cultivador manual de três pontas", "Manual", 900),
    ],
    "Acessórios": [
        ("Regador plástico 5 L", "5 L", 850),
        ("Luvas de jardinagem", "Par M", 700),
        ("Etiquetas para plantas", "20 unidades", 200),
    ],
}
ASSETS = {
    "Vasos": "pots",
    "Substratos": "substrate",
    "Fertilizantes": "fertilizer",
    "Ferramentas": "tools",
    "Acessórios": "accessories",
}


def rename_demo_profiles(db):
    if db.get(CatalogVersion, PROFILES_VERSION):
        return
    admin = db.scalar(
        select(User).where(User.email == "admin@atelieverde.local", User.role == "admin")
    )
    client = db.scalar(
        select(User).where(User.email == "cliente@atelieverde.local", User.role == "customer")
    )
    if not admin or not client:
        return
    for row, name in [(admin, "Leandro"), (client, "Rafael")]:
        before = business.snapshot(row)
        old_name = row.name
        row.name = name
        if row.contact_name == old_name:
            row.contact_name = name
        business.audit(
            db, admin, "Perfil demonstrativo", row, before, "Atualizar nome demonstrativo"
        )
        for entry in db.scalars(
            select(Ledger).where(Ledger.customer_id == row.id, Ledger.counterparty == old_name)
        ):
            entry.counterparty = name
        for cls in [Quote, Project]:
            for record in db.scalars(select(cls).where(cls.customer_id == row.id)):
                if old_name in record.description:
                    record.description = record.description.replace(old_name, name)
                if cls is Project and old_name in record.name:
                    record.name = record.name.replace(old_name, name)
    db.add(CatalogVersion(version=PROFILES_VERSION))
    business.commit(db)


def expand_shop(db):
    if db.get(CatalogVersion, VERSION):
        return
    admin = db.scalar(
        select(User).where(User.email == "admin@atelieverde.local", User.role == "admin")
    )
    demo_emails = ["cliente@atelieverde.local"] + [
        f"cliente{i}@{domain}"
        for i in range(2, 11)
        for domain in ["atelieverde.local", "greenscape.local"]
    ]
    customers = list(
        db.scalars(
            select(User)
            .where(User.email.in_(demo_emails), User.role == "customer", User.active.is_(True))
            .order_by(User.id)
        )
    )
    suppliers = {
        s.category: s for s in db.scalars(select(Supplier).where(Supplier.active.is_(True)))
    }
    if not admin or not customers or not all(c in suppliers for c in ITEMS):
        return
    added, orders = [], []
    for group, (category, items) in enumerate(ITEMS.items()):
        supplier = suppliers[category]
        category_products = []
        for index, (name, variant, cost) in enumerate(items):
            ordinal = group * 3 + index
            sku = f"AV-DEMO-{ordinal + 101}"
            if db.scalar(select(Product.id).where(Product.sku == sku)):
                raise RuntimeError("SKU demonstrativo já utilizado. A expansão não foi aplicada.")
            product = business.save_product(
                db,
                ProductInput(
                    name=name,
                    category=category,
                    variant=variant,
                    brand="Ateliê Verde · demonstração",
                    sku=sku,
                    description=f"{name}. Item fictício para demonstração do catálogo e das operações. Imagem ilustrativa da categoria; especificações e condições de uso devem ser confirmadas em um cadastro real.",
                    barcode=barcode(400 + ordinal),
                    unit="pacote" if category in {"Substratos", "Fertilizantes"} else "un",
                    cost_cents=cost,
                    pricing_mode="Custo + margem",
                    markup_percent=60,
                    tax_regime="Carga efetiva",
                    tax_rates={"effective": 6},
                    supplier_id=supplier.id,
                    location=f"{group + 2}A · {category}",
                    low_stock=6,
                ),
                admin,
            )
            product.demo_asset = ASSETS[category]
            quantity = 30 + ordinal * 2
            move = business.change_stock(
                db,
                product.id,
                quantity,
                "Compra demonstrativa · ampliação do catálogo",
                admin,
                origin=supplier.name,
                destination=product.location,
                reference=f"COMPRA-DEMO-{ordinal + 101}",
                supplier_id=supplier.id,
                unit_cost_cents=cost,
                request_key=f"expanded-demo-receipt-{ordinal + 101}",
            )
            db.flush()
            account = Ledger(
                direction="Despesa",
                source="Estoque",
                supplier_id=supplier.id,
                stock_move_id=move.id,
                counterparty=supplier.name,
                description=f"Compra demonstrativa: {name}",
                due_date=(today() + timedelta(days=10)).isoformat(),
                amount_cents=quantity * cost,
            )
            db.add(account)
            business.audit(db, admin, "Financeiro", account, action="Compra demonstrativa")
            category_products.append(product)
            added.append(product.id)
        customer = customers[group % len(customers)]
        order = checkout(
            db,
            OrderInput(
                items=[
                    {"product_id": p.id, "quantity": i + 1} for i, p in enumerate(category_products)
                ],
                request_key=f"expanded-demo-sale-category-{group}",
            ),
            customer,
            commit=False,
        )
        account = db.scalar(select(Ledger).where(Ledger.order_id == order.id))
        before = business.snapshot(account)
        account.status = "Pago"
        account.paid_date = today().isoformat()
        account.description = f"Venda demonstrativa · pedido #{order.id} · {category}"
        business.audit(db, customer, "Financeiro", account, before, "Pagamento demonstrativo")
        orders.append(order.id)
    db.add(CatalogVersion(version=VERSION))
    business.commit(db)
    return {"products": added, "orders": orders, "incoming_moves": 15, "sale_moves": 15}
