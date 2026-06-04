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

    def get_inventory(self) -> list:
        return (
            self.db.query(
                StockMovement.product_id,
                StockMovement.shelf_id,
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .group_by(StockMovement.product_id, StockMovement.shelf_id)
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

    def list_all(self):
        return self.db.query(StockMovement).order_by(StockMovement.created_at.desc()).all()
