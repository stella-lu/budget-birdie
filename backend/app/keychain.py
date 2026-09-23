"""Thin wrapper around macOS Keychain (via the `security` CLI) for storing the
SimpleFIN access URL — it embeds HTTP Basic Auth credentials, so it belongs in
the OS keychain, not a config file or env var that might get committed or logged.
"""

import subprocess
from typing import Optional

SERVICE = "budget-birdie-simplefin"
ACCOUNT = "access-url"


def set_secret(value: str) -> None:
    subprocess.run(["security", "delete-generic-password", "-s", SERVICE, "-a", ACCOUNT], capture_output=True)
    subprocess.run(
        ["security", "add-generic-password", "-s", SERVICE, "-a", ACCOUNT, "-w", value, "-U"],
        check=True,
        capture_output=True,
    )


def get_secret() -> Optional[str]:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", SERVICE, "-a", ACCOUNT, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()
