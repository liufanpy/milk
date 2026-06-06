import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.wastage_service import WastageService
from app.schemas.wastage import WastageCreate
from app.models.stock_movement import StockMovement
from app.models.product import Product

router = APIRouter(prefix="/api/wastage", tags=["wastage"])


def get_wastage_service(db: Session = Depends(get_db)):
    return WastageService(db)


@router.post("", status_code=201)
def create_wastage(data: WastageCreate, svc: WastageService = Depends(get_wastage_service)):
    try:
        return svc.create_wastage(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_wastage(db: Session = Depends(get_db)):
    return db.query(StockMovement).filter(StockMovement.reason == "wastage").order_by(
        StockMovement.created_at.desc()
    ).limit(100).all()


@router.get("/export")
def export_wastage(db: Session = Depends(get_db)):
    rows = db.query(StockMovement).filter(StockMovement.reason == "wastage").order_by(StockMovement.created_at.desc()).all()
    products = {p.id: p.name for p in db.query(Product).all()}
    csv_lines = ["产品名称,数量,时间"]
    for r in rows:
        pname = products.get(r.product_id, str(r.product_id))
        csv_lines.append(f"{pname},{r.quantity},{r.created_at}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=wastage.csv"})
