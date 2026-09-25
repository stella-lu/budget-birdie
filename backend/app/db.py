import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import keychain

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = os.environ.get("BUDGET_BIRDIE_DB_PATH", str(DATA_DIR / "budget.db"))

# Passphrase comes from the env var if set (handy for scripts/tests), otherwise the
# macOS Keychain (set it once with scripts/set_passphrase.sh).
PASSPHRASE = os.environ.get("BUDGET_BIRDIE_PASSPHRASE") or keychain.get_secret(
    keychain.DB_SERVICE, keychain.DB_ACCOUNT
)
ALLOW_UNENCRYPTED = os.environ.get("BUDGET_BIRDIE_ALLOW_UNENCRYPTED") == "1"


def _sqlcipher_creator():
    """Opens the db file through SQLCipher and keys it before any other statement
    runs. SQLCipher does its own PBKDF2 key derivation from the passphrase — there's
    no separate KDF step to implement here.
    """
    from pysqlcipher3 import dbapi2 as sqlcipher

    class _Connection(sqlcipher.Connection):
        # SQLAlchemy registers its regexp() helper with deterministic=True, an argument
        # this older pysqlite fork doesn't know about. Dropping it is harmless.
        def create_function(self, name, narg, func, deterministic=False):
            return super().create_function(name, narg, func)

    conn = sqlcipher.connect(DB_PATH, check_same_thread=False, factory=_Connection)
    # PRAGMA key can't take bound parameters, so quote it by hand (escape single quotes).
    escaped = PASSPHRASE.replace("'", "''")
    conn.execute(f"PRAGMA key = '{escaped}'")
    return conn


def _looks_plaintext(path: str) -> bool:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return False
    return p.read_bytes()[:16].startswith(b"SQLite format 3")


if PASSPHRASE:
    try:
        import pysqlcipher3  # noqa: F401 — presence check; _sqlcipher_creator does the real import
    except ImportError as e:
        raise RuntimeError(
            "A database passphrase is set but the 'pysqlcipher3' package isn't installed "
            "(brew install sqlcipher, then pip install pysqlcipher3 — see README). Without it "
            "the database would silently stay unencrypted, which defeats the point — refusing to start."
        ) from e
    if _looks_plaintext(DB_PATH):
        raise RuntimeError(
            f"{DB_PATH} is a plaintext SQLite file but encryption is enabled — SQLCipher can't "
            "open it. Run `python scripts/encrypt_existing_db.py` to convert it in place."
        )
    engine = create_engine("sqlite://", creator=_sqlcipher_creator)
elif ALLOW_UNENCRYPTED:
    print(f"WARNING: running UNENCRYPTED ({DB_PATH}) because BUDGET_BIRDIE_ALLOW_UNENCRYPTED=1. Dev/testing only.")
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
else:
    raise RuntimeError(
        "No database passphrase found. Run `./scripts/set_passphrase.sh` once to store one in your "
        "Keychain (or set BUDGET_BIRDIE_PASSPHRASE). For throwaway dev data only, set "
        "BUDGET_BIRDIE_ALLOW_UNENCRYPTED=1 instead."
    )


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
