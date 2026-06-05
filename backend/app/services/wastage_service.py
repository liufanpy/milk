from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.schemas.wastage import WastageCreate


class WastageService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)

    def create_wastage(self, data: WastageCreate):
        self.stock_repo.validate_stock(data.items)

        movements = []
        for item in data.items:
            movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "out",
                "reason": "wastage",
                "quantity": item.quantity,
            })
        self.stock_repo.bulk_create(movements)
        self.db.commit()
        return {"item_count": len(data.items)}
