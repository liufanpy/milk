from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.services.document_helpers import create_document
from app.schemas.purchase import PurchaseCreate
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_item import PurchaseItem
from app.models.product import Product
from app.models.supplier import Supplier
from app.enums import DocumentType, Direction, TransactionCategory

PURCHASE_HEADERS = ["产品名称", "product_name", "数量", "quantity", "进价", "unit_price", "供应商名称", "supplier_name", "日期", "date"]

DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]


def _parse_date(s: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    # ── 核心：创建进货单 + 品项 + 库存 + 资金 ──────

    def _create_order(self, supplier_id: int, purchase_date: date, items: list[dict], status: str = "confirmed", note: str = "") -> dict:
        """items: [{"product_id": int, "quantity": int, "unit_price": float, "production_date": date|None}]"""
        shelf_life_map = {p.id: p.shelf_life_days for p in self.db.query(Product).all()}
        total = sum(it["quantity"] * it["unit_price"] for it in items)

        doc = create_document(self.db, DocumentType.purchase)
        order = PurchaseOrder(
            document_id=doc.id,
            supplier_id=supplier_id,
            purchase_date=purchase_date,
            total_amount=total,
            note=note,
            status=status,
        )
        self.db.add(order)

        movements = []
        for it in items:
            prod_date = it.get("production_date") or date.today()
            expiry = it.get("expiry_date")
            if not expiry:
                sl = shelf_life_map.get(it["product_id"], 0)
                if sl:
                    expiry = prod_date + timedelta(days=sl)

            self.db.add(PurchaseItem(
                document_id=doc.id,
                product_id=it["product_id"],
                quantity=it["quantity"],
                unit_price=it["unit_price"],
                production_date=prod_date,
                expiry_date=expiry,
            ))
            movements.append({
                "product_id": it["product_id"],
                "direction": Direction.in_,
                "quantity": it["quantity"],
                "source_type": DocumentType.purchase,
                "source_id": doc.id,
            })

        self.db.flush()

        if status == "confirmed" and movements:
            self.stock_repo.bulk_create(movements)
        if status == "confirmed" and total > 0:
            self.txn_repo.create(
                category=TransactionCategory.purchase,
                amount=total,
                source_type=DocumentType.purchase,
                source_id=doc.id,
            )

        self.db.commit()
        return {"id": doc.id, "order_number": doc.order_number, "status": status}

    # ── 创建进货单 ────────────────────────────────

    def create_purchase(self, data: PurchaseCreate):
        items = [
            {
                "product_id": it.product_id,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "production_date": getattr(it, 'production_date', None),
                "expiry_date": getattr(it, 'expiry_date', None),
            }
            for it in data.items
        ]
        return self._create_order(data.supplier_id, data.purchase_date, items, data.status, data.note)

    # ── 确认草稿单 ────────────────────────────────

    def confirm_order(self, document_id: int, items: list | None = None):
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.document_id == document_id).first()
        if not order:
            raise ValueError("进货单不存在")
        if order.status != "draft":
            raise ValueError("仅草稿状态可确认")

        # 前端没传 items 时，从 purchase_items 表读取
        if not items:
            db_items = self.db.query(PurchaseItem).filter(PurchaseItem.document_id == document_id).all()
            items = [{"product_id": pi.product_id, "quantity": pi.quantity, "unit_price": pi.unit_price} for pi in db_items]

        movements = []
        total = 0.0
        for it in items:
            qty = it["quantity"] if isinstance(it, dict) else it.quantity
            cost = it["unit_price"] if isinstance(it, dict) else it.unit_price
            pid = it["product_id"] if isinstance(it, dict) else it.product_id
            total += qty * cost
            movements.append({
                "product_id": pid,
                "direction": Direction.in_,
                "quantity": qty,
                "source_type": DocumentType.purchase,
                "source_id": document_id,
            })

        if movements:
            self.stock_repo.bulk_create(movements)
        if total > 0:
            order.total_amount = total
            self.txn_repo.create(
                category=TransactionCategory.purchase,
                amount=total,
                source_type=DocumentType.purchase,
                source_id=document_id,
            )

        order.status = "confirmed"
        self.db.commit()
        return {"id": document_id, "status": "confirmed"}

    # ── 撤销进货单 ────────────────────────────────

    def cancel_order(self, document_id: int):
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.document_id == document_id).first()
        if not order:
            raise ValueError("进货单不存在")

        if order.status == "draft":
            order.status = "cancelled"
            self.db.commit()
            return {"id": document_id, "status": "cancelled"}

        if order.status == "confirmed":
            original_items = self.stock_repo.get_by_source(document_id)
            inventory = {r.product_id: r.stock for r in self.stock_repo.get_inventory()}
            for item in original_items:
                stock = inventory.get(item.product_id, 0)
                if stock < item.quantity:
                    raise ValueError("该进货单商品已被部分售出，库存不足，无法撤销")

            reverses = []
            reverse_total = 0.0
            purchase_items = self.db.query(PurchaseItem).filter(
                PurchaseItem.document_id == document_id
            ).all()
            price_map = {pi.product_id: pi.unit_price for pi in purchase_items}

            for item in original_items:
                unit_price = price_map.get(item.product_id, 0.0)
                reverses.append({
                    "product_id": item.product_id,
                    "direction": Direction.out,
                    "quantity": item.quantity,
                    "source_type": DocumentType.purchase,
                    "source_id": document_id,
                })
                reverse_total += item.quantity * unit_price

            if reverses:
                self.stock_repo.bulk_create(reverses)
            if reverse_total > 0:
                self.txn_repo.create(
                    category=TransactionCategory.purchase,
                    amount=-reverse_total,
                    source_type=DocumentType.purchase,
                    source_id=document_id,
                )

            order.status = "cancelled"
            order.updated_at = datetime.now()
            self.db.commit()
            return {"id": document_id, "status": "cancelled"}

    # ── 列表 ──────────────────────────────────────

    def list_purchases(self):
        orders = (
            self.db.query(PurchaseOrder)
            .order_by(PurchaseOrder.created_at.desc())
            .all()
        )
        from app.models.document import Document
        doc_ids = [o.document_id for o in orders]
        docs = {d.id: d for d in self.db.query(Document).filter(Document.id.in_(doc_ids)).all()}
        suppliers = {s.id: s.name for s in self.db.query(Supplier).all()}
        return [
            {
                "id": o.document_id,
                "order_number": docs[o.document_id].order_number if o.document_id in docs else "",
                "supplier_id": o.supplier_id,
                "supplier_name": suppliers.get(o.supplier_id, ""),
                "purchase_date": str(o.purchase_date),
                "total_amount": o.total_amount,
                "status": o.status,
                "note": o.note,
                "created_at": str(o.created_at),
            }
            for o in orders
        ]

    # ── 详情 ──────────────────────────────────────

    def get_purchase_detail(self, document_id: int):
        from app.models.document import Document
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.document_id == document_id).first()
        if not order:
            return None

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        items = self.db.query(PurchaseItem).filter(PurchaseItem.document_id == document_id).all()
        products = {p.id: p.name for p in self.db.query(Product).all()}
        suppliers = {s.id: s.name for s in self.db.query(Supplier).all()}

        def item_dir(i):
            return {
                "product_id": i.product_id,
                "product_name": products.get(i.product_id, ""),
                "quantity": i.quantity,
                "unit_price": i.unit_price,
            }

        return {
            "id": document_id,
            "order_number": doc.order_number if doc else "",
            "supplier_id": order.supplier_id,
            "supplier_name": suppliers.get(order.supplier_id, ""),
            "purchase_date": str(order.purchase_date),
            "total_amount": order.total_amount,
            "status": order.status,
            "note": order.note,
            "created_at": str(order.created_at),
            "items": [item_dir(i) for i in items],
        }

    # ── CSV 导入 ──

    DFLT_SUPPLIER = "金健牛奶"

    def _name_maps(self):
        prods = {p.name: (p.id, p.default_purchase_price) for p in self.db.query(Product).all()}
        suppliers = {s.name: s.id for s in self.db.query(Supplier).all()}
        return prods, suppliers

    def import_preview(self, file_content: bytes) -> dict:
        prods, suppliers = self._name_maps()

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
            supname = (row.get("供应商名称") or row.get("supplier_name") or "").strip() or self.DFLT_SUPPLIER
            if supname not in suppliers:
                return f"供应商'{supname}'不存在"
            return True

        from app.services.csv_importer import parse_csv
        result = parse_csv(file_content, validate, PURCHASE_HEADERS)

        for row in result["rows"]:
            if row["status"] != "ok":
                continue
            d = row["data"]
            # 回填进价
            raw_price = (d.get("进价") or d.get("unit_price") or "").strip()
            if not raw_price:
                pname = (d.get("产品名称") or d.get("product_name") or "").strip()
                p = prods.get(pname)
                if p:
                    d["进价"] = str(p[1])  # default_purchase_price
            # 回填供应商
            supname = (d.get("供应商名称") or d.get("supplier_name") or "").strip()
            if not supname:
                d["供应商名称"] = self.DFLT_SUPPLIER

        if "进价" not in result["headers"]:
            result["headers"].insert(2, "进价")
        if "供应商名称" not in result["headers"]:
            result["headers"].append("供应商名称")

        return result

    def import_confirm(self, rows: list[dict]) -> dict:
        prods, suppliers = self._name_maps()
        success = 0
        errors: list[dict] = []

        # 按 date 分组
        groups: dict[str, list[dict]] = {}
        for row in rows:
            data = row.get("data", row)
            date_str = (data.get("日期") or data.get("date") or "").strip()
            key = date_str or str(date.today())
            groups.setdefault(key, []).append(data)

        for grp_key, items in groups.items():
            buy_date = _parse_date(grp_key) if grp_key else date.today()
            sid = 0
            parsed_items = []
            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                p = prods.get(pname)
                if not p:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                pid, default_cost = p
                supname = (data.get("供应商名称") or data.get("supplier_name") or "").strip() or self.DFLT_SUPPLIER
                sid = suppliers.get(supname, 0)
                qty = int(float(data.get("数量") or data.get("quantity") or 0))
                cost = float(data.get("进价") or data.get("unit_price") or default_cost)
                date_str2 = (data.get("日期") or data.get("date") or "").strip()
                item_date = _parse_date(date_str2) if date_str2 else date.today()
                parsed_items.append({
                    "product_id": pid, "quantity": qty, "unit_price": cost,
                    "production_date": item_date,
                })

            if parsed_items:
                self._create_order(sid, buy_date, parsed_items)
                success += len(parsed_items)

        return {"success": success, "errors": errors}
