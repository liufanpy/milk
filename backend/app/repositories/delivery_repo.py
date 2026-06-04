from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.delivery import Delivery


class DeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Delivery:
        d = Delivery(**kwargs)
        self.db.add(d)
        self.db.flush()
        return d

    def get_by_id(self, id: int) -> Optional[Delivery]:
        return self.db.query(Delivery).filter(Delivery.id == id).first()

    def list_by_customer(self, customer_id: int) -> List[Delivery]:
        return self.db.query(Delivery).filter(Delivery.customer_id == customer_id).all()

    def list_all(self, customer_id: Optional[int] = None, status: Optional[str] = None):
        q = self.db.query(Delivery)
        if customer_id:
            q = q.filter(Delivery.customer_id == customer_id)
        if status:
            q = q.filter(Delivery.status == status)
        return q.order_by(Delivery.delivery_date.desc()).all()
