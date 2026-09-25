# Budget Birdie

A local-only, envelope-budgeting app (YNAB-style), built to run entirely on one laptop.
No cloud backend, no accounts: your data lives in an encrypted database on your machine.

## Features

Category groups and envelopes, assign/un-assign money, Ready to Assign, credit-card
overspending auto-cover, goals (target balance, by date, monthly funding), splits,
transfers, reconcile, persistent category notes, undo-delete, transaction search,
spending/income reports, and automatic bank sync via SimpleFIN Bridge.

Keyboard shortcuts: `n` (register) jumps to a new transaction; `[` / `]` (budget) step
between months.

## Setup

Requires Python 3.9+, Node 20+, and (for encryption) Homebrew's `sqlcipher`.

```bash
# Backend
brew install sqlcipher
cd backend
python3.9 -m venv venv && source venv/bin/activate
CFLAGS="-I$(brew --prefix sqlcipher)/include -I$(brew --prefix sqlcipher)/include/sqlcipher" \
LDFLAGS="-L$(brew --prefix sqlcipher)/lib" pip install -r requirements.txt
./scripts/set_passphrase.sh          # once: stores your db passphrase in the macOS Keychain
uvicorn app.main:app --port 8000 --reload

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. The API only listens on localhost.

## Security model

- **Database**: encrypted at rest with SQLCipher. The passphrase lives in your macOS
  Keychain (or `BUDGET_BIRDIE_PASSPHRASE`), never in a file. The server **refuses to
  start** without one; for throwaway dev data only, `BUDGET_BIRDIE_ALLOW_UNENCRYPTED=1`
  opts out. If you forget the passphrase the encrypted db is unrecoverable (your JSON
  backups still work).
- **SimpleFIN access URL** (embeds credentials): stored in the Keychain, not the db.
- **Repo**: `backend/data/` (the db) and `backend/backups/` are gitignored. Never commit
  real financial data.
- Converting an existing plaintext db: `python scripts/encrypt_existing_db.py` (keeps the
  plaintext original as `.plaintext-bak` — delete it once verified).

## Schema changes

Alembic migrations run automatically at startup (`backend/migrations/`). After changing
`models.py`: `cd backend && alembic revision --autogenerate -m "what changed"`, review
the generated file, and restart.

## Backups

`backend/scripts/backup.py` exports every table to **plaintext JSON** under
`backend/backups/<date>/` (30 daily + 12 monthly snapshots kept). `run_backup.sh` then
`rclone sync`s that folder to Google Drive (`gdrive:budget-birdie-backups`).

Note the tradeoff: those Drive copies are human-readable and unencrypted — a deliberate
choice, so anyone with access to that Google account can read them.

```bash
rclone config                        # one-time: remote named "gdrive", type "drive"
cd backend && ./scripts/run_backup.sh   # try it once by hand
./scripts/install_backup_job.sh      # nightly at 23:30 via launchd
```

## Bank sync

Bank Sync tab → paste a SimpleFIN Bridge setup token → link each SimpleFIN account to a
local account → Sync now. Synced transactions are matched against manual entries (same
account, exact amount, within 3 days) instead of duplicated.
