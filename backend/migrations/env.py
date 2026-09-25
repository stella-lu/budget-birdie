"""Alembic environment. Uses the app's own engine (so migrations run against the
same encrypted SQLCipher connection the app uses) rather than a URL from alembic.ini.
"""

from alembic import context

from app import models  # noqa: F401 — registers every table on Base.metadata
from app.db import Base, engine

target_metadata = Base.metadata


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite can't ALTER most things in place
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
