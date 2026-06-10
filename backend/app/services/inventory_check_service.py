from datetime import datetime, date
from sqlalchemy.orm import Session
from app.models.inventory_check import InventoryCheck, InventoryCheckItem
from app.models.stock_movement import StockMovement
from app.models.product import Product
from app.models.store import Store
from app.models.product_customer_price import ProductCustomerPrice
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.inventory_check import InventoryCheckCreate


class InventoryCheckService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def _next_order_number(self) -> str:
        from app.services.order_number import next_order_number
        return next_order_number(self.db, InventoryCheck, "IC")

    def _resolve_sale_price(self, customer_id: int, product: Product) -> float:
        """客户协议价 > 产品批发价"""
        custom = self.db.query(ProductCustomerPrice).filter(
            ProductCustomerPrice.customer_id == customer_id,
            ProductCustomerPrice.product_id == product.id,
        ).first()
        if custom:
            return custom.price
        return product.default_wholesale_price

    def _get_last_check_quantity(self, store_id: int, product_id: int, before_date: date) -> int:
        """最近一次盘点该产品的实盘数"""
        last = (
            self.db.query(InventoryCheckItem.actual_quantity)
            .join(InventoryCheck)
            .filter(
                InventoryCheck.store_id == store_id,
                InventoryCheck.check_date < before_date,
                InventoryCheck.status == "confirmed",
                InventoryCheckItem.product_id == product_id,
            )
            .order_by(InventoryCheck.check_date.desc())
            .first()
        )
        return last[0] if last else 0

    def _get_last_check_date(self, store_id: int, before_date: date) -> date | None:
        """最近一次盘点日期"""
        last = (
            self.db.query(InventoryCheck.check_date)
            .filter(
                InventoryCheck.store_id == store_id,
                InventoryCheck.check_date < before_date,
                InventoryCheck.status == "confirmed",
            )
            .order_by(InventoryCheck.check_date.desc())
            .first()
        )
        return last[0] if last else None

    def create(self, data: InventoryCheckCreate):
        store = self.db.query(Store).filter(Store.id == data.store_id).first()
        if not store:
            raise ValueError("店铺不存在")

        check = InventoryCheck(
            order_number=self._next_order_number(),
            store_id=data.store_id,
            check_date=data.check_date,
            note=data.note,
        )
        self.db.add(check)
        self.db.flush()

        products = {p.id: p for p in self.db.query(Product).all()}

        # 上次盘点日期（用于计算期间收货的起点）
        last_check_date = self._get_last_check_date(data.store_id, data.check_date)
        from_dt = datetime.combine(last_check_date, datetime.min.time()) if last_check_date else datetime.min
        to_dt = datetime.combine(data.check_date, datetime.min.time())

        for item in data.items:
            # 保存盘点明细
            detail = InventoryCheckItem(
                check_id=check.id,
                product_id=item.product_id,
                actual_quantity=item.actual_quantity,
            )
            self.db.add(detail)

            # 计算销量
            beginning = self._get_last_check_quantity(data.store_id, item.product_id, data.check_date)
            received = self.stock_repo.get_store_receive_between(
                data.store_id, item.product_id, from_dt, to_dt
            )
            ending = item.actual_quantity
            sales_qty = beginning + received - ending

            product = products.get(item.product_id)
            if not product:
                continue

            if sales_qty > 0:
                # 库存变动
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "direction": "out",
                    "reason": "inventory_check",
                    "quantity": sales_qty,
                    "source_type": "inventory_check",
                    "source_id": check.id,
                    "store_id": data.store_id,
                }])

                # 收入
                sale_price = self._resolve_sale_price(store.customer_id or 0, product)
                revenue = sales_qty * sale_price
                self.txn_repo.create(
                    customer_id=store.customer_id,
                    category="inventory_check",
                    amount=revenue,
                    source_type="inventory_check",
                    source_id=check.id,
                    store_id=data.store_id,
                )

            elif sales_qty < 0:
                # 盘盈
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "direction": "in",
                    "reason": "inventory_check",
                    "quantity": -sales_qty,
                    "source_type": "inventory_check",
                    "source_id": check.id,
                    "store_id": data.store_id,
                }])

        self.db.commit()
        return {"id": check.id, "order_number": check.order_number}

    def list_checks(self, store_id: int | None = None, date_from: str | None = None, date_to: str | None = None):
        from app.models.store import Store as StoreModel
        q = self.db.query(InventoryCheck).order_by(InventoryCheck.check_date.desc())
        if store_id:
            q = q.filter(InventoryCheck.store_id == store_id)
        if date_from:
            q = q.filter(InventoryCheck.check_date >= date.fromisoformat(date_from))
        if date_to:
            q = q.filter(InventoryCheck.check_date < date.fromisoformat(date_to))
        checks = q.all()
        stores = {s.id: s.name for s in self.db.query(StoreModel).all()}
        return [
            {
                "id": c.id,
                "order_number": c.order_number,
                "store_id": c.store_id,
                "store_name": stores.get(c.store_id, ""),
                "check_date": str(c.check_date),
                "status": c.status,
                "item_count": self.db.query(InventoryCheckItem).filter(
                    InventoryCheckItem.check_id == c.id
                ).count(),
                "note": c.note,
                "created_at": str(c.created_at),
            }
            for c in checks
        ]

    def get_detail(self, check_id: int):
        check = self.db.query(InventoryCheck).filter(InventoryCheck.id == check_id).first()
        if not check:
            return None
        stores = {s.id: s.name for s in self.db.query(Store).all()}
        products = {p.id: p for p in self.db.query(Product).all()}
        items = self.db.query(InventoryCheckItem).filter(InventoryCheckItem.check_id == check_id).all()
        stock_moves = self.stock_repo.get_by_source("inventory_check", check_id)
        txns = self.txn_repo.get_by_source("inventory_check", check_id)

        item_details = []
        for item in items:
            p = products.get(item.product_id)
            out_move = next((m for m in stock_moves if m.product_id == item.product_id and m.direction == "out"), None)
            in_move = next((m for m in stock_moves if m.product_id == item.product_id and m.direction == "in"), None)
            sales_qty = out_move.quantity if out_move else (in_move.quantity if in_move else 0)
            item_details.append({
                "product_id": item.product_id,
                "product_name": p.name if p else "",
                "actual_quantity": item.actual_quantity,
                "sales_quantity": sales_qty if out_move else (-in_move.quantity if in_move else 0),
                "unit_price": p.default_wholesale_price if p else 0,
            })

        return {
            "id": check.id,
            "order_number": check.order_number,
            "store_id": check.store_id,
            "store_name": stores.get(check.store_id, ""),
            "check_date": str(check.check_date),
            "status": check.status,
            "note": check.note,
            "created_at": str(check.created_at),
            "items": item_details,
            "transactions": [
                {"id": t.id, "category": t.category, "amount": t.amount, "created_at": str(t.created_at)}
                for t in txns
            ],
        }

    def cancel(self, check_id: int):
        check = self.db.query(InventoryCheck).filter(InventoryCheck.id == check_id).first()
        if not check:
            raise ValueError("盘点单不存在")
        if check.status == "cancelled":
            raise ValueError("该盘点单已撤销")

        # 删库存流水
        moves = self.stock_repo.get_by_source("inventory_check", check_id)
        for m in moves:
            self.db.delete(m)

        # 删资金流水
        txns = self.txn_repo.get_by_source("inventory_check", check_id)
        for t in txns:
            self.db.delete(t)

        check.status = "cancelled"
        self.db.commit()
        return {"id": check.id, "status": "cancelled"}
