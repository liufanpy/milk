from sqlalchemy.orm import Session
from app.models.retail_order import RetailOrder


class RetailOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> RetailOrder:
        order = RetailOrder(**kwargs)
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, document_id: int) -> RetailOrder | None:
        return self.db.query(RetailOrder).filter(RetailOrder.document_id == document_id).first()

    def update_status(self, document_id: int, status: str):
        order = self.get_by_id(document_id)
        if order:
            order.status = status
