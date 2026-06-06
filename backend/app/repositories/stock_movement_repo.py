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

    def get_by_delivery(self, delivery_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.delivery_id == delivery_id
        ).all()

    def get_by_purchase_order(self, purchase_order_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.purchase_order_id == purchase_order_id
        ).all()

    def get_by_retail_order(self, retail_order_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.retail_order_id == retail_order_id,
            StockMovement.reason == "retail",
        ).all()

    def get_by_subscription_order(self, subscription_order_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.subscription_order_id == subscription_order_id
        ).all()

    def get_inventory(self) -> list:
        """按 product_id 汇总库存（不再按 shelf_id 分组）"""
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

    def validate_stock(self, items: list):
        """库存校验：按 product_id 汇总检查"""
        inventory = {
            r.product_id: r.stock
            for r in self.get_inventory()
        }
        # 合并同产品多行
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
