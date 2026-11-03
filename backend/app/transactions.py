"""Use a consistent row lock order for related commercial mutations."""

from fastapi import HTTPException
from sqlalchemy import select, text


def locked(db, cls, id):
    if db.bind.dialect.name == "sqlite":
        # Authentication reads do not begin a physical transaction in sqlite3.
        # A transaction may already hold the write lock (for example during cancellation).
        connection = db.connection().connection.driver_connection
        if not connection.in_transaction:
            db.execute(text("BEGIN IMMEDIATE"))
    row = db.scalar(
        select(cls).where(cls.id == id).with_for_update().execution_options(populate_existing=True)
    )
    if not row:
        raise HTTPException(404, "Registro não encontrado.")
    return row
