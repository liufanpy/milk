from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.database import get_db
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.models.transaction import Transaction
from app.models.stock_movement import StockMovement

router = APIRouter(tags=["dashboard"])


@router.get("/api/receivables")
def get_receivables(db: Session = Depends(get_db)):
    repo = TransactionRepository(db)
    rows = repo.get_receivables()
    return [
        {"customer_id": r.customer_id, "ar_balance": round(r.ar_balance, 2)}
        for r in rows
    ]


@router.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    today = date.today()

    today_sales = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category.in_(["retail", "subscription", "distribution", "sale", "delivery", "delivery_cancel"]),
        func.date(Transaction.created_at) == today,
    ).scalar() or 0.0

    today_payments = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category == "payment",
        func.date(Transaction.created_at) == today,
    ).scalar() or 0.0

    today_out = db.query(func.sum(StockMovement.quantity)).filter(
        StockMovement.direction == "out",
        func.date(StockMovement.created_at) == today,
    ).scalar() or 0

    stock_repo = StockMovementRepository(db)
    inventory_rows = stock_repo.get_inventory()
    low_stock = [
        {"product_id": r.product_id, "stock": r.stock}
        for r in inventory_rows if 0 < r.stock < 10
    ]

    txn_repo = TransactionRepository(db)
    ar_rows = txn_repo.get_receivables()
    top_ar = sorted(
        [{"customer_id": r.customer_id, "ar_balance": round(r.ar_balance, 2)} for r in ar_rows],
        key=lambda x: abs(x["ar_balance"]),
        reverse=True,
    )[:5]

    return {
        "today_sales": round(today_sales, 2),
        "today_payments": round(today_payments, 2),
        "today_out_quantity": today_out,
        "low_stock": low_stock,
        "top_ar": top_ar,
    }
