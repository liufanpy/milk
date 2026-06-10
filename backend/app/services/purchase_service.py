from datetime import datetime, date
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

    # ── 创建进货单 ────────────────────────────────

    def create_purchase(self, data: PurchaseCreate):
        total = sum(item.quantity * item.unit_price for item in data.items)
        doc = create_document(self.db, DocumentType.purchase)
        order = PurchaseOrder(
            document_id=doc.id,
            supplier_id=data.supplier_id,
            purchase_date=data.purchase_date,
            total_amount=total,
            note=data.note,
            status=data.status,
        )
        self.db.add(order)

        for item in data.items:
            self.db.add(PurchaseItem(
                document_id=doc.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                production_date=getattr(item, 'production_date', None),
                expiry_date=getattr(item, 'expiry_date', None),
            ))

        self.db.flush()

        if data.status == "confirmed":
            self._confirm_items(doc.id, data.items)

        self.db.commit()
        return {"id": doc.id, "order_number": doc.order_number, "status": order.status}

    # ── 确认草稿单 ────────────────────────────────

    def confirm_order(self, document_id: int, items: list | None = None):
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.document_id == document_id).first()
        if not order:
            raise ValueError("进货单不存在")
        if order.status != "draft":
            raise ValueError("仅草稿状态可确认")

        order.status = "confirmed"
        self._confirm_items(document_id, items or [])
        self.db.commit()
        return {"id": document_id, "status": "confirmed"}

    def _confirm_items(self, document_id: int, items: list):
        movements = []
        total = 0.0
        for item in items:
            qty = item["quantity"] if isinstance(item, dict) else item.quantity
            cost = item["unit_price"] if isinstance(item, dict) else item.unit_price
            pid = item["product_id"] if isinstance(item, dict) else item.product_id
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
            order = self.db.query(PurchaseOrder).filter(PurchaseOrder.document_id == document_id).first()
            self.txn_repo.create(
                category=TransactionCategory.purchase,
                amount=total,
                source_type=DocumentType.purchase,
                source_id=document_id,
            )

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
        docs = {d.id: d for d in self.db.query(
            self._doc_model()
        ).filter(
            self._doc_model().id.in_([o.document_id for o in orders])
        ).all()}
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

    def _doc_model(self):
        from app.models.document import Document
        return Document

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
        return parse_csv(file_content, validate, PURCHASE_HEADERS)

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
            if key not in groups:
                groups[key] = []
            groups[key].append(data)

        for grp_key, items in groups.items():
            doc = create_document(self.db, DocumentType.purchase)
            order = PurchaseOrder(
                document_id=doc.id,
                supplier_id=0,  # 临时，下面会设
                purchase_date=_parse_date(grp_key) if grp_key else date.today(),
                total_amount=0.0,
                status="confirmed",
            )

            total = 0.0
            movements = []
            item_objs = []
            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                p = prods.get(pname)
                if not p:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                pid, default_cost = p
                supname = (data.get("供应商名称") or data.get("supplier_name") or "").strip() or self.DFLT_SUPPLIER
                sid = suppliers.get(supname, 0)
                order.supplier_id = sid

                qty = int(float(data.get("数量") or data.get("quantity") or 0))
                cost = data.get("进价") or data.get("unit_price") or ""
                cost = float(cost) if cost else default_cost
                date_str2 = (data.get("日期") or data.get("date") or "").strip()
                item_date = _parse_date(date_str2) if date_str2 else date.today()
                total += qty * cost

                item_objs.append(PurchaseItem(
                    document_id=doc.id,
                    product_id=pid,
                    quantity=qty,
                    unit_price=cost,
                    production_date=item_date,
                ))
                movements.append({
                    "product_id": pid,
                    "direction": Direction.in_,
                    "quantity": qty,
                    "source_type": DocumentType.purchase,
                    "source_id": doc.id,
                })

            if not item_objs:
                continue

            self.db.add(order)
            for obj in item_objs:
                self.db.add(obj)
            self.db.flush()

            if movements:
                self.stock_repo.bulk_create(movements)
                if total > 0:
                    self.txn_repo.create(
                        category=TransactionCategory.purchase,
                        amount=total,
                        source_type=DocumentType.purchase,
                        source_id=doc.id,
                    )
                order.total_amount = total
                success += len(movements)

        self.db.commit()
        return {"success": success, "errors": errors}
