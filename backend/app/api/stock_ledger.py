from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.stock_movement import StockMovement
from app.models.document import Document
from app.models.product import Product
from app.models.store import Store
from app.models.purchase_order import PurchaseOrder
from app.models.retail_order import RetailOrder
from app.models.distribution_order import DistributionOrder
from app.models.return_order import ReturnOrder
from app.models.wastage_order import WastageOrder
from app.models.subscription_order import SubscriptionOrder
from app.models.store_sales_order import StoreSalesOrder

router = APIRouter(prefix="/api/stock-ledger", tags=["stock-ledger"])

_ORDER_MODELS = [PurchaseOrder, RetailOrder, DistributionOrder, ReturnOrder, WastageOrder, SubscriptionOrder, StoreSalesOrder]


def _cancelled_doc_ids(db: Session) -> set:
    ids: set[int] = set()
    for model in _ORDER_MODELS:
        for row in db.query(model.document_id).filter(model.status == "cancelled").all():
            ids.add(row[0])
    return ids


def _order_number_map(db: Session, movements: list) -> dict:
    source_ids = {m.source_id for m in movements if m.source_id}
    if not source_ids:
        return {}
    docs = {d.id: d.order_number for d in db.query(Document).filter(Document.id.in_(source_ids)).all()}
    return {m.id: docs.get(m.source_id, "") for m in movements if m.source_id}


@router.get("")
def list_stock_ledger(
    product_id: int | None = Query(None),
    store_id: int | None = Query(None),
    direction: str | None = Query(None),
    source_type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    order_number: str | None = Query(None),
    hide_cancelled: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(StockMovement).order_by(StockMovement.created_at.asc())

    if hide_cancelled:
        cancelled = _cancelled_doc_ids(db)
        if cancelled:
            q = q.filter(StockMovement.source_id.notin_(cancelled))

    if product_id:
        q = q.filter(StockMovement.product_id == product_id)
    if store_id == 0:
        q = q.filter(StockMovement.store_id.is_(None))
    elif store_id == -1:
        q = q.filter(StockMovement.store_id.isnot(None))
    elif store_id and store_id > 0:
        q = q.filter(StockMovement.store_id == store_id)
    if direction:
        q = q.filter(StockMovement.direction == direction)
    if source_type:
        q = q.filter(StockMovement.source_type == source_type)
    if date_from:
        q = q.filter(StockMovement.created_at >= date.fromisoformat(date_from))
    if date_to:
        q = q.filter(StockMovement.created_at < date.fromisoformat(date_to))
    if order_number:
        matched_ids = [d.id for d in db.query(Document.id).filter(Document.order_number == order_number).all()]
        if matched_ids:
            q = q.filter(StockMovement.source_id.in_(matched_ids))
        else:
            q = q.filter(StockMovement.id == -1)

    movements = q.limit(500).all()
    if not movements:
        return []

    products = {p.id: p.name for p in db.query(Product).all()}
    store_ids = {m.store_id for m in movements if m.store_id}
    stores = {s.id: s.name for s in db.query(Store).filter(Store.id.in_(store_ids)).all()}
    order_numbers = _order_number_map(db, movements)

    balances: dict[int, dict] = {}
    rows = []
    for m in movements:
        key = m.product_id
        balances.setdefault(key, {})
        store_key = m.store_id if m.store_id is not None else -1
        balances[key].setdefault(store_key, 0)
        if m.direction.value == "in" if hasattr(m.direction, 'value') else m.direction == "in":
            balances[key][store_key] += m.quantity
        else:
            balances[key][store_key] -= m.quantity

        rows.append({
            "id": m.id,
            "product_id": m.product_id,
            "product_name": products.get(m.product_id, ""),
            "direction": m.direction.value if hasattr(m.direction, 'value') else m.direction,
            "quantity": m.quantity,
            "balance": balances[key][store_key],
            "source_type": m.source_type.value if m.source_type and hasattr(m.source_type, 'value') else m.source_type,
            "order_number": order_numbers.get(m.id, ""),
            "store_id": m.store_id,
            "store_name": stores.get(m.store_id, "总仓") if m.store_id else "总仓",
            "created_at": str(m.created_at),
        })

    return rows
