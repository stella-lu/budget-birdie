"""Exports every table to plaintext JSON under backups/<date>/, then prunes old
backups (keep the last 30 daily snapshots, plus the first-of-month snapshot for
the trailing 12 months). Run manually, or nightly via the launchd job installed
by scripts/install_backup_job.sh.

Plaintext (not an encrypted archive) is a deliberate choice — see the design
doc's Backup & Recovery section. This script talks to the live db the same way
the app does (app.db respects BUDGET_BIRDIE_PASSPHRASE), so it works whether or
not encryption-at-rest is enabled.
"""

import json
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect  # noqa: E402

from app.db import engine  # noqa: E402
from app.models import Base  # noqa: E402

BACKUP_ROOT = Path(__file__).resolve().parent.parent / "backups"
DAILY_RETENTION = 30
MONTHLY_RETENTION = 12


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Not JSON serializable: {value!r}")


def export_snapshot() -> Path:
    today = date.today().isoformat()
    out_dir = BACKUP_ROOT / today
    out_dir.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            rows = [dict(row._mapping) for row in conn.execute(table.select())]
            (out_dir / f"{table.name}.json").write_text(
                json.dumps(rows, indent=2, default=_json_default)
            )

    print(f"Backed up {len(Base.metadata.sorted_tables)} tables to {out_dir}")
    return out_dir


def prune_old_backups():
    if not BACKUP_ROOT.exists():
        return
    dated_dirs = sorted(
        (d for d in BACKUP_ROOT.iterdir() if d.is_dir()),
        key=lambda d: d.name,
        reverse=True,
    )
    cutoff = date.today() - timedelta(days=DAILY_RETENTION)
    keep = set()
    months_kept = set()

    for d in dated_dirs:
        try:
            d_date = date.fromisoformat(d.name)
        except ValueError:
            continue  # not a dated backup folder — leave it alone
        month_key = (d_date.year, d_date.month)
        if d_date >= cutoff:
            keep.add(d)
        elif month_key not in months_kept and len(months_kept) < MONTHLY_RETENTION:
            months_kept.add(month_key)
            keep.add(d)

    for d in dated_dirs:
        if d not in keep:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
            print(f"Pruned old backup {d}")


if __name__ == "__main__":
    export_snapshot()
    prune_old_backups()
