import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.wastage_service import WastageService
from app.schemas.wastage import WastageCreate
from app.models.stock_movement import StockMovement

router = APIRouter(prefix="/api/wastage", tags=["wastage"])


def get_wastage_service(db: Session = Depends(get_db)):
    return WastageService(db)


@router.post("", status_code=201)
def create_wastage(data: WastageCreate, svc: WastageService = Depends(get_wastage_service)):
    return svc.create_wastage(data)


@router.get("")
def list_wastage(db: Session = Depends(get_db)):
    return db.query(StockMovement).filter(StockMovement.reason == "wastage").order_by(
        StockMovement.created_at.desc()
    ).limit(100).all()


@router.get("/export")
def export_wastage(db: Session = Depends(get_db)):
    rows = db.query(StockMovement).filter(StockMovement.reason == "wastage").order_by(StockMovement.created_at.desc()).all()
    csv_lines = ["ID,产品ID,货架ID,数量,时间"]
    for r in rows:
        csv_lines.append(f"{r.id},{r.product_id},{r.shelf_id},{r.quantity},{r.created_at}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=wastage.csv"})
