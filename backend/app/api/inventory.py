import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.stock_movement_repo import StockMovementRepository
from app.models.product import Product

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("")
def get_inventory(db: Session = Depends(get_db)):
    repo = StockMovementRepository(db)
    rows = repo.get_inventory()
    return [
        {"product_id": r.product_id, "stock": r.stock}
        for r in rows if r.stock != 0
    ]


@router.get("/export")
def export_inventory(db: Session = Depends(get_db)):
    repo = StockMovementRepository(db)
    rows = repo.get_inventory()
    products = {p.id: p.name for p in db.query(Product).all()}
    csv_lines = ["产品名称,库存"]
    for r in rows:
        if r.stock != 0:
            pname = products.get(r.product_id, str(r.product_id))
            csv_lines.append(f"{pname},{r.stock}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=inventory.csv"})
