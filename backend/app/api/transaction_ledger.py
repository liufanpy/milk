from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.transaction import Transaction
from app.models.document import Document
from app.models.customer import Customer
from app.models.store import Store
from app.models.purchase_order import PurchaseOrder
from app.models.retail_order import RetailOrder
from app.models.distribution_order import DistributionOrder
from app.models.return_order import ReturnOrder
from app.models.wastage_order import WastageOrder
from app.models.subscription_order import SubscriptionOrder
from app.models.store_sales_order import StoreSalesOrder

router = APIRouter(prefix="/api/transaction-ledger", tags=["transaction-ledger"])

_ORDER_MODELS = [PurchaseOrder, RetailOrder, DistributionOrder, ReturnOrder, WastageOrder, SubscriptionOrder, StoreSalesOrder]


def _cancelled_doc_ids(db: Session) -> set:
    ids: set[int] = set()
    for model in _ORDER_MODELS:
        for row in db.query(model.document_id).filter(model.status == "cancelled").all():
            ids.add(row[0])
    return ids


def _order_number_map(db: Session, txns: list) -> dict:
    source_ids = {t.source_id for t in txns if t.source_id}
    if not source_ids:
        return {}
    docs = {d.id: d.order_number for d in db.query(Document).filter(Document.id.in_(source_ids)).all()}
    return {t.id: docs.get(t.source_id, "") for t in txns if t.source_id}


@router.get("")
def list_transaction_ledger(
    customer_id: int | None = Query(None),
    store_id: int | None = Query(None),
    category: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    order_number: str | None = Query(None),
    hide_cancelled: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).order_by(Transaction.created_at.asc())

    if hide_cancelled:
        cancelled = _cancelled_doc_ids(db)
        if cancelled:
            q = q.filter(Transaction.source_id.notin_(cancelled))

    if customer_id:
        q = q.filter(Transaction.customer_id == customer_id)
    if store_id == 0:
        q = q.filter(Transaction.store_id.is_(None))
    elif store_id == -1:
        q = q.filter(Transaction.store_id.isnot(None))
    elif store_id and store_id > 0:
        q = q.filter(Transaction.store_id == store_id)
    if category:
        q = q.filter(Transaction.category == category)
    if date_from:
        q = q.filter(Transaction.created_at >= date.fromisoformat(date_from))
    if date_to:
        q = q.filter(Transaction.created_at < date.fromisoformat(date_to))
    if order_number:
        matched_ids = [d.id for d in db.query(Document.id).filter(Document.order_number == order_number).all()]
        if matched_ids:
            q = q.filter(Transaction.source_id.in_(matched_ids))
        else:
            q = q.filter(Transaction.id == -1)

    txns = q.limit(500).all()
    if not txns:
        return []

    customers = {c.id: c.name for c in db.query(Customer).all()}
    store_ids = {t.store_id for t in txns if t.store_id}
    stores = {s.id: s.name for s in db.query(Store).filter(Store.id.in_(store_ids)).all()}
    order_numbers = _order_number_map(db, txns)

    balances: dict[int, float] = {}
    rows = []
    for t in txns:
        name = ""
        if t.customer_id:
            name = customers.get(t.customer_id, "")
            balances.setdefault(t.customer_id, 0.0)
            cat_val = t.category.value if hasattr(t.category, 'value') else t.category
            if cat_val in ("distribution", "retail"):
                balances[t.customer_id] += t.amount
            elif cat_val in ("payment", "refund"):
                balances[t.customer_id] -= t.amount
            bal = balances[t.customer_id] if cat_val in ("distribution", "retail", "payment", "refund") else None
        else:
            bal = None

        rows.append({
            "id": t.id,
            "customer_name": name,
            "category": t.category.value if hasattr(t.category, 'value') else t.category,
            "amount": t.amount,
            "balance": round(bal, 2) if bal is not None else None,
            "order_number": order_numbers.get(t.id, ""),
            "store_name": stores.get(t.store_id, "总仓") if t.store_id else "总仓",
            "store_id": t.store_id,
            "created_at": str(t.created_at),
        })

    return rows
