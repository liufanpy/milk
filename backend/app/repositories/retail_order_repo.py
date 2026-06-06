from sqlalchemy.orm import Session
from app.models.retail_order import RetailOrder


class RetailOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, customer_id: int | None = None) -> RetailOrder:
        order = RetailOrder(customer_id=customer_id)
        self.db.add(order)
        self.db.flush()
        return order
