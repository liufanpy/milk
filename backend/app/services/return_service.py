from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.return_schema import ReturnCreate


class ReturnService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_return(self, data: ReturnCreate):
        refund_total = 0.0
        for item in data.items:
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "in",
                "reason": "return",
                "quantity": item.quantity,
                "delivery_id": data.delivery_id,
            }])
            if item.is_wasted:
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "shelf_id": item.shelf_id,
                    "direction": "out",
                    "reason": "wastage",
                    "quantity": item.quantity,
                }])
            refund_total += item.quantity * item.unit_price

        if refund_total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="refund",
                amount=refund_total,
                delivery_id=data.delivery_id,
            )

        self.db.commit()
        return {"refund_total": refund_total}
