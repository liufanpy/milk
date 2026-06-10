from typing import Optional
from sqlalchemy.orm import Session
from app.models.purchase_order import PurchaseOrder


class PurchaseOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> PurchaseOrder:
        order = PurchaseOrder(**kwargs)
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, document_id: int) -> Optional[PurchaseOrder]:
        return self.db.query(PurchaseOrder).filter(PurchaseOrder.document_id == document_id).first()

    def list_all(self):
        return self.db.query(PurchaseOrder).order_by(PurchaseOrder.purchase_date.desc()).all()

    def update_status(self, document_id: int, status: str):
        order = self.get_by_id(document_id)
        if order:
            order.status = status
