from sqlalchemy.orm import Session
from app.repositories.supplier_repo import SupplierRepository
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.csv_importer import parse_csv

SUPPLIER_HEADERS = ["name", "名称", "contact", "联系人", "phone", "电话"]


class SupplierService:
    def __init__(self, db: Session):
        self.repo = SupplierRepository(db)
        self.db = db

    def list_suppliers(self, keyword: str = ""):
        return self.repo.search(keyword)

    def get_supplier(self, supplier_id: int):
        return self.repo.get_by_id(supplier_id)

    def create_supplier(self, data: SupplierCreate):
        return self.repo.create(**data.model_dump())

    def update_supplier(self, supplier_id: int, data: SupplierUpdate):
        return self.repo.update(supplier_id, **data.model_dump(exclude_unset=True))

    def delete_supplier(self, supplier_id: int):
        return self.repo.delete(supplier_id)

    def export_csv(self) -> str:
        suppliers = self.repo.get_all(limit=10000)
        headers = ["名称", "联系人", "电话"]
        lines = [",".join(headers)]
        for s in suppliers:
            lines.append(",".join([s.name, s.contact, s.phone]))
        return "\n".join(lines)

    def import_preview(self, file_content: bytes) -> dict:
        def validate(row: dict) -> str | bool:
            name = (row.get("name") or row.get("名称") or "").strip()
            if not name:
                return "名称为空"
            if self.repo.get_by_name(name):
                return f"'{name}' 已存在"
            return True
        return parse_csv(file_content, validate, SUPPLIER_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        success = 0
        errors: list[dict] = []
        for row in rows:
            data = row.get("data", row)
            name = (data.get("name") or data.get("名称") or "").strip()
            if not name:
                errors.append({"row": row.get("index", "?"), "msg": "名称为空"})
                continue
            if self.repo.get_by_name(name):
                errors.append({"row": row.get("index", "?"), "msg": f"'{name}' 已存在"})
                continue
            try:
                self.repo.create(
                    name=name,
                    contact=(data.get("contact") or data.get("联系人") or "").strip(),
                    phone=(data.get("phone") or data.get("电话") or "").strip(),
                )
                success += 1
            except Exception as e:
                errors.append({"row": row.get("index", "?"), "msg": str(e)})
        return {"success": success, "errors": errors}
