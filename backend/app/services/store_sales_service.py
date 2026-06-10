from datetime import datetime, date
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.store_sales_repo import StoreSalesOrderRepository
from app.repositories.store_repo import StoreRepository
from app.services.document_helpers import create_document
from app.models.store_sales_order import StoreSalesOrder
from app.models.store_sales_item import StoreSalesItem
from app.models.product import Product
from app.models.store import Store
from app.models.product_customer_price import ProductCustomerPrice
from app.schemas.store_sales import StoreSalesCreate
from app.enums import DocumentType, Direction, TransactionCategory

STORE_SALES_HEADERS = ["产品名称", "product_name", "实盘数量", "actual_quantity", "店铺名称", "store_name", "日期", "date"]

DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]


def _parse_date(s: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


class StoreSalesService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.store_repo = StoreRepository(db)
        self.repo = StoreSalesOrderRepository(db)

    def _resolve_sale_price(self, customer_id: int, product: Product) -> float:
        custom = self.db.query(ProductCustomerPrice).filter(
            ProductCustomerPrice.customer_id == customer_id,
            ProductCustomerPrice.product_id == product.id,
        ).first()
        if custom:
            return custom.price
        return product.default_wholesale_price

    def _get_last_check_quantity(self, store_id: int, product_id: int, before_date: date) -> int:
        last = (
            self.db.query(StoreSalesItem.actual_quantity)
            .join(StoreSalesOrder)
            .filter(
                StoreSalesOrder.store_id == store_id,
                StoreSalesOrder.check_date < before_date,
                StoreSalesOrder.status == "confirmed",
                StoreSalesItem.product_id == product_id,
            )
            .order_by(StoreSalesOrder.check_date.desc())
            .first()
        )
        return last[0] if last else 0

    def _get_last_check_date(self, store_id: int, before_date: date) -> date | None:
        last = (
            self.db.query(StoreSalesOrder.check_date)
            .filter(
                StoreSalesOrder.store_id == store_id,
                StoreSalesOrder.check_date < before_date,
                StoreSalesOrder.status == "confirmed",
            )
            .order_by(StoreSalesOrder.check_date.desc())
            .first()
        )
        return last[0] if last else None

    def create(self, data: StoreSalesCreate):
        store = self.db.query(Store).filter(Store.id == data.store_id).first()
        if not store:
            raise ValueError("店铺不存在")

        doc = create_document(self.db, DocumentType.store_sales)
        order = StoreSalesOrder(
            document_id=doc.id,
            store_id=data.store_id,
            check_date=data.check_date,
            note=data.note,
        )
        self.db.add(order)
        self.db.flush()

        products = {p.id: p for p in self.db.query(Product).all()}

        last_check_date = self._get_last_check_date(data.store_id, data.check_date)
        from_dt = datetime.combine(last_check_date, datetime.min.time()) if last_check_date else datetime.min
        to_dt = datetime.combine(data.check_date, datetime.min.time())

        for item in data.items:
            beginning = self._get_last_check_quantity(data.store_id, item.product_id, data.check_date)
            received = self.stock_repo.get_store_receive_between(
                data.store_id, item.product_id, from_dt, to_dt
            )
            ending = item.actual_quantity
            sales_qty = beginning + received - ending

            product = products.get(item.product_id)
            if not product:
                continue

            self.db.add(StoreSalesItem(
                document_id=doc.id,
                product_id=item.product_id,
                beginning=beginning,
                received=received,
                actual_quantity=ending,
                sales_quantity=sales_qty,
            ))

            if sales_qty > 0:
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "direction": Direction.out,
                    "quantity": sales_qty,
                    "source_type": DocumentType.store_sales,
                    "source_id": doc.id,
                    "store_id": data.store_id,
                }])

                sale_price = self._resolve_sale_price(store.customer_id or 0, product)
                revenue = sales_qty * sale_price
                self.txn_repo.create(
                    customer_id=store.customer_id,
                    category=TransactionCategory.store_sales,
                    amount=revenue,
                    source_type=DocumentType.store_sales,
                    source_id=doc.id,
                    store_id=data.store_id,
                )

            elif sales_qty < 0:
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "direction": Direction.in_,
                    "quantity": -sales_qty,
                    "source_type": DocumentType.store_sales,
                    "source_id": doc.id,
                    "store_id": data.store_id,
                }])

        self.db.commit()
        return {"id": doc.id, "order_number": doc.order_number}

    def list_checks(self, store_id: int | None = None, date_from: str | None = None, date_to: str | None = None):
        from app.models.document import Document
        from app.models.store import Store as StoreModel
        q = self.db.query(StoreSalesOrder).order_by(StoreSalesOrder.check_date.desc())
        if store_id:
            q = q.filter(StoreSalesOrder.store_id == store_id)
        if date_from:
            q = q.filter(StoreSalesOrder.check_date >= date.fromisoformat(date_from))
        if date_to:
            q = q.filter(StoreSalesOrder.check_date < date.fromisoformat(date_to))
        checks = q.all()
        stores = {s.id: s.name for s in self.db.query(StoreModel).all()}
        doc_ids = [c.document_id for c in checks]
        docs = {d.id: d for d in self.db.query(Document).filter(Document.id.in_(doc_ids)).all()}
        return [
            {
                "id": c.document_id,
                "order_number": docs[c.document_id].order_number if c.document_id in docs else "",
                "store_id": c.store_id,
                "store_name": stores.get(c.store_id, ""),
                "check_date": str(c.check_date),
                "status": c.status,
                "item_count": self.db.query(StoreSalesItem).filter(
                    StoreSalesItem.document_id == c.document_id
                ).count(),
                "note": c.note,
                "created_at": str(c.created_at),
            }
            for c in checks
        ]

    def get_detail(self, document_id: int):
        from app.models.document import Document
        order = self.repo.get_by_id(document_id)
        if not order:
            return None
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        stores = {s.id: s.name for s in self.db.query(Store).all()}
        products = {p.id: p for p in self.db.query(Product).all()}
        items = self.db.query(StoreSalesItem).filter(StoreSalesItem.document_id == document_id).all()

        item_details = []
        for item in items:
            p = products.get(item.product_id)
            item_details.append({
                "product_id": item.product_id,
                "product_name": p.name if p else "",
                "actual_quantity": item.actual_quantity,
                "sales_quantity": item.sales_quantity,
                "beginning": item.beginning,
                "received": item.received,
                "unit_price": p.default_wholesale_price if p else 0,
            })

        return {
            "id": document_id,
            "order_number": doc.order_number if doc else "",
            "store_id": order.store_id,
            "store_name": stores.get(order.store_id, ""),
            "check_date": str(order.check_date),
            "status": order.status,
            "note": order.note,
            "created_at": str(order.created_at),
            "items": item_details,
        }

    def cancel(self, document_id: int):
        order = self.repo.get_by_id(document_id)
        if not order:
            raise ValueError("巡店记录不存在")
        if order.status == "cancelled":
            raise ValueError("该巡店记录已撤销")

        moves = self.stock_repo.get_by_source(document_id)
        for m in moves:
            self.db.delete(m)

        txns = self.txn_repo.get_by_source(document_id)
        for t in txns:
            self.db.delete(t)

        order.status = "cancelled"
        self.db.commit()
        return {"id": document_id, "status": "cancelled"}

    def import_preview(self, file_content: bytes) -> dict:
        prods = {p.name: p.id for p in self.db.query(Product).all()}
        stores = {s.name: s.id for s in self.db.query(Store).all()}

        def validate(row: dict) -> str | bool:
            pname = (row.get("产品名称") or row.get("product_name") or "").strip()
            if not pname:
                return "产品名称为空"
            if pname not in prods:
                return f"产品'{pname}'不存在"
            qty = row.get("实盘数量") or row.get("actual_quantity") or "0"
            try:
                int(float(qty))
            except ValueError:
                return "实盘数量格式错误"
            sname = (row.get("店铺名称") or row.get("store_name") or "").strip()
            if not sname:
                return "店铺名称为空"
            if sname not in stores:
                return f"店铺'{sname}'不存在"
            return True

        from app.services.csv_importer import parse_csv
        return parse_csv(file_content, validate, STORE_SALES_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        prods = {p.name: p.id for p in self.db.query(Product).all()}
        stores = {s.name: s.id for s in self.db.query(Store).all()}
        success = 0
        errors: list[dict] = []

        groups: dict[tuple, list[dict]] = {}
        for row in rows:
            data = row.get("data", row)
            sname = (data.get("店铺名称") or data.get("store_name") or "").strip()
            date_str = (data.get("日期") or data.get("date") or "").strip()
            key = (sname, date_str or str(date.today()))
            if key not in groups:
                groups[key] = []
            groups[key].append(data)

        for (sname, date_key), items in groups.items():
            sid = stores.get(sname)
            if not sid:
                continue

            doc = create_document(self.db, DocumentType.store_sales)
            order = StoreSalesOrder(
                document_id=doc.id,
                store_id=sid,
                check_date=_parse_date(date_key) if date_key else date.today(),
            )
            self.db.add(order)

            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                pid = prods.get(pname)
                if not pid:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                actual_qty = int(float(data.get("实盘数量") or data.get("actual_quantity") or 0))
                self.db.add(StoreSalesItem(
                    document_id=doc.id,
                    product_id=pid,
                    actual_quantity=actual_qty,
                ))
                success += 1

        self.db.commit()
        return {"success": success, "errors": errors}

    def export_csv(self):
        from app.models.document import Document
        products = {p.id: p.name for p in self.db.query(Product).all()}
        store_names = {s.id: s.name for s in self.db.query(Store).all()}

        rows = []
        items = (
            self.db.query(StoreSalesItem, Document, StoreSalesOrder)
            .join(Document, StoreSalesItem.document_id == Document.id)
            .join(StoreSalesOrder, StoreSalesItem.document_id == StoreSalesOrder.document_id)
            .order_by(Document.created_at.desc())
            .all()
        )

        for item, doc, order in items:
            p = products.get(item.product_id)
            rows.append({
                "单号": doc.order_number,
                "店铺": store_names.get(order.store_id, ""),
                "日期": str(order.check_date),
                "品名": p.name if p else "",
                "期末库存": item.actual_quantity,
                "推算销量": item.sales_quantity,
                "单价": 0,
                "收入": 0,
            })

        from app.services.import_helpers import make_csv_response
        return make_csv_response(rows, "store_sales_export.csv")
