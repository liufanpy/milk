from datetime import datetime, date
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.retail_order_repo import RetailOrderRepository
from app.services.document_helpers import create_document
from app.schemas.sale import SaleCreate
from app.models.retail_order import RetailOrder
from app.models.retail_item import RetailItem
from app.models.transaction import Transaction
from app.models.product import Product
from app.models.customer import Customer
from app.services.pricing import resolve_price
from app.enums import DocumentType, Direction, TransactionCategory

SALE_HEADERS = ["产品名称", "product_name", "数量", "quantity", "售价", "unit_price", "客户名称", "customer_name", "日期", "date"]

DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]


def _parse_date(s: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


class SaleService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.retail_repo = RetailOrderRepository(db)

    def _create_order(self, customer_id: int | None, items: list[dict], paid: bool = True, note: str = "") -> dict:
        self.stock_repo.validate_stock(items)

        doc = create_document(self.db, DocumentType.retail)
        order = RetailOrder(document_id=doc.id, customer_id=customer_id, status="confirmed", note=note)
        self.db.add(order)

        total = 0.0
        movements = []
        for it in items:
            total += it["quantity"] * it["unit_price"]
            self.db.add(RetailItem(document_id=doc.id, product_id=it["product_id"],
                                    quantity=it["quantity"], unit_price=it["unit_price"]))
            movements.append({"product_id": it["product_id"], "direction": Direction.out,
                              "quantity": it["quantity"], "source_type": DocumentType.retail, "source_id": doc.id})

        self.db.flush()
        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(customer_id=customer_id, category=TransactionCategory.retail,
                                 amount=total, source_type=DocumentType.retail, source_id=doc.id)
        if paid and total > 0:
            self.txn_repo.create(customer_id=customer_id, category=TransactionCategory.payment,
                                 amount=total, source_type=DocumentType.retail, source_id=doc.id)

        self.db.commit()
        return {"total": total, "item_count": len(items), "retail_order_id": doc.id}

    def create_sale(self, data: SaleCreate):
        items = [{"product_id": it.product_id, "quantity": it.quantity, "unit_price": it.unit_price} for it in data.items]
        return self._create_order(data.customer_id, items, data.paid, data.note)

    def list_sales(self):
        orders = self.db.query(RetailOrder).order_by(RetailOrder.created_at.desc()).all()
        if not orders:
            return []

        order_doc_ids = [o.document_id for o in orders]
        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        products = {p.id: p.name for p in self.db.query(Product).all()}

        from app.models.document import Document
        docs = {d.id: d for d in self.db.query(Document).filter(Document.id.in_(order_doc_ids)).all()}

        items = (
            self.db.query(RetailItem)
            .filter(RetailItem.document_id.in_(order_doc_ids))
            .all()
        )

        paid_ids = {
            t.source_id
            for t in self.db.query(Transaction).filter(
                Transaction.source_type == DocumentType.retail,
                Transaction.source_id.in_(order_doc_ids),
                Transaction.category == TransactionCategory.payment,
            ).all()
        }

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

            order_total = sum(it.quantity * it.unit_price for it in o_items)
            doc = docs.get(o.document_id)

            result.append({
                "id": o.document_id,
                "order_number": doc.order_number if doc else "",
                "customer_id": o.customer_id,
                "customer_name": customers.get(o.customer_id, "散客") if o.customer_id else "散客",
                "item_count": len(o_items),
                "total_amount": order_total,
                "paid": o.document_id in paid_ids,
                "status": o.status,
                "items_summary": summary,
                "created_at": str(o.created_at),
            })

        return result

    def get_sale_detail(self, document_id: int):
        order = self.retail_repo.get_by_id(document_id)
        if not order:
            return None

        from app.models.document import Document
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        items = self.db.query(RetailItem).filter(RetailItem.document_id == document_id).all()
        products = {p.id: p.name for p in self.db.query(Product).all()}
        customers = {c.id: c.name for c in self.db.query(Customer).all()}

        paid = (
            self.db.query(Transaction).filter(
                Transaction.source_type == DocumentType.retail,
                Transaction.source_id == document_id,
                Transaction.category == TransactionCategory.payment,
            ).first()
            is not None
        )

        def item_dict(it):
            return {
                "product_id": it.product_id,
                "product_name": products.get(it.product_id, ""),
                "quantity": it.quantity,
                "unit_price": it.unit_price,
            }

        return {
            "id": document_id,
            "order_number": doc.order_number if doc else "",
            "customer_id": order.customer_id,
            "customer_name": customers.get(order.customer_id, "散客") if order.customer_id else "散客",
            "item_count": len(items),
            "total_amount": sum(it.quantity * it.unit_price for it in items),
            "paid": paid,
            "status": order.status,
            "items_summary": "",
            "items": [item_dict(it) for it in items],
            "created_at": str(order.created_at),
        }

    def mark_paid(self, document_id: int):
        order = self.retail_repo.get_by_id(document_id)
        if not order:
            raise ValueError("销售记录不存在")
        if order.status == "cancelled":
            raise ValueError("已撤销的销售无法收款")

        existing = (
            self.db.query(Transaction)
            .filter(
                Transaction.source_id == document_id,
                Transaction.category == TransactionCategory.payment,
            )
            .first()
        )
        if existing:
            return {"id": document_id, "paid": True}

        income = (
            self.db.query(Transaction)
            .filter(
                Transaction.source_id == document_id,
                Transaction.category == TransactionCategory.retail,
            )
            .first()
        )
        if not income:
            raise ValueError("未找到收入记录")

        self.txn_repo.create(
            customer_id=order.customer_id,
            category=TransactionCategory.payment,
            amount=income.amount,
            source_type=DocumentType.retail,
            source_id=document_id,
        )
        self.db.commit()
        return {"id": document_id, "paid": True}

    def cancel_sale(self, document_id: int):
        order = self.retail_repo.get_by_id(document_id)
        if not order:
            raise ValueError("销售记录不存在")
        if order.status == "cancelled":
            raise ValueError("该销售已撤销")

        # 查原始出库 movements
        original_items = self.stock_repo.get_by_source(document_id)
        reverses = []
        for m in original_items:
            reverses.append({
                "product_id": m.product_id,
                "direction": Direction.in_,
                "quantity": m.quantity,
                "source_type": DocumentType.retail,
                "source_id": document_id,
            })

        if reverses:
            self.stock_repo.bulk_create(reverses)

        # 反向冲抵账务
        original_txns = (
            self.db.query(Transaction)
            .filter(
                Transaction.source_id == document_id,
            )
            .all()
        )
        for t in original_txns:
            self.txn_repo.create(
                customer_id=order.customer_id,
                category=t.category,
                amount=-t.amount,
                source_type=DocumentType.retail,
                source_id=document_id,
            )

        self.retail_repo.update_status(document_id, "cancelled")
        self.db.commit()
        return {"id": document_id, "status": "cancelled"}

    # ── CSV 导入 ──

    DFLT_CUSTOMER = "散客"

    def _name_maps(self):
        prods = {p.name: p.id for p in self.db.query(Product).all()}
        customers = {c.name: c.id for c in self.db.query(Customer).all()}
        return prods, customers

    def import_preview(self, file_content: bytes) -> dict:
        prods, customers = self._name_maps()

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
            return True

        from app.services.csv_importer import parse_csv
        result = parse_csv(file_content, validate, SALE_HEADERS)

        # 对 OK 行解析价格并回填到售价列
        for row in result["rows"]:
            if row["status"] != "ok":
                continue
            d = row["data"]
            raw_price = (d.get("售价") or d.get("unit_price") or "").strip()
            if not raw_price:
                cname = (d.get("客户名称") or d.get("customer_name") or "").strip() or self.DFLT_CUSTOMER
                cid = customers.get(cname)
                pid = prods.get((d.get("产品名称") or d.get("product_name") or "").strip())
                if pid:
                    d["售价"] = str(resolve_price(cid or 0, pid, self.db))

        if "售价" not in result["headers"]:
            result["headers"].insert(2, "售价")  # 插在数量后面

        return result

    def import_confirm(self, rows: list[dict]) -> dict:
        prods, customers = self._name_maps()
        success = 0
        errors: list[dict] = []

        groups: dict[tuple, list[dict]] = {}
        for row in rows:
            data = row.get("data", row)
            cname = (data.get("客户名称") or data.get("customer_name") or "").strip() or self.DFLT_CUSTOMER
            date_str = (data.get("日期") or data.get("date") or "").strip()
            groups.setdefault((cname, date_str or str(date.today())), []).append(data)

        for (cname, _), items in groups.items():
            cid = customers.get(cname)
            parsed = []
            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                p = prods.get(pname)
                if not p:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                pid = p
                qty = int(float(data.get("数量") or data.get("quantity") or 0))
                raw_price = (data.get("售价") or data.get("unit_price") or "").strip()
                if raw_price:
                    price = float(raw_price)
                else:
                    price = resolve_price(cid, pid, self.db)
                parsed.append({"product_id": pid, "quantity": qty, "unit_price": price})
            if parsed:
                self._create_order(cid, parsed)
                success += len(parsed)

        return {"success": success, "errors": errors}

    def export_csv(self):
        from app.models.document import Document
        products = {p.id: p.name for p in self.db.query(Product).all()}
        customers = {c.id: c.name for c in self.db.query(Customer).all()}

        items = (
            self.db.query(RetailItem, Document, RetailOrder)
            .join(Document, RetailItem.document_id == Document.id)
            .join(RetailOrder, RetailItem.document_id == RetailOrder.document_id)
            .order_by(Document.created_at.desc())
            .all()
        )

        paid_ids = {
            t.source_id
            for t in self.db.query(Transaction).filter(
                Transaction.source_type == DocumentType.retail,
                Transaction.category == TransactionCategory.payment,
            ).all()
        }

        rows = []
        for item, doc, order in items:
            rows.append({
                "单号": doc.order_number,
                "客户": customers.get(order.customer_id, "散客") if order.customer_id else "散客",
                "日期": str(order.created_at.date()) if order.created_at else "",
                "品名": products.get(item.product_id, ""),
                "数量": item.quantity,
                "售价": item.unit_price,
                "折扣": item.discount,
                "实收": round(item.quantity * item.unit_price - item.discount, 2),
                "付款状态": "已付" if item.document_id in paid_ids else "未付",
            })

        from app.services.import_helpers import make_csv_response
        return make_csv_response(rows, "retail_export.csv")
