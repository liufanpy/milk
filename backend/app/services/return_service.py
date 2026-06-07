from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.return_order_repo import ReturnOrderRepository
from app.schemas.return_schema import ReturnCreate
from app.models.return_order import ReturnOrder
from app.models.transaction import Transaction
from app.models.product import Product
from app.models.customer import Customer


class ReturnService:
    def __init__(self, db: Session):
        self.db = db
        self.return_repo = ReturnOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_return(self, data: ReturnCreate):
        order = self.return_repo.create(
            customer_id=data.customer_id,
            source_type=data.source_type,
            source_order_id=data.source_order_id,
            note=data.note,
        )

        refund_total = 0.0
        for item in data.items:
            # 退货入库
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "direction": "in",
                "reason": "return",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "return_order_id": order.id,
            }])
            # 如果产品已报废，额外做一条出库
            if item.is_wasted:
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "direction": "out",
                    "reason": "wastage",
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "return_order_id": order.id,
                }])
            refund_total += item.quantity * item.unit_price

        # 退款
        if refund_total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="refund",
                amount=refund_total,
                return_order_id=order.id,
            )

        self.db.commit()
        return {"id": order.id, "refund_total": refund_total}

    def list_returns(self):
        from app.models.stock_movement import StockMovement

        orders = self.return_repo.list_all()
        if not orders:
            return []

        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        products = {p.id: p.name for p in self.db.query(Product).all()}

        order_ids = [o.id for o in orders]
        movements = (
            self.db.query(StockMovement)
            .filter(
                StockMovement.return_order_id.in_(order_ids),
                StockMovement.reason == "return",
            )
            .all()
        )
        refunds = {
            t.return_order_id: t.amount
            for t in self.db.query(Transaction).filter(
                Transaction.return_order_id.in_(order_ids),
                Transaction.category == "refund",
            ).all()
        }

        order_items: dict[int, list] = {}
        for m in movements:
            order_items.setdefault(m.return_order_id, []).append(m)

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
                "customer_id": o.customer_id,
                "customer_name": customers.get(o.customer_id, ""),
                "source_type": o.source_type,
                "source_order_id": o.source_order_id,
                "item_count": len(items),
                "total_refund": refunds.get(o.id, 0),
                "note": o.note,
                "status": o.status,
                "items_summary": summary,
                "created_at": str(o.created_at),
            })

        return result

    def get_return_detail(self, order_id: int):
        order = self.return_repo.get_by_id(order_id)
        if not order:
            return None

        items = self.stock_repo.get_by_return_order(order_id)
        products = {p.id: p.name for p in self.db.query(Product).all()}
        customers = {c.id: c.name for c in self.db.query(Customer).all()}

        refunds = (
            self.db.query(Transaction)
            .filter(
                Transaction.return_order_id == order_id,
                Transaction.category == "refund",
            ).all()
        )
        total_refund = sum(t.amount for t in refunds)

        def item_dict(m):
            return {
                "product_id": m.product_id,
                "product_name": products.get(m.product_id, ""),
                "quantity": m.quantity,
                "unit_price": m.unit_price or 0,
            }

        return {
            "id": order.id,
            "customer_id": order.customer_id,
            "customer_name": customers.get(order.customer_id, ""),
            "source_type": order.source_type,
            "source_order_id": order.source_order_id,
            "item_count": len(items),
            "total_refund": total_refund,
            "note": order.note,
            "status": order.status,
            "items": [item_dict(m) for m in items if m.direction == "in" and m.reason == "return"],
            "transactions": [
                {"id": t.id, "category": t.category, "amount": t.amount, "created_at": str(t.created_at)}
                for t in refunds
            ],
            "created_at": str(order.created_at),
        }

    def cancel_return(self, order_id: int):
        order = self.return_repo.get_by_id(order_id)
        if not order:
            raise ValueError("退货单不存在")
        if order.status == "cancelled":
            raise ValueError("该退货单已撤销")

        # 查原始记录
        original_items = self.stock_repo.get_by_return_order(order_id)
        for m in original_items:
            # 反向冲抵库存
            reverse_dir = "out" if m.direction == "in" else "in"
            self.stock_repo.bulk_create([{
                "product_id": m.product_id,
                "direction": reverse_dir,
                "reason": "cancel",
                "quantity": m.quantity,
                "unit_price": m.unit_price or 0,
                "return_order_id": order_id,
            }])

        # 反向冲抵账务
        original_txns = (
            self.db.query(Transaction)
            .filter(Transaction.return_order_id == order_id)
            .all()
        )
        for t in original_txns:
            self.txn_repo.create(
                customer_id=order.customer_id,
                category=t.category,
                amount=-t.amount,
                return_order_id=order_id,
            )

        self.return_repo.update_status(order_id, "cancelled")
        self.db.commit()
        return {"id": order.id, "status": "cancelled"}
