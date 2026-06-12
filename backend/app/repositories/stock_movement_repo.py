from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.stock_movement import StockMovement
from app.enums import Direction, DocumentType


class StockMovementRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, movements: List[dict]) -> List[StockMovement]:
        objs = [StockMovement(**m) for m in movements]
        self.db.add_all(objs)
        self.db.flush()
        return objs

    def get_by_source(self, source_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.source_id == source_id
        ).all()

    def get_inventory(self) -> list:
        """按 product_id 汇总总仓库存（store_id IS NULL）"""
        return (
            self.db.query(
                StockMovement.product_id,
                func.sum(
                    case(
                        (StockMovement.direction == Direction.in_, StockMovement.quantity),
                        (StockMovement.direction == Direction.out, -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .filter(StockMovement.store_id.is_(None))
            .group_by(StockMovement.product_id)
            .having(
                func.sum(
                    case(
                        (StockMovement.direction == Direction.in_, StockMovement.quantity),
                        (StockMovement.direction == Direction.out, -StockMovement.quantity),
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
                        (StockMovement.direction == Direction.in_, StockMovement.quantity),
                        (StockMovement.direction == Direction.out, -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .filter(StockMovement.store_id == store_id)
            .group_by(StockMovement.product_id)
            .having(
                func.sum(
                    case(
                        (StockMovement.direction == Direction.in_, StockMovement.quantity),
                        (StockMovement.direction == Direction.out, -StockMovement.quantity),
                    )
                ) != 0
            )
            .all()
        )

    def get_store_receive_since(self, store_id: int, product_id: int, since_id: int) -> int:
        """两轮盘点之间的店铺收货量，基于 stock_movement.id 游标"""
        result = (
            self.db.query(func.sum(StockMovement.quantity))
            .filter(
                StockMovement.id > since_id,
                StockMovement.store_id == store_id,
                StockMovement.product_id == product_id,
                StockMovement.direction == Direction.in_,
            )
            .scalar()
        )
        return result or 0

    def get_max_movement_id(self) -> int:
        result = self.db.query(func.max(StockMovement.id)).scalar()
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
