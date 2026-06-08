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

router = APIRouter(prefix="/api/transaction-ledger", tags=["transaction-ledger"])

_FK_MAP = [
    ("purchase_order_id", "purchase_orders"),
    ("retail_order_id", "retail_orders"),
    ("return_order_id", "return_orders"),
    ("delivery_id", "deliveries"),
    ("subscription_order_id", "subscription_orders"),
]

_MODELS = {
    "purchase_orders": PurchaseOrder,
    "retail_orders": RetailOrder,
    "return_orders": ReturnOrder,
    "deliveries": Delivery,
    "subscription_orders": SubscriptionOrder,
}


def _order_number_map(db: Session, txns: list) -> dict:
    ids_by_table: dict[str, set] = {}
    for t in txns:
        for fk, table in _FK_MAP:
            val = getattr(t, fk, None)
            if val:
                ids_by_table.setdefault(table, set()).add(val)

    result: dict[int, str] = {}
    for table, ids in ids_by_table.items():
        model = _MODELS[table]
        for row in db.query(model).filter(model.id.in_(ids)).all():
            for t in txns:
                for fk, t2 in _FK_MAP:
                    if t2 == table and getattr(t, fk, None) == row.id:
                        if row.order_number:
                            result[t.id] = row.order_number
    return result


@router.get("")
def list_transaction_ledger(
    customer_id: int | None = Query(None),
    category: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    order_number: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).order_by(Transaction.created_at.asc())

    if customer_id:
        q = q.filter(Transaction.customer_id == customer_id)
    if date_from:
        q = q.filter(Transaction.created_at >= date.fromisoformat(date_from))
    if date_to:
        q = q.filter(Transaction.created_at < date.fromisoformat(date_to))
    if order_number:
        filters = []
        for fk, table_name in _FK_MAP:
            model = _MODELS[table_name]
            matched = db.query(model.id).filter(model.order_number == order_number).all()
            if matched:
                ids = [row[0] for row in matched]
                col = getattr(Transaction, fk)
                filters.append(col.in_(ids))
        if filters:
            from sqlalchemy import or_
            q = q.filter(or_(*filters))
        else:
            q = q.filter(Transaction.id == -1)
        q = q.filter(Transaction.category == category)

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
