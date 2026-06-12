from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.store import Store


class StoreRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Store:
        store = Store(**kwargs)
        self.db.add(store)
        self.db.flush()
        return store

    def get_by_id(self, store_id: int) -> Optional[Store]:
        return self.db.query(Store).filter(Store.id == store_id).first()

    def get_by_customer(self, customer_id: int) -> Optional[Store]:
        return self.db.query(Store).filter(Store.customer_id == customer_id).first()

    def list_all(self) -> List[Store]:
        return self.db.query(Store).order_by(Store.name).all()

    def update(self, store_id: int, **kwargs) -> Optional[Store]:
        store = self.get_by_id(store_id)
        if not store:
            return None
        for k, v in kwargs.items():
            if v is not None:
                setattr(store, k, v)
        self.db.flush()
        return store

    def delete(self, store_id: int) -> bool:
        store = self.get_by_id(store_id)
        if not store:
            return False
        self.db.delete(store)
        self.db.flush()
        return True
