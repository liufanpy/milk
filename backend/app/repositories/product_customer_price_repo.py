from sqlalchemy.orm import Session
from app.models.product_customer_price import ProductCustomerPrice
from app.repositories.base import BaseRepository


class ProductCustomerPriceRepository(BaseRepository[ProductCustomerPrice]):
    def __init__(self, db: Session):
        super().__init__(ProductCustomerPrice, db)

    def get_by_customer(self, customer_id: int):
        return self.db.query(ProductCustomerPrice).filter(
            ProductCustomerPrice.customer_id == customer_id
        ).all()
