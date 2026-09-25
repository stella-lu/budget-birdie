"""Runs Alembic migrations at startup so schema changes never require wiping the db."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.db import engine

BACKEND_DIR = Path(__file__).resolve().parent.parent


def upgrade_to_head() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))

    tables = set(inspect(engine).get_table_names())
    if "accounts" in tables and "alembic_version" not in tables:
        # Created by the pre-Alembic create_all() — already matches the baseline
        # revision, so just record that instead of trying to create tables again.
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")
