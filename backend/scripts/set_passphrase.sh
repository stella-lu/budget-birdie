#!/bin/bash
# Stores the database encryption passphrase in your macOS Keychain (never in a file,
# never echoed, never in shell history). Run once, before first starting the server.
# Refuses to overwrite an existing one unless --force, since changing it would lock
# you out of a database already encrypted with the old one.
set -euo pipefail
cd "$(dirname "$0")/.."
source venv/bin/activate

python - "$@" <<'PY'
import getpass, sys
sys.path.insert(0, ".")
from app import keychain

existing = keychain.get_secret(keychain.DB_SERVICE, keychain.DB_ACCOUNT)
if existing and "--force" not in sys.argv:
    print("A passphrase is already stored. Changing it would lock you out of an existing")
    print("encrypted database. Re-run with --force only if you know what you're doing.")
    sys.exit(1)

print("Choose a passphrase for your budget database. Make it long and unique.")
print("If you forget it the encrypted db is unrecoverable (your plaintext JSON backups still work).")
a = getpass.getpass("Passphrase: ")
b = getpass.getpass("Again: ")
if a != b or len(a) < 12:
    print("Didn't match, or shorter than 12 characters. Nothing saved.")
    sys.exit(1)
keychain.set_secret(a, keychain.DB_SERVICE, keychain.DB_ACCOUNT)
print("Saved to Keychain. Start the server as usual.")
PY
