from sqlalchemy.orm import Session
from app.models.supplier import Supplier
from app.repositories.base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    def __init__(self, db: Session):
        super().__init__(Supplier, db)

    def search(self, keyword: str = "", skip: int = 0, limit: int = 100):
        q = self.db.query(Supplier)
        if keyword:
            q = q.filter(Supplier.name.ilike(f"%{keyword}%"))
        return q.offset(skip).limit(limit).all()

    def get_by_name(self, name: str):
        return self.db.query(Supplier).filter(Supplier.name == name).first()
