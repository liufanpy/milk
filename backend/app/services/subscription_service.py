from sqlalchemy.orm import Session
from app.repositories.subscription_order_repo import SubscriptionOrderRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.services.document_helpers import create_document
from app.models.subscription_order import SubscriptionOrder
from app.models.subscription_item import SubscriptionItem
from app.schemas.subscription import SubscriptionCreate, SubscriptionDeduct
from app.enums import DocumentType, Direction, TransactionCategory


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.sub_repo = SubscriptionOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_order(self, data: SubscriptionCreate):
        doc = create_document(self.db, DocumentType.subscription)
        order = SubscriptionOrder(
            document_id=doc.id,
            customer_id=data.customer_id,
            paid_amount=data.paid_amount,
            remaining_amount=data.paid_amount,
            note=data.note,
            status="active",
        )
        self.db.add(order)

        if data.is_paid:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category=TransactionCategory.subscription,
                amount=data.paid_amount,
                source_type=DocumentType.subscription,
                source_id=doc.id,
            )
        self.db.commit()
        return {
            "id": doc.id,
            "paid_amount": order.paid_amount,
            "remaining_amount": order.remaining_amount,
            "status": order.status,
        }

    def _resolve_unit_price(self, customer_id: int, product_id: int, unit_price: float | None) -> float:
        if unit_price is not None:
            return unit_price

        from app.models.product import Product
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return 0.0

        from app.models.product_customer_price import ProductCustomerPrice
        custom = self.db.query(ProductCustomerPrice).filter(
            ProductCustomerPrice.customer_id == customer_id,
            ProductCustomerPrice.product_id == product_id,
        ).first()
        if custom:
            return custom.price

        from app.models.customer import Customer
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if customer and customer.price_tier == "批发":
            return product.default_wholesale_price

        return product.retail_price

    def _get_purchase_cost(self, product_id: int) -> float:
        from app.models.product import Product
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if product:
            return product.default_purchase_price
        return 0.0

    def deduct(self, document_id: int, data: SubscriptionDeduct):
        order = self.sub_repo.get_by_id(document_id)
        if not order:
            raise ValueError("订奶单不存在")
        if order.status != "active":
            raise ValueError("订奶单非活跃状态")

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

            self.db.add(SubscriptionItem(
                document_id=document_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=unit_price,
                is_promo=item.is_promo,
            ))

            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "direction": Direction.out,
                "quantity": item.quantity,
                "source_type": DocumentType.subscription,
                "source_id": document_id,
            }])

            if item.is_promo:
                purchase_cost = self._get_purchase_cost(item.product_id)
                total_cost = item.quantity * purchase_cost
                if total_cost > 0:
                    self.txn_repo.create(
                        customer_id=order.customer_id,
                        category=TransactionCategory.promo,
                        amount=-total_cost,
                        source_type=DocumentType.subscription,
                        source_id=document_id,
                    )
            else:
                total_price = item.quantity * unit_price
                self.txn_repo.create(
                    customer_id=order.customer_id,
                    category=TransactionCategory.subscription,
                    amount=total_price,
                    source_type=DocumentType.subscription,
                    source_id=document_id,
                )

        order.remaining_amount -= paid_total
        if order.remaining_amount <= 0:
            order.status = "completed"

        self.db.commit()
        return {
            "remaining_amount": order.remaining_amount,
            "status": order.status,
            "deducted": paid_total,
        }
