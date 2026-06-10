from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.distribution_order import DistributionOrder


class DistributionOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> DistributionOrder:
        d = DistributionOrder(**kwargs)
        self.db.add(d)
        self.db.flush()
        return d

    def get_by_id(self, document_id: int) -> Optional[DistributionOrder]:
        return self.db.query(DistributionOrder).filter(DistributionOrder.document_id == document_id).first()

    def list_by_customer(self, customer_id: int) -> List[DistributionOrder]:
        return self.db.query(DistributionOrder).filter(DistributionOrder.customer_id == customer_id).all()

    def list_all(self, customer_id: Optional[int] = None, status: Optional[str] = None):
        q = self.db.query(DistributionOrder)
        if customer_id:
            q = q.filter(DistributionOrder.customer_id == customer_id)
        if status:
            q = q.filter(DistributionOrder.status == status)
        return q.order_by(DistributionOrder.delivery_date.desc()).all()

    def update_status(self, document_id: int, status: str):
        order = self.get_by_id(document_id)
        if order:
            order.status = status
