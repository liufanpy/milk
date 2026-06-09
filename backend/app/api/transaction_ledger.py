from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.purchase_order import PurchaseOrder
from app.models.retail_order import RetailOrder
from app.models.return_order import ReturnOrder
from app.models.delivery import Delivery
from app.models.subscription_order import SubscriptionOrder
from app.models.inventory_check import InventoryCheck

router = APIRouter(prefix="/api/transaction-ledger", tags=["transaction-ledger"])

_SOURCE_MODELS = {
    "purchase": PurchaseOrder,
    "retail": RetailOrder,
    "return": ReturnOrder,
    "delivery": Delivery,
    "subscription": SubscriptionOrder,
    "inventory_check": InventoryCheck,
}


def _order_number_map(db: Session, txns: list) -> dict:
    ids_by_type: dict[str, set] = {}
    for t in txns:
        if t.source_type and t.source_id:
            ids_by_type.setdefault(t.source_type, set()).add(t.source_id)

    result: dict[int, str] = {}
    for stype, ids in ids_by_type.items():
        model = _SOURCE_MODELS.get(stype)
        if not model:
            continue
        for row in db.query(model).filter(model.id.in_(ids)).all():
            for t in txns:
                if t.source_type == stype and t.source_id == row.id:
                    if row.order_number:
                        result[t.id] = row.order_number
    return result


@router.get("")
def list_transaction_ledger(
    customer_id: int | None = Query(None),
    store_id: int | None = Query(None),
    category: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    order_number: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).order_by(Transaction.created_at.asc())

    if customer_id:
        q = q.filter(Transaction.customer_id == customer_id)
    if store_id is not None:
        q = q.filter(Transaction.store_id == store_id)
    if category:
        q = q.filter(Transaction.category == category)
    if date_from:
        q = q.filter(Transaction.created_at >= date.fromisoformat(date_from))
    if date_to:
        q = q.filter(Transaction.created_at < date.fromisoformat(date_to))
    if order_number:
        filters = []
        for stype, model in _SOURCE_MODELS.items():
            matched = db.query(model.id).filter(model.order_number == order_number).all()
            if matched:
                ids = [row[0] for row in matched]
                filters.append(
                    (Transaction.source_type == stype) & (Transaction.source_id.in_(ids))
                )
        if filters:
            from sqlalchemy import or_
            q = q.filter(or_(*filters))
        else:
            q = q.filter(Transaction.id == -1)

    txns = q.limit(500).all()
    if not txns:
        return []

    customers = {c.id: c.name for c in db.query(Customer).all()}
    suppliers = {s.id: s.name for s in db.query(Supplier).all()}
    order_numbers = _order_number_map(db, txns)

    balances: dict[int, float] = {}
    rows = []
    for t in txns:
        name = ""
        if t.customer_id:
            name = customers.get(t.customer_id, "")
            balances.setdefault(t.customer_id, 0.0)
            if t.category in ("distribution", "retail", "subscription"):
                balances[t.customer_id] += t.amount
            elif t.category in ("payment", "refund"):
                balances[t.customer_id] -= t.amount
            bal = balances[t.customer_id]
        elif t.supplier_id:
            name = suppliers.get(t.supplier_id, "")
            bal = None
        else:
            bal = None

        rows.append({
            "id": t.id,
            "customer_name": name,
            "category": t.category,
            "amount": t.amount,
            "balance": round(bal, 2) if bal is not None else None,
            "order_number": order_numbers.get(t.id, ""),
            "created_at": str(t.created_at),
        })

    return rows
