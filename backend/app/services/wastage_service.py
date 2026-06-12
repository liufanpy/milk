from datetime import datetime, date
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.wastage_order_repo import WastageOrderRepository
from app.services.document_helpers import create_document
from app.schemas.wastage import WastageCreate
from app.models.wastage_order import WastageOrder
from app.models.wastage_item import WastageItem
from app.models.product import Product
from app.enums import DocumentType, Direction, TransactionCategory

WASTAGE_HEADERS = ["产品名称", "product_name", "数量", "quantity", "原因", "reason", "日期", "date"]

DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]


def _parse_date(s: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


class WastageService:
    def __init__(self, db: Session):
        self.db = db
        self.wastage_repo = WastageOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def _create_order(self, items: list[dict], note: str = "") -> dict:
        self.stock_repo.validate_stock(items)
        costs = {p.id: p.default_purchase_price for p in self.db.query(Product).all()}

        doc = create_document(self.db, DocumentType.wastage)
        order = WastageOrder(document_id=doc.id, note=note)
        self.db.add(order)

        total_cost = 0.0
        movements = []
        for it in items:
            reason = it.get("reason", "damaged") or "damaged"
            cost = costs.get(it["product_id"], 0)
            self.db.add(WastageItem(document_id=doc.id, product_id=it["product_id"],
                                     quantity=it["quantity"], unit_price=cost, reason=reason))
            movements.append({"product_id": it["product_id"], "direction": Direction.out,
                              "quantity": it["quantity"], "source_type": DocumentType.wastage, "source_id": doc.id})
            total_cost += it["quantity"] * cost

        self.db.flush()
        self.stock_repo.bulk_create(movements)
        if total_cost > 0:
            self.txn_repo.create(category=TransactionCategory.wastage, amount=-total_cost)

        self.db.commit()
        return {"id": doc.id, "item_count": len(items), "total_cost": total_cost}

    def create_wastage(self, data: WastageCreate):
        items = [{"product_id": it.product_id, "quantity": it.quantity, "reason": getattr(it, 'reason', 'damaged')} for it in data.items]
        return self._create_order(items, data.note)

    def list_wastage(self):
        orders = self.wastage_repo.list_all()
        if not orders:
            return []

        from app.models.document import Document
        doc_ids = [o.document_id for o in orders]
        products = {p.id: p.name for p in self.db.query(Product).all()}
        docs = {d.id: d for d in self.db.query(Document).filter(Document.id.in_(doc_ids)).all()}

        items = self.db.query(WastageItem).filter(WastageItem.document_id.in_(doc_ids)).all()
        order_items: dict[int, list] = {}
        for it in items:
            order_items.setdefault(it.document_id, []).append(it)

        result = []
        for o in orders:
            o_items = order_items.get(o.document_id, [])
            parts = []
            for it in o_items[:2]:
                pname = products.get(it.product_id, "")
                parts.append(f"{pname}×{it.quantity}")
            summary = "、".join(parts)
            if len(o_items) > 2:
                summary += f" 等{len(o_items)}件"

            reasons = list({it.reason for it in o_items})
            doc = docs.get(o.document_id)

            result.append({
                "id": o.document_id,
                "order_number": doc.order_number if doc else "",
                "item_count": len(o_items),
                "reasons": reasons,
                "items_summary": summary,
                "note": o.note,
                "status": o.status,
                "created_at": str(o.created_at),
            })

        return result

    def get_wastage_detail(self, document_id: int):
        from app.models.document import Document
        order = self.wastage_repo.get_by_id(document_id)
        if not order:
            return None

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        items = self.db.query(WastageItem).filter(WastageItem.document_id == document_id).all()
        products = {p.id: p.name for p in self.db.query(Product).all()}

        def item_dict(it):
            return {
                "product_id": it.product_id,
                "product_name": products.get(it.product_id, ""),
                "quantity": it.quantity,
                "reason": it.reason,
                "unit_price": it.unit_price,
            }

        total_cost = sum(it.quantity * it.unit_price for it in items)

        return {
            "id": document_id,
            "order_number": doc.order_number if doc else "",
            "note": order.note,
            "status": order.status,
            "item_count": len(items),
            "total_cost": total_cost,
            "items": [item_dict(it) for it in items],
            "created_at": str(order.created_at),
        }

    def cancel_wastage(self, document_id: int):
        order = self.wastage_repo.get_by_id(document_id)
        if not order:
            raise ValueError("损耗单不存在")
        if order.status == "cancelled":
            raise ValueError("该损耗单已撤销")

        original_items = self.stock_repo.get_by_source(document_id)
        for m in original_items:
            self.stock_repo.bulk_create([{
                "product_id": m.product_id,
                "direction": Direction.in_,
                "quantity": m.quantity,
                "source_type": DocumentType.wastage,
                "source_id": document_id,
            }])

        self.wastage_repo.update_status(document_id, "cancelled")
        self.db.commit()
        return {"id": document_id, "status": "cancelled"}

    def _name_maps(self):
        prods = {p.name: (p.id, p.default_purchase_price) for p in self.db.query(Product).all()}
        return prods, {}

    def import_preview(self, file_content: bytes) -> dict:
        prods, _ = self._name_maps()
        valid_reasons = {"expired", "damaged", "self_consumed"}

        def validate(row: dict) -> str | bool:
            pname = (row.get("产品名称") or row.get("product_name") or "").strip()
            if not pname:
                return "产品名称为空"
            if pname not in prods:
                return f"产品'{pname}'不存在"
            qty = row.get("数量") or row.get("quantity") or "0"
            try:
                if int(float(qty)) <= 0:
                    return "数量必须大于0"
            except ValueError:
                return "数量格式错误"
            reason = (row.get("原因") or row.get("reason") or "").strip()
            if reason and reason not in valid_reasons:
                return f"原因'{reason}'无效，可选: expired/damaged/self_consumed"
            return True

        from app.services.csv_importer import parse_csv
        return parse_csv(file_content, validate, WASTAGE_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        prods, _ = self._name_maps()
        success = 0
        errors: list[dict] = []

        groups: dict[str, list[dict]] = {}
        for row in rows:
            data = row.get("data", row)
            date_str = (data.get("日期") or data.get("date") or "").strip()
            groups.setdefault(date_str or str(date.today()), []).append(data)

        for _, items in groups.items():
            parsed = []
            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                p = prods.get(pname)
                if not p:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                pid, default_cost = p
                qty = int(float(data.get("数量") or data.get("quantity") or 0))
                reason = (data.get("原因") or data.get("reason") or "").strip() or "damaged"
                parsed.append({"product_id": pid, "quantity": qty, "reason": reason})
            if parsed:
                self._create_order(parsed)
                success += len(parsed)

        return {"success": success, "errors": errors}

    def export_csv(self):
        from app.models.document import Document
        products = {p.id: p.name for p in self.db.query(Product).all()}

        rows = []
        items = (
            self.db.query(WastageItem, Document)
            .join(Document, WastageItem.document_id == Document.id)
            .order_by(Document.created_at.desc())
            .all()
        )

        for item, doc in items:
            rows.append({
                "单号": doc.order_number,
                "日期": str(doc.created_at.date()) if doc.created_at else "",
                "品名": products.get(item.product_id, ""),
                "数量": item.quantity,
                "进价": item.unit_price,
                "金额": item.quantity * item.unit_price,
                "原因": item.reason,
                "关联单据": item.source_document_id or "",
            })

        from app.services.import_helpers import make_csv_response
        return make_csv_response(rows, "wastage_export.csv")
