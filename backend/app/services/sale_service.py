from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.sale import SaleCreate
from app.models.transaction import Transaction


class SaleService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_sale(self, data: SaleCreate):
        inventory = {
            (r.product_id, r.shelf_id): r.stock
            for r in self.stock_repo.get_inventory()
        }
        for item in data.items:
            stock = inventory.get((item.product_id, item.shelf_id), 0)
            if stock < item.quantity:
                raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {item.quantity}")

        total = 0.0
        movements = []
        for item in data.items:
            amount = item.quantity * item.unit_price
            total += amount
            movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "out",
                "reason": "sale",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="sale",
                amount=total,
            )

        self.db.commit()
        return {"total": total, "item_count": len(data.items)}

    def list_sales(self):
        return self.db.query(Transaction).filter(
            Transaction.category == "sale"
        ).order_by(Transaction.created_at.desc()).all()
