from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, db: Session):
        super().__init__(Customer, db)

    def search(self, keyword: str = "", price_tier: str = "", skip: int = 0, limit: int = 100):
        q = self.db.query(Customer)
        if keyword:
            q = q.filter(Customer.name.ilike(f"%{keyword}%"))
        if price_tier:
            q = q.filter(Customer.price_tier == price_tier)
        return q.offset(skip).limit(limit).all()

    def get_by_name(self, name: str):
        return self.db.query(Customer).filter(Customer.name == name).first()
