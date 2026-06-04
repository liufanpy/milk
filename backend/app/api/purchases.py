import io
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.purchase_service import PurchaseService
from app.schemas.purchase import PurchaseCreate
from app.models.stock_movement import StockMovement
from app.models.product import Product
from app.models.shelf import Shelf

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
    products = {p.id: p.name for p in db.query(Product).all()}
    shelves = {s.id: s.name for s in db.query(Shelf).all()}
    csv_lines = ["产品名称,货架名称,数量,进价,日期"]
    for r in rows:
        pname = products.get(r.product_id, str(r.product_id))
        sname = shelves.get(r.shelf_id, str(r.shelf_id))
        date_str = str(r.created_at)[:10] if r.created_at else ""
        csv_lines.append(f"{pname},{sname},{r.quantity},{r.unit_cost},{date_str}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=purchases.csv"})


@router.post("/import")
async def import_purchases(file: UploadFile = File(...), svc: PurchaseService = Depends(get_purchase_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: PurchaseService = Depends(get_purchase_service)):
    return svc.import_confirm(data.get("rows", []))
