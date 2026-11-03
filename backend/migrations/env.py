from alembic import context
from app import models  # noqa: F401 -- registra as tabelas no metadata
from app.database import Base, engine

target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        sqlite = connection.dialect.name == "sqlite"
        if sqlite:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()
        if sqlite:
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError("Migração deixou referências inválidas: " + str(violations))
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
