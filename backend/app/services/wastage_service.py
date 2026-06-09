from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.wastage_order_repo import WastageOrderRepository
from app.schemas.wastage import WastageCreate, VALID_REASONS
from app.models.wastage_order import WastageOrder
from app.models.product import Product


class WastageService:
    def __init__(self, db: Session):
        self.db = db
        self.wastage_repo = WastageOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def _next_order_number(self) -> str:
        from app.services.order_number import next_order_number
        return next_order_number(self.db, WastageOrder, "WO")

    def create_wastage(self, data: WastageCreate):
        for item in data.items:
            if item.reason not in VALID_REASONS:
                raise ValueError(f"无效的损耗原因: {item.reason}")

        self.stock_repo.validate_stock(data.items)

        order = self.wastage_repo.create(note=data.note)
        order.order_number = self._next_order_number()

        product_ids = list({item.product_id for item in data.items})
        costs = {p.id: p.default_purchase_price for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()}

        movements = []
        total_cost = 0.0
        for item in data.items:
            movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": item.reason,
                "quantity": item.quantity,
                "unit_price": costs.get(item.product_id, 0),
                "source_type": "wastage",
                "source_id": order.id,
            })
            total_cost += item.quantity * costs.get(item.product_id, 0)

        self.stock_repo.bulk_create(movements)

        if total_cost > 0:
            self.txn_repo.create(
                category="wastage",
                amount=-total_cost,
            )

        self.db.commit()
        return {"id": order.id, "item_count": len(data.items), "total_cost": total_cost}

    def list_wastage(self):
        from app.models.stock_movement import StockMovement

        orders = self.wastage_repo.list_all()
        if not orders:
            return []

        products = {p.id: p.name for p in self.db.query(Product).all()}

        order_ids = [o.id for o in orders]
        movements = (
            self.db.query(StockMovement)
            .filter(
                StockMovement.source_type == "wastage",
                StockMovement.source_id.in_(order_ids),
            )
            .all()
        )

        order_items: dict[int, list] = {}
        for m in movements:
            order_items.setdefault(m.source_id, []).append(m)

        result = []
        for o in orders:
            items = order_items.get(o.id, [])
            parts = []
            for m in items[:2]:
                pname = products.get(m.product_id, "")
                parts.append(f"{pname}×{m.quantity}")
            summary = "、".join(parts)
            if len(items) > 2:
                summary += f" 等{len(items)}件"

            reasons = list({m.reason for m in items})

            result.append({
                "id": o.id,
                "order_number": o.order_number,
                "item_count": len(items),
                "reasons": reasons,
                "items_summary": summary,
                "note": o.note,
                "status": o.status,
                "created_at": str(o.created_at),
            })

        return result

    def get_wastage_detail(self, order_id: int):
        order = self.wastage_repo.get_by_id(order_id)
        if not order:
            return None

        items = self.stock_repo.get_by_source("wastage", order_id)
        products = {p.id: p.name for p in self.db.query(Product).all()}

        def item_dict(m):
            return {
                "product_id": m.product_id,
                "product_name": products.get(m.product_id, ""),
                "quantity": m.quantity,
                "reason": m.reason,
                "unit_price": m.unit_price or 0,
            }

        total_cost = sum(m.quantity * (m.unit_price or 0) for m in items)

        return {
            "id": order.id,
            "order_number": order.order_number,
            "note": order.note,
            "status": order.status,
            "item_count": len(items),
            "total_cost": total_cost,
            "items": [item_dict(m) for m in items],
            "created_at": str(order.created_at),
        }

    def cancel_wastage(self, order_id: int):
        order = self.wastage_repo.get_by_id(order_id)
        if not order:
            raise ValueError("损耗单不存在")
        if order.status == "cancelled":
            raise ValueError("该损耗单已撤销")

        original_items = self.stock_repo.get_by_source("wastage", order_id)
        for m in original_items:
            self.stock_repo.bulk_create([{
                "product_id": m.product_id,
                "direction": "in",
                "reason": "cancel",
                "quantity": m.quantity,
                "unit_price": m.unit_price or 0,
                "source_type": "wastage",
                "source_id": order_id,
            }])

        self.wastage_repo.update_status(order_id, "cancelled")
        self.db.commit()
        return {"id": order.id, "status": "cancelled"}
