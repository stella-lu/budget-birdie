# Budget Birdie 🐦

A local-only, envelope-budgeting app in the style of YNAB. It runs entirely on your
laptop: no cloud backend, no accounts, and your data lives in an encrypted database that
never leaves your machine (except the backups *you* choose to send to Google Drive).

**Features:** category groups and envelopes · assign/un-assign money · Ready to Assign ·
credit-card overspending auto-cover · goals (target balance, by date, monthly funding) ·
splits · transfers · reconcile · persistent category notes · undo delete · transaction
search · spending and income-vs-expense reports · bank sync via SimpleFIN Bridge.

**Shortcuts:** `n` (in a register) jumps to a new transaction · `[` / `]` (on the budget) step
between months.

## Quick start

**You need:** macOS (uses Keychain + launchd), Python 3.9+, Node 20+, [Homebrew](https://brew.sh),
and the Xcode Command Line Tools (`xcode-select --install`).

```bash
git clone https://github.com/stella-lu/budget-birdie.git && cd budget-birdie

# Backend
brew install sqlcipher
cd backend
python3.9 -m venv venv && source venv/bin/activate
CFLAGS="-I$(brew --prefix sqlcipher)/include -I$(brew --prefix sqlcipher)/include/sqlcipher" \
LDFLAGS="-L$(brew --prefix sqlcipher)/lib" pip install -r requirements.txt
./scripts/set_passphrase.sh            # one time: picks your db passphrase, stores it in Keychain
uvicorn app.main:app --port 8000 --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. Interactive API docs live at http://127.0.0.1:8000/docs.

## How it's built

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI, SQLAlchemy 2, Alembic |
| Database | SQLite encrypted with SQLCipher (`pysqlcipher3`) |
| Frontend | React + TypeScript (Vite), plain CSS, no UI libs |
| Bank sync | SimpleFIN Bridge (read-only) |
| Backups | JSON export + rclone → Google Drive, scheduled by launchd |

```
backend/app/
  budgeting.py    all the budget math (start reading here)
  models.py       tables · schemas.py API shapes · routers/ one file per resource
  db.py           encrypted engine setup · migrate.py runs Alembic at startup
  simplefin.py    bank sync client · keychain.py macOS Keychain wrapper
backend/migrations/   Alembic revisions · backend/scripts/   backup + passphrase tools
frontend/src/pages/   one component per screen · api.ts typed client for the backend
```

### Budget model (the bits worth knowing)

- **Money is integer cents** everywhere. No floats.
- **Ready to Assign** = income categorized to it − everything ever assigned to a category.
  It's derived, never stored.
- **Available** for a category = all assigned + all activity (through that month) + movements.
  It's cumulative, so unspent money rolls forward on its own.
- **Credit cards:** a purchase moves what was *available* in its category into that card's
  `Payment: <card>` category, so debt is never double-counted. Paying the card (a transfer
  into it) draws that reserve back down. Overspending isn't auto-covered; you move money
  between envelopes yourself.
- `Transaction.budget_amount_cents` normally equals `amount_cents`. It differs only on the
  "paying a card" transfer leg, where the account balance and the envelope move in opposite
  directions.
- Deletes are **soft** (`deleted_at`), which is what makes undo work. Every balance query
  filters them out.

## Security model

- **Database:** encrypted at rest. The passphrase lives in your Keychain (or
  `BUDGET_BIRDIE_PASSPHRASE`), never in a file. The server **refuses to start** without one;
  `BUDGET_BIRDIE_ALLOW_UNENCRYPTED=1` opts out for throwaway dev data. Forget the passphrase
  and the encrypted db is gone for good, so your JSON backups are the safety net.
- **SimpleFIN access URL** (it embeds credentials) is also stored in the Keychain, not the db.
- **The API has no auth.** It binds to `127.0.0.1` and CORS only allows the local frontend, so
  don't expose it to a network.
- `backend/data/` and `backend/backups/` are gitignored. Don't commit real financial data.
- Have a plaintext db? `python scripts/encrypt_existing_db.py` converts it in place (keeps a
  `.plaintext-bak` copy; delete it once you've checked the app opens).

## Backups

`scripts/backup.py` dumps every table to **plaintext JSON** in `backend/backups/<date>/`
(keeps 30 dailies + 12 monthlies), and `scripts/run_backup.sh` then `rclone sync`s that to
Google Drive. Plaintext is a deliberate tradeoff (readable and restorable with zero tooling),
but it means anyone with access to that Drive account can read your budget.

```bash
rclone config                          # one time: remote named "gdrive", type "drive"
                                       #   (tip: scope "drive.file" limits rclone to files it creates)
cd backend && ./scripts/run_backup.sh  # try it by hand first
./scripts/install_backup_job.sh        # then schedule it nightly at 23:30 (launchd)
```

Override the destination with `BUDGET_BIRDIE_RCLONE_REMOTE`. Logs: `backend/backups/launchd.log`.

## Bank sync

1. Link your banks in [SimpleFIN Bridge](https://bridge.simplefin.org) and grab a **setup token**.
2. Bank Sync tab → paste the token (single use) → link each SimpleFIN account to a local one.
3. **Sync now.** Transactions are deduped by SimpleFIN's id, and matched to your manual entries
   (same account, exact amount, within 3 days) instead of duplicated.

## Changing the schema

Migrations run automatically at startup. After editing `models.py`:

```bash
cd backend && alembic revision --autogenerate -m "what changed"   # then review the file
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No database passphrase found` | Run `./scripts/set_passphrase.sh` |
| `file is not a database` | Wrong passphrase, or the db is plaintext (see the convert script above) |
| `Address already in use` | Something's already on port 8000: `lsof -i :8000` |
| Homebrew: "Command Line Tools too outdated" | `sudo softwareupdate -i "Command Line Tools for Xcode-<version>"` |
| Vite errors on `node:` imports | You're on an old Node; use 20+ (`nvm use 20`) |

## Known limitations

- **No automated tests yet.** Everything so far was verified by hand against a running app.
- Bank sync is built to the SimpleFIN spec but hasn't been exercised against live banks.
- Undo covers deleted transactions only (no edit history). Editing a transfer means delete and re-add.
- Refunds on a credit card don't auto-reverse the envelope move.
- rclone's shared Google client_id is being retired during 2026. If Drive uploads start
  failing, [create your own client_id](https://rclone.org/drive/#making-your-own-client-id).
- Single user, single laptop, macOS only, by design.
