from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.purchase import PurchaseCreate


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_purchase(self, data: PurchaseCreate):
        total = 0.0
        movements = []
        for item in data.items:
            total += item.quantity * item.unit_cost
            movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "in",
                "reason": "purchase",
                "quantity": item.quantity,
                "unit_cost": item.unit_cost,
            })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                supplier_id=data.supplier_id,
                category="purchase",
                amount=total,
            )

        self.db.commit()
        return {"total": total, "item_count": len(data.items)}

    def list_purchases(self):
        return self.stock_repo.list_all()
