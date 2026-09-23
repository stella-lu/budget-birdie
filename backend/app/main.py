from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.budgeting import get_or_create_rta_category
from app.db import Base, SessionLocal, engine
from app.routers import accounts, budget, categories, payees, reports, sync, transactions

app = FastAPI(title="Budget Birdie API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(payees.router)
app.include_router(transactions.router)
app.include_router(budget.router)
app.include_router(sync.router)
app.include_router(reports.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        get_or_create_rta_category(db)
        db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
