# Budget Birdie

A local-only, envelope-budgeting app (YNAB-style), built to run entirely on one laptop.
See the [design doc](https://claude.ai/code/artifact/ece60242-9d9f-4660-bfb1-2f5b85ed2dca) for architecture and scope.

## Status

Phase 0 (core ledger) is implemented: accounts, category groups/categories, manual
transactions (with splits and transfers), assign/un-assign money, Ready to Assign, and
automatic credit-card overspending coverage. No bank sync, encryption, or goals yet —
see the design doc's phased plan.

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
