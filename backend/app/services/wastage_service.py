from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.schemas.wastage import WastageCreate


class WastageService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)

    def create_wastage(self, data: WastageCreate):
        inventory = {
            (r.product_id, r.shelf_id): r.stock
            for r in self.stock_repo.get_inventory()
        }
        for item in data.items:
            stock = inventory.get((item.product_id, item.shelf_id), 0)
            if stock < item.quantity:
                raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {item.quantity}")

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
