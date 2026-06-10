from typing import Optional
from sqlalchemy.orm import Session
from app.models.store_sales_order import StoreSalesOrder


class StoreSalesOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> StoreSalesOrder:
        order = StoreSalesOrder(**kwargs)
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, document_id: int) -> Optional[StoreSalesOrder]:
        return self.db.query(StoreSalesOrder).filter(StoreSalesOrder.document_id == document_id).first()

    def list_all(self):
        return self.db.query(StoreSalesOrder).order_by(StoreSalesOrder.check_date.desc()).all()
