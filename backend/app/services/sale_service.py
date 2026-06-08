from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.retail_order_repo import RetailOrderRepository
from app.schemas.sale import SaleCreate
from app.models.retail_order import RetailOrder
from app.models.transaction import Transaction
from app.models.product import Product
from app.models.customer import Customer


class SaleService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.retail_repo = RetailOrderRepository(db)

    def _next_order_number(self) -> str:
        from app.services.order_number import next_order_number
        return next_order_number(self.db, RetailOrder, "RO")

    def create_sale(self, data: SaleCreate):
        self.stock_repo.validate_stock(data.items)

        retail_order = self.retail_repo.create(customer_id=data.customer_id)
        retail_order.order_number = self._next_order_number()

        total = 0.0
        movements = []
        for item in data.items:
            total += item.quantity * item.unit_price
            movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": "retail",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "retail_order_id": retail_order.id,
            })

        self.stock_repo.bulk_create(movements)

        # 收入
        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="retail",
                amount=total,
                retail_order_id=retail_order.id,
            )

        # cogs 成本
        product_ids = list({item.product_id for item in data.items})
        costs = {p.id: p.default_purchase_price for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()}
        for item in data.items:
            cost = costs.get(item.product_id, 0)
            if cost > 0:
                self.txn_repo.create(
                    customer_id=data.customer_id,
                    category="cogs",
                    amount=-(item.quantity * cost),
                    retail_order_id=retail_order.id,
                )

        # 已收款 → payment Transaction
        if data.paid and total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="payment",
                amount=total,
                retail_order_id=retail_order.id,
            )

        self.db.commit()
        return {"total": total, "item_count": len(data.items), "retail_order_id": retail_order.id}

    def list_sales(self):
        from app.models.stock_movement import StockMovement

        orders = self.db.query(RetailOrder).order_by(RetailOrder.created_at.desc()).all()
        if not orders:
            return []

        order_ids = [o.id for o in orders]
        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        products = {p.id: p.name for p in self.db.query(Product).all()}

        movements = (
            self.db.query(StockMovement)
            .filter(
                StockMovement.retail_order_id.in_(order_ids),
                StockMovement.reason == "retail",
            )
            .all()
        )

        paid_ids = {
            t.retail_order_id
            for t in self.db.query(Transaction).filter(
                Transaction.retail_order_id.in_(order_ids),
                Transaction.category == "payment",
            ).all()
        }

        order_items: dict[int, list] = {}
        order_totals: dict[int, float] = {}
        for m in movements:
            order_items.setdefault(m.retail_order_id, []).append(m)
            order_totals[m.retail_order_id] = order_totals.get(m.retail_order_id, 0) + m.quantity * m.unit_price

        result = []
        for o in orders:
            items = order_items.get(o.id, [])
            parts = []
            for m in items[:2]:
                pname = products.get(m.product_id, "")
                parts.append(f"{pname}×{m.quantity}")
            summary = "、".join(parts)
            if len(items) > 2:
                summary += f" 等{len(items)}件"

            result.append({
                "id": o.id,
                "order_number": o.order_number,
                "customer_id": o.customer_id,
                "customer_name": customers.get(o.customer_id, "散客") if o.customer_id else "散客",
                "item_count": len(items),
                "total_amount": order_totals.get(o.id, 0),
                "paid": o.id in paid_ids,
                "status": o.status,
                "items_summary": summary,
                "created_at": str(o.created_at),
            })

        return result

    def get_sale_detail(self, order_id: int):
        order = self.retail_repo.get_by_id(order_id)
        if not order:
            return None

        items = self.stock_repo.get_by_retail_order(order_id)
        products = {p.id: p.name for p in self.db.query(Product).all()}
        customers = {c.id: c.name for c in self.db.query(Customer).all()}

        paid = (
            self.db.query(Transaction).filter(
                Transaction.retail_order_id == order_id,
                Transaction.category == "payment",
            ).first()
            is not None
        )

        def item_dict(m):
            return {
                "product_id": m.product_id,
                "product_name": products.get(m.product_id, ""),
                "quantity": m.quantity,
                "unit_price": m.unit_price,
            }

        return {
            "id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "customer_name": customers.get(order.customer_id, "散客") if order.customer_id else "散客",
            "item_count": len(items),
            "total_amount": sum(m.quantity * m.unit_price for m in items),
            "paid": paid,
            "status": order.status,
            "items_summary": "",
            "items": [item_dict(m) for m in items],
            "created_at": str(order.created_at),
        }

    def mark_paid(self, order_id: int):
        order = self.retail_repo.get_by_id(order_id)
        if not order:
            raise ValueError("销售记录不存在")
        if order.status == "cancelled":
            raise ValueError("已撤销的销售无法收款")

        # 查是否已有 payment
        existing = (
            self.db.query(Transaction)
            .filter(
                Transaction.retail_order_id == order_id,
                Transaction.category == "payment",
            )
            .first()
        )
        if existing:
            return {"id": order.id, "paid": True}

        # 查收入金额
        income = (
            self.db.query(Transaction)
            .filter(
                Transaction.retail_order_id == order_id,
                Transaction.category == "retail",
            )
            .first()
        )
        if not income:
            raise ValueError("未找到收入记录")

        self.txn_repo.create(
            customer_id=order.customer_id,
            category="payment",
            amount=income.amount,
            retail_order_id=order_id,
        )
        self.db.commit()
        return {"id": order.id, "paid": True}

    def cancel_sale(self, order_id: int):
        order = self.retail_repo.get_by_id(order_id)
        if not order:
            raise ValueError("销售记录不存在")
        if order.status == "cancelled":
            raise ValueError("该销售已撤销")

        # 查原始出库记录
        original_items = self.stock_repo.get_by_retail_order(order_id)
        reverses = []
        for m in original_items:
            reverses.append({
                "product_id": m.product_id,
                "direction": "in",
                "reason": "cancel",
                "quantity": m.quantity,
                "unit_price": m.unit_price,
                "retail_order_id": order_id,
            })

        if reverses:
            self.stock_repo.bulk_create(reverses)

        # 反向冲抵账务
        original_txns = (
            self.db.query(Transaction)
            .filter(Transaction.retail_order_id == order_id)
            .all()
        )
        for t in original_txns:
            self.txn_repo.create(
                customer_id=order.customer_id,
                category=t.category,
                amount=-t.amount,
                retail_order_id=order_id,
            )

        self.retail_repo.update_status(order_id, "cancelled")
        self.db.commit()
        return {"id": order.id, "status": "cancelled"}
