from datetime import datetime, date
from sqlalchemy.orm import Session
from app.repositories.distribution_repo import DistributionOrderRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.store_repo import StoreRepository
from app.services.document_helpers import create_document
from app.models.distribution_order import DistributionOrder
from app.models.distribution_order_item import DistributionOrderItem
from app.schemas.distribution import DistributionCreate, ExchangeCreate
from app.enums import DocumentType, Direction, TransactionCategory

DISTRIBUTION_HEADERS = ["产品名称", "product_name", "数量", "quantity", "售价", "unit_price", "客户名称", "customer_name", "店铺名称", "store_name", "日期", "date"]

DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]


def _parse_date(s: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


class DistributionService:
    def __init__(self, db: Session):
        self.db = db
        self.dist_repo = DistributionOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.store_repo = StoreRepository(db)

    # ── 列表 ──

    def list_with_amounts(self, customer_id=None, status=None):
        orders = self.dist_repo.list_all(customer_id, status)
        if not orders:
            return []
        ids = [d.document_id for d in orders]
        amounts = self.txn_repo.get_amounts_by_distribution(ids)

        from app.models.document import Document
        docs = {d.id: d for d in self.db.query(Document).filter(Document.id.in_(ids)).all()}

        return [
            {
                "id": d.document_id,
                "order_number": docs[d.document_id].order_number if d.document_id in docs else "",
                "customer_id": d.customer_id,
                "delivery_date": str(d.delivery_date),
                "status": d.status,
                "note": d.note,
                "subscription_order_id": d.subscription_order_id,
                "created_at": str(d.created_at) if d.created_at else None,
                "total_amount": amounts[d.document_id]["total_amount"],
                "paid_amount": amounts[d.document_id]["paid_amount"],
                "unpaid_amount": amounts[d.document_id]["unpaid_amount"],
            }
            for d in orders
        ]

    # ── 创建铺货单 ──

    def create_distribution(self, data: DistributionCreate):
        self.stock_repo.validate_stock(data.items)
        store = self.store_repo.get_by_customer(data.customer_id)

        doc = create_document(self.db, DocumentType.distribution)
        order = DistributionOrder(
            document_id=doc.id,
            customer_id=data.customer_id,
            delivery_date=data.delivery_date,
            status="pending",
            subscription_order_id=data.subscription_order_id,
            store_id=store.id if store else None,
            note=data.note,
        )
        self.db.add(order)

        total = 0.0
        movements = []
        for item in data.items:
            total += item.quantity * item.unit_price
            self.db.add(DistributionOrderItem(
                document_id=doc.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            ))
            # 总仓出库
            movements.append({
                "product_id": item.product_id,
                "direction": Direction.out,
                "quantity": item.quantity,
                "source_type": DocumentType.distribution,
                "source_id": doc.id,
            })
            # 店铺入库
            if store:
                movements.append({
                    "product_id": item.product_id,
                    "direction": Direction.in_,
                    "quantity": item.quantity,
                    "source_type": DocumentType.distribution,
                    "source_id": doc.id,
                    "store_id": store.id,
                })

        self.db.flush()
        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category=TransactionCategory.distribution,
                amount=total,
                source_type=DocumentType.distribution,
                source_id=doc.id,
            )

        order.status = "delivered"
        self.db.commit()
        return {"id": doc.id, "total": total}

    # ── 详情 ──

    def get_detail(self, document_id: int):
        from app.models.product import Product
        from app.models.document import Document

        order = self.dist_repo.get_by_id(document_id)
        if not order:
            return None

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        items = self.db.query(DistributionOrderItem).filter(
            DistributionOrderItem.document_id == document_id,
            DistributionOrderItem.type.is_(None),
        ).all()
        transactions = self.txn_repo.get_by_source(document_id)
        products = {p.id: p.name for p in self.db.query(Product).all()}

        dist_total = sum(t.amount for t in transactions if t.category == TransactionCategory.distribution)
        paid_total = sum(t.amount for t in transactions if t.category == TransactionCategory.payment)

        # 换货记录
        exchange_items = self.db.query(DistributionOrderItem).filter(
            DistributionOrderItem.document_id == document_id,
            DistributionOrderItem.type.isnot(None),
        ).all()

        from app.enums import DistributionItemType
        exchanges = []
        if exchange_items:
            returns = [it for it in exchange_items if it.type == DistributionItemType.exchange_return]
            news = [it for it in exchange_items if it.type == DistributionItemType.exchange_new]
            exchanges.append({
                "return_items": [
                    {"product_id": it.product_id, "product_name": products.get(it.product_id, ""),
                     "quantity": it.quantity, "unit_price": it.unit_price}
                    for it in returns
                ],
                "new_items": [
                    {"product_id": it.product_id, "product_name": products.get(it.product_id, ""),
                     "quantity": it.quantity, "unit_price": it.unit_price}
                    for it in news
                ],
            })

        return {
            "id": document_id,
            "order_number": doc.order_number if doc else "",
            "customer_id": order.customer_id,
            "delivery_date": str(order.delivery_date),
            "status": order.status,
            "note": order.note,
            "items": [
                {
                    "product_id": it.product_id,
                    "product_name": products.get(it.product_id, ""),
                    "quantity": it.quantity,
                    "unit_price": it.unit_price,
                }
                for it in items
            ],
            "total_amount": dist_total,
            "paid_amount": paid_total,
            "unpaid_amount": dist_total - paid_total,
            "transactions": [
                {"id": t.id, "category": t.category.value if hasattr(t.category, 'value') else t.category,
                 "amount": t.amount, "created_at": str(t.created_at)}
                for t in transactions
            ],
            "exchanges": exchanges,
        }

    # ── 换货 ──

    def exchange(self, document_id: int, data: ExchangeCreate):
        from app.enums import DistributionItemType

        order = self.dist_repo.get_by_id(document_id)
        if not order:
            raise ValueError("铺货单不存在")

        return_total = sum(item.quantity * item.unit_price for item in data.return_items)
        new_total = sum(item.quantity * item.unit_price for item in data.new_items)

        if abs(return_total - new_total) > 0.005:
            raise ValueError("换货金额不一致，请走退货结算后重新开单")

        store_id = order.store_id

        # 记录换货 items
        for item in data.return_items:
            self.db.add(DistributionOrderItem(
                document_id=document_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                type=DistributionItemType.exchange_return,
            ))
        for item in data.new_items:
            self.db.add(DistributionOrderItem(
                document_id=document_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                type=DistributionItemType.exchange_new,
            ))

        # 反向 movements（退货回仓）
        return_movements = []
        for item in data.return_items:
            mov = {
                "product_id": item.product_id,
                "direction": Direction.in_,
                "quantity": item.quantity,
                "source_type": DocumentType.distribution,
                "source_id": document_id,
            }
            return_movements.append(mov)
            if store_id:
                return_movements.append({**mov, "direction": Direction.out, "store_id": store_id})
        self.stock_repo.bulk_create(return_movements)

        # 新品出库
        self.stock_repo.validate_stock(data.new_items)
        new_movements = []
        for item in data.new_items:
            mov = {
                "product_id": item.product_id,
                "direction": Direction.out,
                "quantity": item.quantity,
                "source_type": DocumentType.distribution,
                "source_id": document_id,
            }
            new_movements.append(mov)
            if store_id:
                new_movements.append({**mov, "direction": Direction.in_, "store_id": store_id})
        self.stock_repo.bulk_create(new_movements)

        self.db.commit()
        return {"return_total": return_total, "new_total": new_total}

    # ── 结算 ──

    def settle(self, document_id: int, amount: float):
        order = self.dist_repo.get_by_id(document_id)
        if not order:
            raise ValueError("铺货单不存在")

        self.txn_repo.create(
            customer_id=order.customer_id,
            category=TransactionCategory.payment,
            amount=amount,
            source_type=DocumentType.distribution,
            source_id=document_id,
        )

        amounts = self.txn_repo.get_amounts_by_distribution([document_id])
        info = amounts.get(document_id, {})
        if info.get("unpaid_amount", 0) <= 0:
            order.status = "settled"

        self.db.commit()
        return {"id": document_id, "paid": amount}

    def batch_settle(self, customer_id: int, items: list[dict]):
        doc_ids = [item["id"] for item in items]
        for item in items:
            order = self.dist_repo.get_by_id(item["id"])
            if not order:
                raise ValueError(f"铺货单 #{item['id']} 不存在")
            if order.customer_id != customer_id:
                raise ValueError(f"铺货单 #{item['id']} 不属于该客户")
            self.txn_repo.create(
                customer_id=customer_id,
                category=TransactionCategory.payment,
                amount=item["amount"],
                source_type=DocumentType.distribution,
                source_id=item["id"],
            )

        amounts = self.txn_repo.get_amounts_by_distribution(doc_ids)
        for did in doc_ids:
            info = amounts.get(did, {})
            if info.get("unpaid_amount", 0) <= 0:
                order = self.dist_repo.get_by_id(did)
                if order:
                    order.status = "settled"

        self.db.commit()
        return {"results": [{"id": item["id"], "paid": item["amount"]} for item in items]}

    # ── CSV 导入 ──

    def _name_maps(self):
        from app.models.product import Product
        from app.models.customer import Customer
        prods = {p.name: (p.id, p.retail_price) for p in self.db.query(Product).all()}
        customers = {c.name: c.id for c in self.db.query(Customer).all()}
        stores = {s.name: s for s in self.db.query(self._store_model()).all()}
        return prods, customers, stores

    def _store_model(self):
        from app.models.store import Store
        return Store

    def import_preview(self, file_content: bytes) -> dict:
        prods, customers, stores = self._name_maps()

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
        return parse_csv(file_content, validate, DISTRIBUTION_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        from app.models.product import Product
        from app.models.customer import Customer
        prods = {p.name: (p.id, p.retail_price) for p in self.db.query(Product).all()}
        customers = {c.name: c.id for c in self.db.query(Customer).all()}
        stores = {s.name: s for s in self.db.query(self._store_model()).all()}

        success = 0
        errors: list[dict] = []

        groups: dict[tuple, list[dict]] = {}
        for row in rows:
            data = row.get("data", row)
            cname = (data.get("客户名称") or data.get("customer_name") or "").strip()
            date_str = (data.get("日期") or data.get("date") or "").strip()
            key = (cname, date_str or str(date.today()))
            if key not in groups:
                groups[key] = []
            groups[key].append(data)

        for (cname, date_key), items in groups.items():
            cid = customers.get(cname)
            if not cid:
                continue

            store = self.store_repo.get_by_customer(cid)
            doc = create_document(self.db, DocumentType.distribution)
            order = DistributionOrder(
                document_id=doc.id,
                customer_id=cid,
                delivery_date=_parse_date(date_key) if date_key else date.today(),
                status="delivered",
                store_id=store.id if store else None,
            )
            self.db.add(order)

            total = 0.0
            movements = []
            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                p = prods.get(pname)
                if not p:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                pid, default_price = p
                qty = int(float(data.get("数量") or data.get("quantity") or 0))
                price = data.get("售价") or data.get("unit_price") or ""
                price = float(price) if price else default_price
                total += qty * price

                self.db.add(DistributionOrderItem(
                    document_id=doc.id,
                    product_id=pid,
                    quantity=qty,
                    unit_price=price,
                ))
                movements.append({
                    "product_id": pid,
                    "direction": Direction.out,
                    "quantity": qty,
                    "source_type": DocumentType.distribution,
                    "source_id": doc.id,
                })
                if store:
                    movements.append({
                        "product_id": pid,
                        "direction": Direction.in_,
                        "quantity": qty,
                        "source_type": DocumentType.distribution,
                        "source_id": doc.id,
                        "store_id": store.id,
                    })

            self.db.flush()

            if movements:
                self.stock_repo.bulk_create(movements)
                if total > 0:
                    self.txn_repo.create(
                        customer_id=cid,
                        category=TransactionCategory.distribution,
                        amount=total,
                        source_type=DocumentType.distribution,
                        source_id=doc.id,
                    )
                success += len([m for m in movements if m["direction"] == Direction.out])

        self.db.commit()
        return {"success": success, "errors": errors}

    def export_csv(self):
        from app.models.document import Document
        from app.models.product import Product
        from app.models.customer import Customer
        products = {p.id: p.name for p in self.db.query(Product).all()}
        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        stores = {s.id: s.name for s in self.db.query(self._store_model()).all()}

        items = (
            self.db.query(DistributionOrderItem, Document, DistributionOrder)
            .join(Document, DistributionOrderItem.document_id == Document.id)
            .join(DistributionOrder, DistributionOrderItem.document_id == DistributionOrder.document_id)
            .filter(DistributionOrderItem.type.is_(None))
            .order_by(Document.created_at.desc())
            .all()
        )

        rows = []
        for item, doc, order in items:
            rows.append({
                "单号": doc.order_number,
                "客户": customers.get(order.customer_id, ""),
                "店铺": stores.get(order.store_id, ""),
                "日期": str(order.created_at.date()) if order.created_at else "",
                "品名": products.get(item.product_id, ""),
                "数量": item.quantity,
                "售价": item.unit_price,
                "折扣": item.discount,
                "实收": round(item.quantity * item.unit_price - item.discount, 2),
                "付款状态": "已结算" if order.status == "settled" else "未结算",
            })

        from app.services.import_helpers import make_csv_response
        return make_csv_response(rows, "distribution_export.csv")
