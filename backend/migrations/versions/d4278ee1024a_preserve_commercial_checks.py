"""Preserve checks in databases already upgraded by SQLite batch migration."""

import sqlalchemy as sa
from alembic import op

revision = "d4278ee1024a"
down_revision = "7360d6abb529"
branch_labels = None
depends_on = None


def upgrade():
    for table, checks in {
        "products": [
            ("ck_products_stock_nonnegative", "stock >= 0"),
            ("ck_products_price_positive", "price_cents > 0"),
        ],
        "ledger": [("ck_ledger_amount_positive", "amount_cents > 0")],
    }.items():
        existing = {
            c["sqltext"].strip() for c in sa.inspect(op.get_bind()).get_check_constraints(table)
        }
        missing = [(name, sql) for name, sql in checks if sql not in existing]
        if missing:
            with op.batch_alter_table(table) as batch:
                for name, sql in missing:
                    batch.create_check_constraint(name, sql)


def downgrade():
    # These checks were present before the commercial migration as well.
    pass
