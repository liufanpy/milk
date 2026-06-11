from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.database import get_db
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.models.transaction import Transaction
from app.models.stock_movement import StockMovement
from app.models.product import Product

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
def get_dashboard(
    date_from: str = Query(..., description="开始日期 YYYY-MM-DD"),
    date_to: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)

    sales_categories = ["retail", "subscription", "store_sales"]
    out_source_types = ["retail", "subscription", "store_sales"]

    total_sales = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category.in_(sales_categories),
        func.date(Transaction.created_at) >= d_from,
        func.date(Transaction.created_at) <= d_to,
    ).scalar() or 0.0

    total_payments = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category == "payment",
        func.date(Transaction.created_at) >= d_from,
        func.date(Transaction.created_at) <= d_to,
    ).scalar() or 0.0

    total_out = db.query(func.sum(StockMovement.quantity)).filter(
        StockMovement.direction == "out",
        StockMovement.source_type.in_(out_source_types),
        func.date(StockMovement.created_at) >= d_from,
        func.date(StockMovement.created_at) <= d_to,
    ).scalar() or 0

    total_cost = db.query(
        func.sum(StockMovement.quantity * Product.default_purchase_price)
    ).filter(
        StockMovement.direction == "out",
        StockMovement.source_type.in_(out_source_types),
        func.date(StockMovement.created_at) >= d_from,
        func.date(StockMovement.created_at) <= d_to,
    ).join(Product, StockMovement.product_id == Product.id).scalar() or 0.0

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

    cost_val = round(total_cost, 2)
    return {
        "total_sales": round(total_sales, 2),
        "total_payments": round(total_payments, 2),
        "total_cost": cost_val,
        "total_gross_profit": round(total_sales - cost_val, 2),
        "total_out_quantity": total_out,
        "low_stock": low_stock,
        "top_ar": top_ar,
    }
