"""One-time: converts a plaintext data/budget.db into an encrypted one, in place.
The original is kept as budget.db.plaintext-bak — delete it yourself once you've
confirmed the app opens the new file, since it's an unencrypted copy of your data.
"""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pysqlcipher3 import dbapi2 as sqlcipher  # noqa: E402

from app import keychain  # noqa: E402

db_path = Path(os.environ.get("BUDGET_BIRDIE_DB_PATH", Path(__file__).resolve().parent.parent / "data" / "budget.db"))
passphrase = os.environ.get("BUDGET_BIRDIE_PASSPHRASE") or keychain.get_secret(keychain.DB_SERVICE, keychain.DB_ACCOUNT)
if not passphrase:
    sys.exit("No passphrase found — run ./scripts/set_passphrase.sh first.")
if not db_path.exists():
    sys.exit(f"{db_path} doesn't exist — nothing to convert.")
if not db_path.read_bytes()[:16].startswith(b"SQLite format 3"):
    sys.exit(f"{db_path} doesn't look like a plaintext SQLite file (already encrypted?).")

new_path = db_path.with_suffix(".db.encrypting")
new_path.unlink(missing_ok=True)
escaped = passphrase.replace("'", "''")

conn = sqlcipher.connect(str(db_path))
conn.execute(f"ATTACH DATABASE '{new_path}' AS enc KEY '{escaped}'")
conn.execute("SELECT sqlcipher_export('enc')")
conn.execute("DETACH DATABASE enc")
conn.close()

backup = db_path.with_suffix(".db.plaintext-bak")
shutil.move(str(db_path), str(backup))
shutil.move(str(new_path), str(db_path))
print(f"Encrypted {db_path}. Plaintext original kept at {backup} — delete it once you've verified.")
