from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.sale_service import SaleService
from app.schemas.sale import SaleCreate

router = APIRouter(prefix="/api/sales", tags=["sales"])


def get_sale_service(db: Session = Depends(get_db)):
    return SaleService(db)


@router.post("", status_code=201)
def create_sale(data: SaleCreate, svc: SaleService = Depends(get_sale_service)):
    try:
        return svc.create_sale(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_sales(svc: SaleService = Depends(get_sale_service)):
    return svc.list_sales()


@router.get("/export")
def export_sales(svc: SaleService = Depends(get_sale_service)):
    return svc.export_csv()


@router.post("/import")
async def import_sales(file: UploadFile = File(...), svc: SaleService = Depends(get_sale_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: SaleService = Depends(get_sale_service)):
    return svc.import_confirm(data.get("rows", []))


@router.get("/{order_id}")
def get_sale(order_id: int, svc: SaleService = Depends(get_sale_service)):
    detail = svc.get_sale_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="销售记录不存在")
    return detail


@router.post("/{order_id}/pay")
def mark_paid(order_id: int, svc: SaleService = Depends(get_sale_service)):
    try:
        return svc.mark_paid(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel")
def cancel_sale(order_id: int, svc: SaleService = Depends(get_sale_service)):
    try:
        return svc.cancel_sale(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
