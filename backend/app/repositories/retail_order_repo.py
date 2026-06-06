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

    def get_by_id(self, order_id: int) -> RetailOrder | None:
        return self.db.query(RetailOrder).filter(RetailOrder.id == order_id).first()

    def update_status(self, order_id: int, status: str):
        order = self.get_by_id(order_id)
        if order:
            order.status = status
