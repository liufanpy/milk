from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.stock_movement import StockMovement


class StockMovementRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, movements: List[dict]) -> List[StockMovement]:
        objs = [StockMovement(**m) for m in movements]
        self.db.add_all(objs)
        self.db.flush()
        return objs

    def get_by_source(self, source_type: str, source_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.source_type == source_type,
            StockMovement.source_id == source_id,
        ).all()

    def get_by_source_reason(self, source_type: str, source_id: int, reason: str) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.source_type == source_type,
            StockMovement.source_id == source_id,
            StockMovement.reason == reason,
        ).all()

    def get_by_source_exclude_reason(self, source_type: str, source_id: int, exclude_reason: str) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.source_type == source_type,
            StockMovement.source_id == source_id,
            StockMovement.reason != exclude_reason,
        ).all()

    def get_inventory(self) -> list:
        """按 product_id 汇总总仓库存（store_id IS NULL）"""
        return (
            self.db.query(
                StockMovement.product_id,
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .filter(StockMovement.store_id.is_(None))
            .group_by(StockMovement.product_id)
            .having(
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ) != 0
            )
            .all()
        )

    def get_inventory_by_store(self, store_id: int) -> list:
        """按 product_id 汇总店铺库存"""
        return (
            self.db.query(
                StockMovement.product_id,
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .filter(StockMovement.store_id == store_id)
            .group_by(StockMovement.product_id)
            .having(
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ) != 0
            )
            .all()
        )

    def get_store_receive_between(self, store_id: int, product_id: int, from_date, to_date) -> int:
        """两次盘点之间的店铺收货总量（按 delivery_date 算）"""
        from app.models.delivery import Delivery
        result = (
            self.db.query(func.sum(StockMovement.quantity))
            .join(Delivery, (StockMovement.source_type == "delivery") & (StockMovement.source_id == Delivery.id))
            .filter(
                StockMovement.store_id == store_id,
                StockMovement.product_id == product_id,
                StockMovement.reason == "store_receive",
                Delivery.delivery_date >= from_date,
                Delivery.delivery_date < to_date,
            )
            .scalar()
        )
        return result or 0

    def validate_stock(self, items: list):
        inventory = {
            r.product_id: r.stock
            for r in self.get_inventory()
        }
        needed: dict[int, int] = {}
        for item in items:
            pid = item.product_id if hasattr(item, 'product_id') else item["product_id"]
            qty = item.quantity if hasattr(item, 'quantity') else item["quantity"]
            needed[pid] = needed.get(pid, 0) + qty
        for pid, qty in needed.items():
            stock = inventory.get(pid, 0)
            if stock < qty:
                raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {qty}")

    def list_all(self):
        return self.db.query(StockMovement).order_by(StockMovement.created_at.desc()).all()
