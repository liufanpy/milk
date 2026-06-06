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
            paid_amount=data.paid_amount,
            remaining_amount=data.paid_amount,
            note=data.note,
            status="active",
        )
        if data.is_paid:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="payment",
                amount=data.paid_amount,
                subscription_order_id=order.id,
            )
        self.db.commit()
        return {
            "id": order.id,
            "paid_amount": order.paid_amount,
            "remaining_amount": order.remaining_amount,
            "status": order.status,
        }

    def _resolve_unit_price(self, customer_id: int, product_id: int, unit_price: float | None) -> float:
        """解析优先级：手动填入 > 客户专属价 > 等级价(批发价) > 默认零售价"""
        if unit_price is not None:
            return unit_price

        from app.models.product import Product
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return 0.0

        # 客户专属价
        from app.models.product_customer_price import ProductCustomerPrice
        custom = self.db.query(ProductCustomerPrice).filter(
            ProductCustomerPrice.customer_id == customer_id,
            ProductCustomerPrice.product_id == product_id,
        ).first()
        if custom:
            return custom.price

        # 等级价：批发客户用批发价
        from app.models.customer import Customer
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if customer and customer.price_tier == "批发":
            return product.default_wholesale_price

        # 默认零售价
        return product.default_retail_price

    def _get_purchase_cost(self, product_id: int) -> float:
        """获取产品进价（默认进货价）"""
        from app.models.product import Product
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if product:
            return product.default_purchase_price
        return 0.0

    def deduct(self, order_id: int, data: SubscriptionDeduct):
        order = self.sub_repo.get_by_id(order_id)
        if not order:
            raise ValueError("订奶单不存在")
        if order.status != "active":
            raise ValueError("订奶单非活跃状态")

        # 计算付费行合计并校验金额
        paid_total = 0.0
        items_for_validate = []
        for item in data.items:
            if not item.is_promo:
                price = self._resolve_unit_price(order.customer_id, item.product_id, item.unit_price)
                paid_total += item.quantity * price
            items_for_validate.append({"product_id": item.product_id, "quantity": item.quantity})

        if paid_total > order.remaining_amount:
            raise ValueError(f"超出余额，剩余 ¥{order.remaining_amount:.2f}，本次扣减 ¥{paid_total:.2f}")

        self.stock_repo.validate_stock(items_for_validate)

        for item in data.items:
            unit_price = 0.0 if item.is_promo else self._resolve_unit_price(order.customer_id, item.product_id, item.unit_price)
            purchase_cost = self._get_purchase_cost(item.product_id)
            total_price = item.quantity * unit_price
            total_cost = item.quantity * purchase_cost

            # StockMovement - 定奶出库
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "direction": "out",
                "reason": "subscription",
                "quantity": item.quantity,
                "unit_price": unit_price,
                "subscription_order_id": order_id,
            }])

            if item.is_promo:
                # 赠送行：记促销成本
                if total_cost > 0:
                    self.txn_repo.create(
                        customer_id=order.customer_id,
                        category="promo",
                        amount=-total_cost,
                        subscription_order_id=order_id,
                    )
            else:
                # 付费行：收入确认 + 成本
                self.txn_repo.create(
                    customer_id=order.customer_id,
                    category="subscription",
                    amount=total_price,
                    subscription_order_id=order_id,
                )
                if total_cost > 0:
                    self.txn_repo.create(
                        customer_id=order.customer_id,
                        category="cogs",
                        amount=-total_cost,
                        subscription_order_id=order_id,
                    )

        # 更新余额
        order.remaining_amount -= paid_total
        if order.remaining_amount <= 0:
            order.status = "completed"

        self.db.commit()
        return {
            "remaining_amount": order.remaining_amount,
            "status": order.status,
            "deducted": paid_total,
        }
