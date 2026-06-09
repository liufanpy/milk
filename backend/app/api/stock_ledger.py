from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.stock_movement import StockMovement
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.retail_order import RetailOrder
from app.models.return_order import ReturnOrder
from app.models.wastage_order import WastageOrder
from app.models.delivery import Delivery
from app.models.subscription_order import SubscriptionOrder
from app.models.inventory_check import InventoryCheck

router = APIRouter(prefix="/api/stock-ledger", tags=["stock-ledger"])

_SOURCE_MODELS = {
    "purchase": PurchaseOrder,
    "retail": RetailOrder,
    "return": ReturnOrder,
    "wastage": WastageOrder,
    "delivery": Delivery,
    "subscription": SubscriptionOrder,
    "inventory_check": InventoryCheck,
}


def _order_number_map(db: Session, movements: list) -> dict:
    ids_by_type: dict[str, set] = {}
    for m in movements:
        if m.source_type and m.source_id:
            ids_by_type.setdefault(m.source_type, set()).add(m.source_id)

    result: dict[int, str] = {}
    for stype, ids in ids_by_type.items():
        model = _SOURCE_MODELS.get(stype)
        if not model:
            continue
        for row in db.query(model).filter(model.id.in_(ids)).all():
            for m in movements:
                if m.source_type == stype and m.source_id == row.id:
                    if row.order_number:
                        result[m.id] = row.order_number
    return result


@router.get("")
def list_stock_ledger(
    product_id: int | None = Query(None),
    store_id: int | None = Query(None),
    direction: str | None = Query(None),
    reason: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    order_number: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(StockMovement).order_by(StockMovement.created_at.asc())

    if product_id:
        q = q.filter(StockMovement.product_id == product_id)
    if store_id is not None:
        q = q.filter(StockMovement.store_id == store_id)
    if direction:
        q = q.filter(StockMovement.direction == direction)
    if reason:
        q = q.filter(StockMovement.reason == reason)
    if date_from:
        q = q.filter(StockMovement.created_at >= date.fromisoformat(date_from))
    if date_to:
        q = q.filter(StockMovement.created_at < date.fromisoformat(date_to))
    if order_number:
        filters = []
        for stype, model in _SOURCE_MODELS.items():
            matched = db.query(model.id).filter(model.order_number == order_number).all()
            if matched:
                ids = [row[0] for row in matched]
                filters.append(
                    (StockMovement.source_type == stype) & (StockMovement.source_id.in_(ids))
                )
        if filters:
            from sqlalchemy import or_
            q = q.filter(or_(*filters))
        else:
            q = q.filter(StockMovement.id == -1)

    movements = q.limit(500).all()
    if not movements:
        return []

    products = {p.id: p.name for p in db.query(Product).all()}
    order_numbers = _order_number_map(db, movements)

    balances: dict[int, dict] = {}  # product_id → {store_key: balance}, store_key=-1 means warehouse(NULL)
    rows = []
    for m in movements:
        key = m.product_id
        balances.setdefault(key, {})
        store_key = m.store_id if m.store_id is not None else -1
        balances[key].setdefault(store_key, 0)
        if m.direction == "in":
            balances[key][store_key] += m.quantity
        else:
            balances[key][store_key] -= m.quantity

        rows.append({
            "id": m.id,
            "product_id": m.product_id,
            "product_name": products.get(m.product_id, ""),
            "direction": m.direction,
            "quantity": m.quantity,
            "balance": balances[key][store_key],
            "reason": m.reason,
            "unit_price": m.unit_price or 0,
            "order_number": order_numbers.get(m.id, ""),
            "store_id": m.store_id,
            "created_at": str(m.created_at),
        })

    return rows
