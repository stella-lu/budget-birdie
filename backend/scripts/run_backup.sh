#!/bin/bash
# Runs the export, then pushes backups/ to the configured rclone remote.
# Called nightly by the launchd job (see install_backup_job.sh), or run by hand.
set -euo pipefail

cd "$(dirname "$0")/.."

source venv/bin/activate
python scripts/backup.py

REMOTE="${BUDGET_BIRDIE_RCLONE_REMOTE:-gdrive:budget-birdie-backups}"
if command -v rclone >/dev/null 2>&1; then
  rclone sync backups/ "$REMOTE" --create-empty-src-dirs
  echo "Synced backups/ to $REMOTE"
else
  echo "rclone not found on PATH — backup exported locally only, not synced to $REMOTE" >&2
fi
