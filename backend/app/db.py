import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = os.environ.get("BUDGET_BIRDIE_DB_PATH", str(DATA_DIR / "budget.db"))
PASSPHRASE = os.environ.get("BUDGET_BIRDIE_PASSPHRASE")


def _sqlcipher_creator():
    """Opens the db file through SQLCipher and keys it before any other statement
    runs. SQLCipher does its own PBKDF2 key derivation from the passphrase — there's
    no separate KDF step to implement here.
    """
    import sqlcipher3.dbapi2 as sqlcipher

    conn = sqlcipher.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA key = ?", (PASSPHRASE,))
    conn.execute("PRAGMA cipher_compatibility = 4")
    return conn


if PASSPHRASE:
    try:
        import sqlcipher3  # noqa: F401 — presence check; _sqlcipher_creator does the real import
    except ImportError as e:
        raise RuntimeError(
            "BUDGET_BIRDIE_PASSPHRASE is set but the 'sqlcipher3' package isn't installed "
            "(pip install sqlcipher3-binary, or sqlcipher3 if you've built libsqlcipher "
            "yourself). Without it the database would silently stay unencrypted, which "
            "defeats the point — refusing to start instead."
        ) from e
    engine = create_engine("sqlite://", creator=_sqlcipher_creator)
else:
    print(
        "WARNING: BUDGET_BIRDIE_PASSPHRASE is not set — the database at "
        f"{DB_PATH} is NOT encrypted. Fine for local dev, not for real financial data. "
        "See README.md for how to enable encryption."
    )
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_connection, _):
    dbapi_connection.execute("PRAGMA foreign_keys = ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
