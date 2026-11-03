from app.database import SessionLocal
from app.expanded_demo import ITEMS, VERSION, expand_shop, rename_demo_profiles
from app.models import CatalogVersion, Ledger, Order, Product, StockMove, Supplier, User
from sqlalchemy import func, select


def test_expansion_links_receipts_sales_and_finance_once(client):
    with SessionLocal() as db:
        db.get(User, 1).email = "admin@atelieverde.local"
        db.get(User, 2).email = "cliente@atelieverde.local"
        original_private = db.get(User, 3).name
        for i, category in enumerate(ITEMS):
            db.add(
                Supplier(
                    code=f"FOR-{i}",
                    name=f"Fornecedor {category}",
                    category=category,
                    identity_key=f"supplier-{i}",
                )
            )
        db.commit()
        rename_demo_profiles(db)
        assert db.get(User, 1).name == "Leandro"
        assert db.get(User, 2).name == "Rafael"
        assert db.get(User, 3).name == original_private
        result = expand_shop(db)
        assert len(result["products"]) == 15 and len(result["orders"]) == 5
        assert db.get(CatalogVersion, VERSION)
        for id in result["products"]:
            product = db.get(Product, id)
            moves = list(db.scalars(select(StockMove).where(StockMove.product_id == id)))
            assert len(moves) == 2 and sum(m.quantity for m in moves) == product.stock
            entry = next(m for m in moves if m.quantity > 0)
            payable = db.scalar(select(Ledger).where(Ledger.stock_move_id == entry.id))
            assert payable.amount_cents == entry.quantity * entry.unit_cost_cents
            assert payable.supplier_id == product.supplier_id
        for id in result["orders"]:
            order = db.get(Order, id)
            assert sum(item["quantity"] for item in order.items) == 6
            paid = db.scalar(select(Ledger).where(Ledger.order_id == id))
            assert paid.status == "Pago" and paid.amount_cents == order.total_cents
        counts = [
            db.scalar(select(func.count()).select_from(cls))
            for cls in [Product, Order, StockMove, Ledger]
        ]
        assert expand_shop(db) is None
        rename_demo_profiles(db)
        assert counts == [
            db.scalar(select(func.count()).select_from(cls))
            for cls in [Product, Order, StockMove, Ledger]
        ]


def test_demo_expansion_ignores_unrelated_accounts(client):
    with SessionLocal() as db:
        assert expand_shop(db) is None
        rename_demo_profiles(db)
        assert db.get(User, 1).name == "Admin"
        assert db.get(User, 2).name == "Cliente um"
