from typing import Optional
from sqlalchemy.orm import Session
from app.models.wastage_order import WastageOrder


class WastageOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> WastageOrder:
        order = WastageOrder(**kwargs)
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, id: int) -> Optional[WastageOrder]:
        return self.db.query(WastageOrder).filter(WastageOrder.id == id).first()

    def list_all(self):
        return self.db.query(WastageOrder).order_by(WastageOrder.created_at.desc()).all()

    def update_status(self, order_id: int, status: str):
        order = self.get_by_id(order_id)
        if order:
            order.status = status
