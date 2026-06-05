from sqlalchemy.orm import Session
from app.repositories.subscription_order_repo import SubscriptionOrderRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.subscription import SubscriptionCreate, SubscriptionDeduct


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.sub_repo = SubscriptionOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_order(self, data: SubscriptionCreate):
        order = self.sub_repo.create(
            customer_id=data.customer_id,
            total_amount=data.total_amount,
            total_bottles=data.total_bottles,
            paid_bottles=data.paid_bottles,
            free_bottles=data.free_bottles,
            remaining_bottles=data.total_bottles,
            status="active",
        )
        self.txn_repo.create(
            customer_id=data.customer_id,
            category="subscription",
            amount=data.total_amount,
        )
        self.db.commit()
        return {"id": order.id, "remaining_bottles": order.remaining_bottles}

    def deduct(self, order_id: int, data: SubscriptionDeduct):
        order = self.sub_repo.get_by_id(order_id)
        if not order:
            raise ValueError("订奶单不存在")
        total_qty = sum(item.quantity for item in data.items)
        if order.remaining_bottles < total_qty:
            raise ValueError(f"瓶数不足，剩余 {order.remaining_bottles} 瓶")

        inventory = {
            (r.product_id, r.shelf_id): r.stock
            for r in self.stock_repo.get_inventory()
        }
        for item in data.items:
            stock = inventory.get((item.product_id, data.shelf_id), 0)
            if stock < item.quantity:
                raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {item.quantity}")

        movements = []
        for item in data.items:
            movements.append({
                "product_id": item.product_id,
                "shelf_id": data.shelf_id,
                "direction": "out",
                "reason": "sale",
                "quantity": item.quantity,
                "subscription_order_id": order_id,
            })

        self.stock_repo.bulk_create(movements)
        order.remaining_bottles -= total_qty
        if order.remaining_bottles <= 0:
            order.status = "completed"
        self.db.commit()
        return {"remaining_bottles": order.remaining_bottles}
