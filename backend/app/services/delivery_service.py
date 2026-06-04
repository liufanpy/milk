from sqlalchemy.orm import Session
from app.repositories.delivery_repo import DeliveryRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.delivery import DeliveryCreate, ExchangeCreate


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.delivery_repo = DeliveryRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_delivery(self, data: DeliveryCreate):
        # 库存校验
        inventory = {
            (r.product_id, r.shelf_id): r.stock
            for r in self.stock_repo.get_inventory()
        }
        for item in data.items:
            stock = inventory.get((item.product_id, item.shelf_id), 0)
            if stock < item.quantity:
                raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {item.quantity}")

        delivery = self.delivery_repo.create(
            customer_id=data.customer_id,
            delivery_date=data.delivery_date,
            status="pending",
            subscription_order_id=data.subscription_order_id,
            note=data.note,
        )

        total = 0.0
        movements = []
        for item in data.items:
            amount = item.quantity * item.unit_price
            total += amount
            movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "out",
                "reason": "delivery",
                "quantity": item.quantity,
                "unit_cost": 0.0,
                "delivery_id": delivery.id,
            })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="delivery",
                amount=total,
                delivery_id=delivery.id,
            )

        delivery.status = "delivered"
        self.db.commit()
        return {"id": delivery.id, "total": total}

    def get_delivery_detail(self, delivery_id: int):
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            return None
        movements = self.stock_repo.get_by_delivery(delivery_id)
        transactions = self.txn_repo.get_by_delivery(delivery_id)

        delivery_total = sum(t.amount for t in transactions if t.category == "delivery")
        delivery_cancel_total = sum(t.amount for t in transactions if t.category == "delivery_cancel")
        paid_total = sum(t.amount for t in transactions if t.category == "payment")

        net = delivery_total + delivery_cancel_total

        return {
            "id": delivery.id,
            "customer_id": delivery.customer_id,
            "delivery_date": str(delivery.delivery_date),
            "status": delivery.status,
            "note": delivery.note,
            "items": [{"product_id": m.product_id, "quantity": m.quantity, "reason": m.reason, "direction": m.direction} for m in movements],
            "total_amount": net,
            "paid_amount": paid_total,
            "unpaid_amount": net - paid_total,
            "transactions": [{"id": t.id, "category": t.category, "amount": t.amount, "created_at": str(t.created_at)} for t in transactions],
        }

    def exchange(self, delivery_id: int, data: ExchangeCreate):
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            raise ValueError("送货单不存在")

        # 计算旧 delivery 净额（当前应收）
        old_transactions = self.txn_repo.get_by_delivery(delivery_id)
        old_total = sum(t.amount for t in old_transactions if t.category == "delivery") + \
                    sum(t.amount for t in old_transactions if t.category == "delivery_cancel")

        # return_items: 退货回库，stock_movement(reason=return)
        return_total = 0.0
        for item in data.return_items:
            amt = item.quantity * item.unit_price
            return_total += amt
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "in",
                "reason": "return",
                "quantity": item.quantity,
                "delivery_id": delivery_id,
            }])

        # new_items: 出货，stock_movement(reason=delivery)，带库存校验
        inventory = {
            (r.product_id, r.shelf_id): r.stock
            for r in self.stock_repo.get_inventory()
        }
        new_total = 0.0
        for item in data.new_items:
            stock = inventory.get((item.product_id, item.shelf_id), 0)
            if stock < item.quantity:
                raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {item.quantity}")
            amt = item.quantity * item.unit_price
            new_total += amt
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "out",
                "reason": "delivery",
                "quantity": item.quantity,
                "delivery_id": delivery_id,
            }])

        # transaction: 冲抵旧的 delivery + 新建新的 delivery
        if old_total != 0:
            self.txn_repo.create(
                customer_id=delivery.customer_id,
                category="delivery_cancel",
                amount=-old_total,
                delivery_id=delivery_id,
            )
        if new_total > 0:
            self.txn_repo.create(
                customer_id=delivery.customer_id,
                category="delivery",
                amount=new_total,
                delivery_id=delivery_id,
            )

        # 更新 delivery.total_amount
        delivery.total_amount = new_total

        self.db.commit()
        return {"return_total": return_total, "new_total": new_total}
