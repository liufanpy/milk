from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.purchase import PurchaseCreate
from app.services.csv_importer import parse_csv
from app.models.product import Product
from app.models.shelf import Shelf
from app.models.supplier import Supplier

PURCHASE_HEADERS = ["产品名称", "product_name", "数量", "quantity", "进价", "unit_cost", "货架名称", "shelf_name", "供应商名称", "supplier_name"]


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_purchase(self, data: PurchaseCreate):
        total = 0.0
        movements = []
        for item in data.items:
            total += item.quantity * item.unit_cost
            movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "in",
                "reason": "purchase",
                "quantity": item.quantity,
                "unit_cost": item.unit_cost,
            })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                supplier_id=data.supplier_id,
                category="purchase",
                amount=total,
            )

        self.db.commit()
        return {"total": total, "item_count": len(data.items)}

    def list_purchases(self):
        return self.stock_repo.list_all()

    def _name_maps(self):
        products = {p.name: p.id for p in self.db.query(Product).all()}
        shelves = {s.name: s.id for s in self.db.query(Shelf).all()}
        suppliers = {s.name: s.id for s in self.db.query(Supplier).all()}
        return products, shelves, suppliers

    def import_preview(self, file_content: bytes) -> dict:
        products, shelves, suppliers = self._name_maps()

        def validate(row: dict) -> str | bool:
            pname = (row.get("产品名称") or row.get("product_name") or "").strip()
            if not pname:
                return "产品名称为空"
            if pname not in products:
                return f"产品'{pname}'不存在"
            qty = row.get("数量") or row.get("quantity") or "0"
            try:
                if int(float(qty)) <= 0:
                    return "数量必须大于0"
            except ValueError:
                return "数量格式错误"
            sname = (row.get("货架名称") or row.get("shelf_name") or "").strip()
            if sname and sname not in shelves:
                return f"货架'{sname}'不存在"
            supname = (row.get("供应商名称") or row.get("supplier_name") or "").strip()
            if not supname:
                return "供应商名称为空"
            if supname not in suppliers:
                return f"供应商'{supname}'不存在"
            return True

        return parse_csv(file_content, validate, PURCHASE_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        products, shelves, suppliers = self._name_maps()
        success = 0
        errors: list[dict] = []

        # 按供应商分组
        groups: dict[str, list[dict]] = {}
        for row in rows:
            data = row.get("data", row)
            supname = (data.get("供应商名称") or data.get("supplier_name") or "").strip()
            if supname not in groups:
                groups[supname] = []
            groups[supname].append(data)

        for supname, items in groups.items():
            sid = suppliers.get(supname)
            if not sid:
                for item in items:
                    errors.append({"row": item.get("index", "?"), "msg": f"供应商'{supname}'不存在"})
                continue

            total = 0.0
            movements = []
            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                pid = products.get(pname)
                if not pid:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                sname = (data.get("货架名称") or data.get("shelf_name") or "").strip()
                shelf_id = shelves.get(sname) if sname else None
                if not shelf_id:
                    errors.append({"row": data.get("index", "?"), "msg": f"货架'{sname}'不存在"})
                    continue
                qty = int(float(data.get("数量") or data.get("quantity") or 0))
                cost = float(data.get("进价") or data.get("unit_cost") or 0)
                total += qty * cost
                movements.append({
                    "product_id": pid,
                    "shelf_id": shelf_id,
                    "direction": "in",
                    "reason": "purchase",
                    "quantity": qty,
                    "unit_cost": cost,
                })

            if movements:
                self.stock_repo.bulk_create(movements)
                if total > 0:
                    self.txn_repo.create(supplier_id=sid, category="purchase", amount=total)
                success += len(movements)

        self.db.commit()
        return {"success": success, "errors": errors}
