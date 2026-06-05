from datetime import datetime
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

    def list_with_amounts(self, customer_id=None, status=None):
        deliveries = self.delivery_repo.list_all(customer_id, status)
        if not deliveries:
            return []
        ids = [d.id for d in deliveries]
        amounts = self.txn_repo.get_amounts_by_deliveries(ids)
        return [
            {
                "id": d.id,
                "customer_id": d.customer_id,
                "delivery_date": str(d.delivery_date),
                "status": d.status,
                "note": d.note,
                "subscription_order_id": d.subscription_order_id,
                "created_at": str(d.created_at) if d.created_at else None,
                "total_amount": amounts[d.id]["total_amount"],
                "paid_amount": amounts[d.id]["paid_amount"],
                "unpaid_amount": amounts[d.id]["unpaid_amount"],
            }
            for d in deliveries
        ]

    def create_delivery(self, data: DeliveryCreate):
        self.stock_repo.validate_stock(data.items)

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
                "unit_price": item.unit_price,
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

        # 换货记录：按 created_at 分组
        exchange_movements = [m for m in movements if m.reason == "exchange"]
        groups: dict = {}
        for m in exchange_movements:
            groups.setdefault(m.created_at, []).append(m)
        exchanges = [
            {
                "created_at": str(ts),
                "return_items": [
                    {"product_id": m.product_id, "quantity": m.quantity, "unit_price": m.unit_price}
                    for m in ms if m.direction == "in"
                ],
                "new_items": [
                    {"product_id": m.product_id, "quantity": m.quantity, "unit_price": m.unit_price}
                    for m in ms if m.direction == "out"
                ],
            }
            for ts, ms in groups.items()
        ]

        return {
            "id": delivery.id,
            "customer_id": delivery.customer_id,
            "delivery_date": str(delivery.delivery_date),
            "status": delivery.status,
            "note": delivery.note,
            "items": [{"product_id": m.product_id, "quantity": m.quantity, "reason": m.reason, "direction": m.direction} for m in movements if m.reason != "exchange"],
            "total_amount": net,
            "paid_amount": paid_total,
            "unpaid_amount": net - paid_total,
            "transactions": [{"id": t.id, "category": t.category, "amount": t.amount, "created_at": str(t.created_at)} for t in transactions],
            "exchanges": exchanges,
        }

    def exchange(self, delivery_id: int, data: ExchangeCreate):
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            raise ValueError("送货单不存在")

        return_total = sum(item.quantity * item.unit_price for item in data.return_items)
        new_total = sum(item.quantity * item.unit_price for item in data.new_items)

        if abs(return_total - new_total) > 0.005:
            raise ValueError("换货金额不一致，请走退货结算后重新开单")

        now = datetime.now()

        # 退回入库（先 flush 让库存对后续校验可见）
        return_movements = []
        for item in data.return_items:
            return_movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "in",
                "reason": "exchange",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "delivery_id": delivery_id,
                "created_at": now,
            })
        self.stock_repo.bulk_create(return_movements)

        # 新发出库（带库存校验，此时退回库存已可见）
        self.stock_repo.validate_stock(data.new_items)
        new_movements = []
        for item in data.new_items:
            new_movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "out",
                "reason": "exchange",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "delivery_id": delivery_id,
                "created_at": now,
            })
        self.stock_repo.bulk_create(new_movements)

        self.db.commit()
        return {"return_total": return_total, "new_total": new_total}
