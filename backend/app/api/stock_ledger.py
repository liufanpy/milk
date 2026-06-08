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

router = APIRouter(prefix="/api/stock-ledger", tags=["stock-ledger"])

_FK_MAP = [
    ("purchase_order_id", "purchase_orders"),
    ("retail_order_id", "retail_orders"),
    ("return_order_id", "return_orders"),
    ("wastage_order_id", "wastage_orders"),
    ("delivery_id", "deliveries"),
    ("subscription_order_id", "subscription_orders"),
]

_MODELS = {
    "purchase_orders": PurchaseOrder,
    "retail_orders": RetailOrder,
    "return_orders": ReturnOrder,
    "wastage_orders": WastageOrder,
    "deliveries": Delivery,
    "subscription_orders": SubscriptionOrder,
}


def _order_number_map(db: Session, movements: list) -> dict:
    ids_by_table: dict[str, set] = {}
    for m in movements:
        for fk, table in _FK_MAP:
            val = getattr(m, fk, None)
            if val:
                ids_by_table.setdefault(table, set()).add(val)

    result: dict[int, str] = {}
    for table, ids in ids_by_table.items():
        model = _MODELS[table]
        for row in db.query(model).filter(model.id.in_(ids)).all():
            for m in movements:
                for fk, t2 in _FK_MAP:
                    if t2 == table and getattr(m, fk, None) == row.id:
                        if row.order_number:
                            result[m.id] = row.order_number
    return result


@router.get("")
def list_stock_ledger(
    product_id: int | None = Query(None),
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
    if direction:
        q = q.filter(StockMovement.direction == direction)
    if date_from:
        q = q.filter(StockMovement.created_at >= date.fromisoformat(date_from))
    if date_to:
        q = q.filter(StockMovement.created_at < date.fromisoformat(date_to))
    if order_number:
        # 按单号反查：搜索各订单表 → 收集 (fk_col, id) 对
        filters = []
        for fk, table_name in _FK_MAP:
            model = _MODELS[table_name]
            matched = db.query(model.id).filter(model.order_number == order_number).all()
            if matched:
                ids = [row[0] for row in matched]
                col = getattr(StockMovement, fk)
                filters.append(col.in_(ids))
        if filters:
            from sqlalchemy import or_
            q = q.filter(or_(*filters))
        else:
            q = q.filter(StockMovement.id == -1)  # 无匹配 → 空结果
        q = q.filter(StockMovement.reason == reason)

    movements = q.limit(500).all()
    if not movements:
        return []

    products = {p.id: p.name for p in db.query(Product).all()}
    order_numbers = _order_number_map(db, movements)

    balances: dict[int, int] = {}
    rows = []
    for m in movements:
        balances.setdefault(m.product_id, 0)
        if m.direction == "in":
            balances[m.product_id] += m.quantity
        else:
            balances[m.product_id] -= m.quantity

        rows.append({
            "id": m.id,
            "product_id": m.product_id,
            "product_name": products.get(m.product_id, ""),
            "direction": m.direction,
            "quantity": m.quantity,
            "balance": balances[m.product_id],
            "reason": m.reason,
            "unit_price": m.unit_price or 0,
            "order_number": order_numbers.get(m.id, ""),
            "created_at": str(m.created_at),
        })

    return rows
