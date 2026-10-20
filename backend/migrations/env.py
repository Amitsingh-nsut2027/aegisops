from alembic import context

from database import database_engine, metadata


if context.is_offline_mode():
    context.configure(
        dialect_name="postgresql", target_metadata=metadata, literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = database_engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
