from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.delivery_repo import DeliveryRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.store_repo import StoreRepository
from app.models.delivery import Delivery
from app.schemas.delivery import DeliveryCreate, ExchangeCreate


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.delivery_repo = DeliveryRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.store_repo = StoreRepository(db)

    def _next_order_number(self) -> str:
        from app.services.order_number import next_order_number
        return next_order_number(self.db, Delivery, "DO")

    def list_with_amounts(self, customer_id=None, status=None):
        deliveries = self.delivery_repo.list_all(customer_id, status)
        if not deliveries:
            return []
        ids = [d.id for d in deliveries]
        amounts = self.txn_repo.get_amounts_by_deliveries(ids)
        return [
            {
                "id": d.id,
                "order_number": d.order_number,
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

        # 查客户关联的店铺
        store = self.store_repo.get_by_customer(data.customer_id)

        delivery = self.delivery_repo.create(
            customer_id=data.customer_id,
            delivery_date=data.delivery_date,
            status="pending",
            subscription_order_id=data.subscription_order_id,
            store_id=store.id if store else None,
            note=data.note,
        )
        delivery.order_number = self._next_order_number()

        total = 0.0
        movements = []
        for item in data.items:
            total += item.quantity * item.unit_price
            movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": "distribution",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "source_type": "delivery",
                "source_id": delivery.id,
            })

        # 若客户有店铺，多记一条店铺入库
        if store:
            for item in data.items:
                movements.append({
                    "product_id": item.product_id,
                    "direction": "in",
                    "reason": "store_receive",
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "source_type": "delivery",
                    "source_id": delivery.id,
                    "store_id": store.id,
                    "customer_id": data.customer_id,
                })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="distribution",
                amount=total,
                source_type="delivery",
                source_id=delivery.id,
            )

        delivery.status = "delivered"
        self.db.commit()
        return {"id": delivery.id, "total": total}

    def get_delivery_detail(self, delivery_id: int):
        from app.models.product import Product

        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            return None
        movements = self.stock_repo.get_by_source("delivery", delivery_id)
        transactions = self.txn_repo.get_by_source("delivery", delivery_id)
        products = {p.id: p.name for p in self.db.query(Product).all()}

        delivery_total = sum(t.amount for t in transactions if t.category in ("distribution", "delivery"))
        delivery_cancel_total = sum(t.amount for t in transactions if t.category == "delivery_cancel")
        paid_total = sum(t.amount for t in transactions if t.category == "payment")

        net = delivery_total + delivery_cancel_total

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
            "order_number": delivery.order_number,
            "customer_id": delivery.customer_id,
            "delivery_date": str(delivery.delivery_date),
            "status": delivery.status,
            "note": delivery.note,
            "items": [
                {
                    "product_id": m.product_id,
                    "product_name": products.get(m.product_id, ""),
                    "quantity": m.quantity,
                    "unit_price": m.unit_price or 0,
                }
                for m in movements if m.reason != "exchange"
            ],
            "total_amount": net,
            "paid_amount": paid_total,
            "unpaid_amount": net - paid_total,
            "transactions": [
                {"id": t.id, "category": t.category, "amount": t.amount, "created_at": str(t.created_at)}
                for t in transactions
            ],
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
        store_id = delivery.store_id

        return_movements = []
        for item in data.return_items:
            mov = {
                "product_id": item.product_id,
                "direction": "in",
                "reason": "exchange",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "source_type": "delivery",
                "source_id": delivery_id,
                "created_at": now,
            }
            if store_id:
                return_movements.append({**mov})  # 总仓
                return_movements.append({**mov, "direction": "out", "store_id": store_id})  # 店铺
            else:
                return_movements.append(mov)
        self.stock_repo.bulk_create(return_movements)

        self.stock_repo.validate_stock(data.new_items)
        new_movements = []
        for item in data.new_items:
            mov = {
                "product_id": item.product_id,
                "direction": "out",
                "reason": "exchange",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "source_type": "delivery",
                "source_id": delivery_id,
                "created_at": now,
            }
            if store_id:
                new_movements.append({**mov})  # 总仓
                new_movements.append({**mov, "direction": "in", "store_id": store_id})  # 店铺
            else:
                new_movements.append(mov)
        self.stock_repo.bulk_create(new_movements)

        self.db.commit()
        return {"return_total": return_total, "new_total": new_total}
