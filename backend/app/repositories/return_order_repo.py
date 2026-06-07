from typing import Optional
from sqlalchemy.orm import Session
from app.models.return_order import ReturnOrder


class ReturnOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> ReturnOrder:
        order = ReturnOrder(**kwargs)
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, id: int) -> Optional[ReturnOrder]:
        return self.db.query(ReturnOrder).filter(ReturnOrder.id == id).first()

    def list_all(self):
        return self.db.query(ReturnOrder).order_by(ReturnOrder.created_at.desc()).all()

    def update_status(self, order_id: int, status: str):
        order = self.get_by_id(order_id)
        if order:
            order.status = status
