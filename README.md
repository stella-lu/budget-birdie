# Budget Birdie

A local-only, envelope-budgeting app (YNAB-style), built to run entirely on one laptop.
See the [design doc](https://claude.ai/code/artifact/ece60242-9d9f-4660-bfb1-2f5b85ed2dca) for architecture and scope.

## Status

- **Phase 0 (core ledger)**: done — accounts, category groups/categories, manual
  transactions (with splits and transfers), assign/un-assign money, Ready to Assign,
  and automatic credit-card overspending coverage.
- **Phase 1 (encryption + backup)**: backup half done (plaintext JSON export +
  rclone + launchd, see below); encryption is wired up in code but **blocked** on
  this machine — see "Enabling encryption" below.
- **Phase 2+ (bank sync, goals, reports, polish)**: in progress — see the
  [design doc](https://claude.ai/code/artifact/ece60242-9d9f-4660-bfb1-2f5b85ed2dca)'s phased plan for scope.

## Running it

Requires Python 3.9+ and Node 20+.

**Backend**

```bash
cd backend
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173. The API listens on http://127.0.0.1:8000 (localhost
only — see the design doc's Storage & Security section).

Data lives in `backend/data/budget.db` (gitignored — never commit real financial data).

## Enabling encryption (Phase 1)

The db layer (`backend/app/db.py`) already supports SQLCipher: set
`BUDGET_BIRDIE_PASSPHRASE` before starting the server and it encrypts the database
file with that passphrase (SQLCipher does its own key derivation — nothing else to
configure). Without it, the app falls back to plain SQLite and prints a warning.

This needs the `sqlcipher3-binary` PyPI package, which needs a working C compiler.
**On this machine that's currently blocked**: Homebrew (and therefore
`pip install sqlcipher3-binary`'s build-from-source fallback) fails with
"Your Command Line Tools are too outdated." Fix, one time:

```bash
sudo rm -rf /Library/Developer/CommandLineTools
sudo xcode-select --install
```

That needs your password interactively, so it's not something I can run for you.
After that:

```bash
cd backend && source venv/bin/activate
pip install sqlcipher3-binary
export BUDGET_BIRDIE_PASSPHRASE="choose a strong passphrase"
uvicorn app.main:app --port 8000 --reload
```

Note this only encrypts a *fresh* database — switching an existing plaintext
`budget.db` over isn't a simple flip (SQLCipher and plain SQLite files aren't
interchangeable). Do this before you put real data in, or ask me to write a
one-time migration script when you're ready.

## Backups (Phase 1)

`backend/scripts/backup.py` exports every table to plaintext JSON under
`backend/backups/<date>/` and prunes old snapshots (last 30 days + one per month for
a year). `backend/scripts/run_backup.sh` runs that and then `rclone sync`s the
`backups/` folder to Google Drive.

One-time setup:

```bash
# 1. Point rclone at your Google Drive (opens a browser to authorize — has to be you)
~/bin/rclone config
#    n) New remote → name it "gdrive" → type "drive" → accept the defaults,
#    including the browser auth step.

# 2. Try it by hand
cd backend
./scripts/run_backup.sh

# 3. Once that works, install the nightly job (runs at 23:30 via launchd)
./scripts/install_backup_job.sh
```

`rclone` is installed at `~/bin/rclone` on this machine (Homebrew couldn't build it
either, for the same Command Line Tools reason — I used the prebuilt binary from
rclone.org instead, no compiler needed).
