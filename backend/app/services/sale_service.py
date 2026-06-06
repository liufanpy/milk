from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.retail_order_repo import RetailOrderRepository
from app.schemas.sale import SaleCreate
from app.models.transaction import Transaction
from app.models.product import Product


class SaleService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.retail_repo = RetailOrderRepository(db)

    def create_sale(self, data: SaleCreate):
        self.stock_repo.validate_stock(data.items)

        retail_order = self.retail_repo.create(customer_id=data.customer_id)

        total = 0.0
        movements = []
        for item in data.items:
            unit_price = 0.0 if item.is_promo else item.unit_price
            amount = item.quantity * unit_price
            if not item.is_promo:
                total += amount
            movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": "retail",
                "quantity": item.quantity,
                "unit_price": unit_price,
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

        # cogs + promo 成本
        product_ids = list({item.product_id for item in data.items})
        costs = {p.id: p.default_purchase_price for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()}
        for item in data.items:
            cost = costs.get(item.product_id, 0)
            if cost > 0:
                category = "promo" if item.is_promo else "cogs"
                self.txn_repo.create(
                    customer_id=data.customer_id,
                    category=category,
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
        return self.db.query(Transaction).filter(
            Transaction.category.in_(["retail", "sale"])
        ).order_by(Transaction.created_at.desc()).all()
