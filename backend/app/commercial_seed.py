"""One-time extension of the existing demo, without resetting commercial data."""

from sqlalchemy import select

from . import business
from .models import CatalogVersion, Ledger, Product, Supplier, User

VERSION = "commercial-demo-2026-10-04-v1"


def sync_commercial(db):
    if db.get(CatalogVersion, VERSION):
        return
    for user in db.scalars(select(User).where(User.role == "customer").order_by(User.id)):
        if not user.customer_code:
            user.customer_code = business.next_code(db, "CLI")
    categories = [
        ("Viveiro Verde", "Plantas", 3),
        ("Cerâmica Jardim", "Vasos", 7),
        ("Terra Boa Insumos", "Substratos", 2),
        ("AgroDistribuidora", "Fertilizantes", 4),
        ("Ferramentas Pro", "Ferramentas", 5),
        ("Jardim & Cia", "Acessórios", 3),
    ]
    by_category = {}
    for name, category, days in categories:
        row = db.scalar(select(Supplier).where(Supplier.identity_key == business.normalized(name)))
        if not row:
            row = Supplier(
                code=business.next_code(db, "FOR"),
                name=name,
                category=category,
                delivery_days=days,
                identity_key=business.normalized(name),
                notes="Fornecedor fictício para demonstração. Atualize os contatos com os dados do seu parceiro.",
            )
            db.add(row)
            db.flush()
        by_category[category] = row.id
    identities = set()
    for product in db.scalars(select(Product).order_by(Product.id)):
        if not product.supplier_id:
            product.supplier_id = by_category.get(product.category)
        if not product.identity_key:
            key = business.product_identity(product.name, product.brand, product.variant)
            if key not in identities:
                product.identity_key = key
        identities.add(product.identity_key)
    by_name = {row.name: row.id for row in db.scalars(select(Supplier))}
    for entry in db.scalars(
        select(Ledger).where(Ledger.direction == "Despesa", Ledger.supplier_id.is_(None))
    ):
        entry.supplier_id = by_name.get(entry.counterparty)
    db.add(CatalogVersion(version=VERSION))
    business.commit(db)
