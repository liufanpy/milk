from sqlalchemy.orm import Session
from app.repositories.shelf_repo import ShelfRepository
from app.schemas.shelf import ShelfCreate, ShelfUpdate
from app.services.csv_importer import parse_csv

SHELF_HEADERS = ["name", "名称", "customer_id", "客户ID"]


class ShelfService:
    def __init__(self, db: Session):
        self.repo = ShelfRepository(db)
        self.db = db

    def list_shelves(self):
        return self.repo.get_all()

    def get_shelf(self, shelf_id: int):
        return self.repo.get_by_id(shelf_id)

    def create_shelf(self, data: ShelfCreate):
        return self.repo.create(**data.model_dump())

    def update_shelf(self, shelf_id: int, data: ShelfUpdate):
        return self.repo.update(shelf_id, **data.model_dump(exclude_unset=True))

    def delete_shelf(self, shelf_id: int):
        return self.repo.delete(shelf_id)

    def export_csv(self) -> str:
        shelves = self.repo.get_all(limit=10000)
        headers = ["名称", "客户ID"]
        lines = [",".join(headers)]
        for s in shelves:
            lines.append(",".join([s.name, str(s.customer_id or "")]))
        return "\n".join(lines)

    def import_preview(self, file_content: bytes) -> dict:
        def validate(row: dict) -> str | bool:
            name = (row.get("name") or row.get("名称") or "").strip()
            if not name:
                return "名称为空"
            return True
        return parse_csv(file_content, validate, SHELF_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        success = 0
        errors: list[dict] = []
        for row in rows:
            data = row.get("data", row)
            name = (data.get("name") or data.get("名称") or "").strip()
            if not name:
                errors.append({"row": row.get("index", "?"), "msg": "名称为空"})
                continue
            try:
                cid = data.get("customer_id") or data.get("客户ID") or ""
                self.repo.create(
                    name=name,
                    customer_id=int(cid) if cid else None,
                )
                success += 1
            except Exception as e:
                errors.append({"row": row.get("index", "?"), "msg": str(e)})
        return {"success": success, "errors": errors}
