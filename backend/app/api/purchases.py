import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.purchase_service import PurchaseService
from app.schemas.purchase import PurchaseCreate
from app.models.stock_movement import StockMovement

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


def get_purchase_service(db: Session = Depends(get_db)):
    return PurchaseService(db)


@router.post("", status_code=201)
def create_purchase(data: PurchaseCreate, svc: PurchaseService = Depends(get_purchase_service)):
    return svc.create_purchase(data)


@router.get("")
def list_purchases(svc: PurchaseService = Depends(get_purchase_service)):
    return svc.list_purchases()


@router.get("/export")
def export_purchases(db: Session = Depends(get_db)):
    rows = db.query(StockMovement).filter(StockMovement.reason == "purchase").order_by(StockMovement.created_at.desc()).all()
    csv_lines = ["ID,产品ID,货架ID,数量,进价,时间"]
    for r in rows:
        csv_lines.append(f"{r.id},{r.product_id},{r.shelf_id},{r.quantity},{r.unit_cost},{r.created_at}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=purchases.csv"})
