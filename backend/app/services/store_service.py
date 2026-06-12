from sqlalchemy.orm import Session
from app.repositories.store_repo import StoreRepository
from app.schemas.store import StoreCreate, StoreUpdate
from app.models.customer import Customer
from app.services.csv_importer import parse_csv
from app.services.import_helpers import make_csv_response

STORE_HEADERS = ["name", "名称", "customer_name", "客户名称", "address", "地址"]


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

    def delete(self, store_id: int) -> dict:
        ok = self.repo.delete(store_id)
        if not ok:
            raise ValueError("店铺不存在")
        self.db.commit()
        return {"id": store_id, "deleted": True}

    def export_csv(self):
        stores = self.list_stores()
        rows = []
        for s in stores:
            rows.append({
                "名称": s["name"],
                "客户名称": s["customer_name"],
                "地址": s["address"],
                "状态": s["status"],
            })
        return make_csv_response(rows, "stores.csv")

    def import_preview(self, file_content: bytes) -> dict:
        def validate(row: dict) -> str | bool:
            name = (row.get("name") or row.get("名称") or "").strip()
            if not name:
                return "名称为空"
            return True
        return parse_csv(file_content, validate, STORE_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        success = 0
        errors: list[dict] = []
        customers = {c.name: c.id for c in self.db.query(Customer).all()}
        for row in rows:
            data = row.get("data", row)
            name = (data.get("name") or data.get("名称") or "").strip()
            if not name:
                errors.append({"row": row.get("index", "?"), "msg": "名称为空"})
                continue
            cname = (data.get("customer_name") or data.get("客户名称") or "").strip()
            cid = customers.get(cname) if cname else None
            try:
                self.repo.create(
                    name=name,
                    customer_id=cid,
                    address=(data.get("address") or data.get("地址") or "").strip(),
                )
                success += 1
            except Exception as e:
                errors.append({"row": row.get("index", "?"), "msg": str(e)})
        self.db.commit()
        return {"success": success, "errors": errors}
