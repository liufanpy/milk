from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.wastage import WastageCreate
from app.models.product import Product


class WastageService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_wastage(self, data: WastageCreate):
        self.stock_repo.validate_stock(data.items)

        product_ids = list({item.product_id for item in data.items})
        costs = {p.id: p.default_purchase_price for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()}

        movements = []
        total_cost = 0.0
        for item in data.items:
            movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": "wastage",
                "quantity": item.quantity,
            })
            cost = costs.get(item.product_id, 0)
            total_cost += item.quantity * cost

        self.stock_repo.bulk_create(movements)

        if total_cost > 0:
            self.txn_repo.create(
                category="wastage",
                amount=-total_cost,
            )

        self.db.commit()
        return {"item_count": len(data.items), "total_cost": total_cost}
