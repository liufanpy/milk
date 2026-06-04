from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.stock_movement_repo import StockMovementRepository

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("")
def get_inventory(db: Session = Depends(get_db)):
    repo = StockMovementRepository(db)
    rows = repo.get_inventory()
    return [
        {"product_id": r.product_id, "shelf_id": r.shelf_id, "stock": r.stock}
        for r in rows if r.stock != 0
    ]
