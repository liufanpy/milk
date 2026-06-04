from sqlalchemy.orm import Session
from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: Session):
        super().__init__(Product, db)

    def search(self, keyword: str = "", skip: int = 0, limit: int = 100):
        q = self.db.query(Product)
        if keyword:
            q = q.filter(Product.name.ilike(f"%{keyword}%"))
        return q.offset(skip).limit(limit).all()

    def get_by_name(self, name: str):
        return self.db.query(Product).filter(Product.name == name).first()
