from sqlalchemy.orm import Session
from app.repositories.store_repo import StoreRepository
from app.schemas.store import StoreCreate, StoreUpdate
from app.models.customer import Customer


class StoreService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StoreRepository(db)

    def create(self, data: StoreCreate) -> dict:
        store = self.repo.create(
            name=data.name,
            customer_id=data.customer_id,
            address=data.address,
        )
        self.db.commit()
        return {"id": store.id, "name": store.name}

    def list_stores(self) -> list:
        stores = self.repo.list_all()
        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        return [
            {
                "id": s.id,
                "name": s.name,
                "customer_id": s.customer_id,
                "customer_name": customers.get(s.customer_id, ""),
                "address": s.address,
                "status": s.status,
                "created_at": str(s.created_at),
            }
            for s in stores
        ]

    def get_store(self, store_id: int) -> dict | None:
        store = self.repo.get_by_id(store_id)
        if not store:
            return None
        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        return {
            "id": store.id,
            "name": store.name,
            "customer_id": store.customer_id,
            "customer_name": customers.get(store.customer_id, ""),
            "address": store.address,
            "status": store.status,
            "created_at": str(store.created_at),
        }

    def update(self, store_id: int, data: StoreUpdate) -> dict:
        store = self.repo.update(store_id, **data.model_dump(exclude_none=True))
        if not store:
            raise ValueError("店铺不存在")
        self.db.commit()
        return {"id": store.id}
