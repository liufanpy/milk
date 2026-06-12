from datetime import datetime, date
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.return_order_repo import ReturnOrderRepository
from app.services.document_helpers import create_document
from app.schemas.return_schema import ReturnCreate
from app.models.return_order import ReturnOrder
from app.models.return_item import ReturnItem
from app.models.transaction import Transaction
from app.models.product import Product
from app.models.customer import Customer
from app.services.pricing import resolve_price
from app.enums import DocumentType, Direction, TransactionCategory

RETURN_HEADERS = ["产品名称", "product_name", "数量", "quantity", "退款金额", "unit_price", "客户名称", "customer_name", "日期", "date"]

DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]


def _parse_date(s: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


class ReturnService:
    def __init__(self, db: Session):
        self.db = db
        self.return_repo = ReturnOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def _create_order(self, customer_id: int, items: list[dict], note: str = "") -> dict:
        doc = create_document(self.db, DocumentType.return_order)
        order = ReturnOrder(document_id=doc.id, customer_id=customer_id, note=note)
        self.db.add(order)

        refund_total = 0.0
        for it in items:
            self.db.add(ReturnItem(document_id=doc.id, product_id=it["product_id"],
                                    quantity=it["quantity"], unit_price=it["unit_price"]))
            self.stock_repo.bulk_create([{"product_id": it["product_id"], "direction": Direction.in_,
                                          "quantity": it["quantity"], "source_type": DocumentType.return_order,
                                          "source_id": doc.id}])
            refund_total += it["quantity"] * it["unit_price"]

        if refund_total > 0:
            self.txn_repo.create(customer_id=customer_id, category=TransactionCategory.refund,
                                 amount=refund_total, source_type=DocumentType.return_order, source_id=doc.id)

        self.db.commit()
        return {"id": doc.id, "refund_total": refund_total}

    def create_return(self, data: ReturnCreate):
        items = [{"product_id": it.product_id, "quantity": it.quantity, "unit_price": it.unit_price} for it in data.items]
        return self._create_order(data.customer_id, items, data.note)

    def list_returns(self):
        orders = self.return_repo.list_all()
        if not orders:
            return []

        from app.models.document import Document
        doc_ids = [o.document_id for o in orders]
        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        products = {p.id: p.name for p in self.db.query(Product).all()}
        docs = {d.id: d for d in self.db.query(Document).filter(Document.id.in_(doc_ids)).all()}

        items = self.db.query(ReturnItem).filter(ReturnItem.document_id.in_(doc_ids)).all()
        refunds = {
            t.source_id: t.amount
            for t in self.db.query(Transaction).filter(
                Transaction.source_type == DocumentType.return_order,
                Transaction.source_id.in_(doc_ids),
                Transaction.category == TransactionCategory.refund,
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

            doc = docs.get(o.document_id)
            result.append({
                "id": o.document_id,
                "order_number": doc.order_number if doc else "",
                "customer_id": o.customer_id,
                "customer_name": customers.get(o.customer_id, ""),
                "item_count": len(o_items),
                "total_refund": refunds.get(o.document_id, 0),
                "note": o.note,
                "status": o.status,
                "items_summary": summary,
                "created_at": str(o.created_at),
            })

        return result

    def get_return_detail(self, document_id: int):
        from app.models.document import Document
        order = self.return_repo.get_by_id(document_id)
        if not order:
            return None

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        items = self.db.query(ReturnItem).filter(ReturnItem.document_id == document_id).all()
        products = {p.id: p.name for p in self.db.query(Product).all()}
        customers = {c.id: c.name for c in self.db.query(Customer).all()}

        refunds = (
            self.db.query(Transaction)
            .filter(
                Transaction.source_type == DocumentType.return_order,
                Transaction.source_id == document_id,
                Transaction.category == TransactionCategory.refund,
            ).all()
        )
        total_refund = sum(t.amount for t in refunds)

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
            "customer_name": customers.get(order.customer_id, ""),
            "item_count": len(items),
            "total_refund": total_refund,
            "note": order.note,
            "status": order.status,
            "items": [item_dict(it) for it in items],
            "transactions": [
                {"id": t.id, "category": t.category.value if hasattr(t.category, 'value') else t.category,
                 "amount": t.amount, "created_at": str(t.created_at)}
                for t in refunds
            ],
            "created_at": str(order.created_at),
        }

    def cancel_return(self, document_id: int):
        order = self.return_repo.get_by_id(document_id)
        if not order:
            raise ValueError("退货单不存在")
        if order.status == "cancelled":
            raise ValueError("该退货单已撤销")

        original_items = self.stock_repo.get_by_source(document_id)
        inventory = {r.product_id: r.stock for r in self.stock_repo.get_inventory()}
        for m in original_items:
            if m.direction == Direction.in_:
                stock = inventory.get(m.product_id, 0)
                if stock < m.quantity:
                    raise ValueError("退货商品已被售出，库存不足，无法撤销")

        for m in original_items:
            reverse_dir = Direction.out if m.direction == Direction.in_ else Direction.in_
            self.stock_repo.bulk_create([{
                "product_id": m.product_id,
                "direction": reverse_dir,
                "quantity": m.quantity,
                "source_type": DocumentType.return_order,
                "source_id": document_id,
            }])

        original_txns = (
            self.db.query(Transaction)
            .filter(
                Transaction.source_type == DocumentType.return_order,
                Transaction.source_id == document_id,
            )
            .all()
        )
        for t in original_txns:
            self.txn_repo.create(
                customer_id=order.customer_id,
                category=t.category,
                amount=-t.amount,
                source_type=DocumentType.return_order,
                source_id=document_id,
            )

        self.return_repo.update_status(document_id, "cancelled")
        self.db.commit()
        return {"id": document_id, "status": "cancelled"}

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
            cname = (row.get("客户名称") or row.get("customer_name") or "").strip()
            if not cname:
                return "客户名称为空"
            if cname not in customers:
                return f"客户'{cname}'不存在"
            return True

        from app.services.csv_importer import parse_csv
        result = parse_csv(file_content, validate, RETURN_HEADERS)

        for row in result["rows"]:
            if row["status"] != "ok":
                continue
            d = row["data"]
            raw_price = (d.get("退款金额") or d.get("unit_price") or "").strip()
            if not raw_price:
                cname = (d.get("客户名称") or d.get("customer_name") or "").strip()
                cid = customers.get(cname)
                pid = prods.get((d.get("产品名称") or d.get("product_name") or "").strip())
                if pid:
                    d["退款金额"] = str(resolve_price(cid, pid, self.db))

        if "退款金额" not in result["headers"]:
            result["headers"].insert(2, "退款金额")

        return result

    def import_confirm(self, rows: list[dict]) -> dict:
        prods, customers = self._name_maps()
        success = 0
        errors: list[dict] = []

        groups: dict[tuple, list[dict]] = {}
        for row in rows:
            data = row.get("data", row)
            cname = (data.get("客户名称") or data.get("customer_name") or "").strip()
            date_str = (data.get("日期") or data.get("date") or "").strip()
            groups.setdefault((cname, date_str or str(date.today())), []).append(data)

        for (cname, _), items in groups.items():
            cid = customers.get(cname)
            if not cid:
                continue
            parsed = []
            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                p = prods.get(pname)
                if not p:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                pid = p
                qty = int(float(data.get("数量") or data.get("quantity") or 0))
                raw_price = (data.get("退款金额") or data.get("unit_price") or "").strip()
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

        rows = []
        items = (
            self.db.query(ReturnItem, Document, ReturnOrder)
            .join(Document, ReturnItem.document_id == Document.id)
            .join(ReturnOrder, ReturnItem.document_id == ReturnOrder.document_id)
            .order_by(Document.created_at.desc())
            .all()
        )

        for item, doc, order in items:
            rows.append({
                "单号": doc.order_number,
                "客户": customers.get(order.customer_id, ""),
                "日期": str(order.created_at.date()) if order.created_at else "",
                "品名": products.get(item.product_id, ""),
                "数量": item.quantity,
                "退款金额": item.unit_price * item.quantity,
                "关联铺货单": order.original_distribution_document_id or "",
            })

        from app.services.import_helpers import make_csv_response
        return make_csv_response(rows, "return_export.csv")
