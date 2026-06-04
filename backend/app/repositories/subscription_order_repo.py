from typing import Optional
from sqlalchemy.orm import Session
from app.models.subscription_order import SubscriptionOrder


class SubscriptionOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> SubscriptionOrder:
        order = SubscriptionOrder(**kwargs)
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, id: int) -> Optional[SubscriptionOrder]:
        return self.db.query(SubscriptionOrder).filter(SubscriptionOrder.id == id).first()

    def list_all(self):
        return self.db.query(SubscriptionOrder).order_by(SubscriptionOrder.created_at.desc()).all()
