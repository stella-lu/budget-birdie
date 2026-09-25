"""Thin wrapper around macOS Keychain (via the `security` CLI). Used for secrets that
must never land in a file, env var history, or the database: the SimpleFIN access URL
(embeds HTTP Basic Auth credentials) and the database encryption passphrase.
"""

import subprocess
from typing import Optional

SIMPLEFIN_SERVICE = "budget-birdie-simplefin"
SIMPLEFIN_ACCOUNT = "access-url"
DB_SERVICE = "budget-birdie-db"
DB_ACCOUNT = "passphrase"


def set_secret(value: str, service: str = SIMPLEFIN_SERVICE, account: str = SIMPLEFIN_ACCOUNT) -> None:
    subprocess.run(["security", "delete-generic-password", "-s", service, "-a", account], capture_output=True)
    subprocess.run(
        ["security", "add-generic-password", "-s", service, "-a", account, "-w", value, "-U"],
        check=True,
        capture_output=True,
    )


def get_secret(service: str = SIMPLEFIN_SERVICE, account: str = SIMPLEFIN_ACCOUNT) -> Optional[str]:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()
