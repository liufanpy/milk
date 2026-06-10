from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.purchase_service import PurchaseService
from app.schemas.purchase import PurchaseCreate, PurchaseConfirm

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
def export_purchases(svc: PurchaseService = Depends(get_purchase_service)):
    from app.services.import_helpers import make_csv_response
    orders = svc.list_purchases()
    if not orders:
        return make_csv_response([], "purchases.csv")
    rows = [
        {"单号": o["order_number"], "供应商": o["supplier_name"], "日期": o["purchase_date"],
         "金额": o["total_amount"], "状态": o["status"], "备注": o.get("note", "")}
        for o in orders
    ]
    return make_csv_response(rows, "purchases.csv")


@router.post("/import")
async def import_purchases(file: UploadFile = File(...), svc: PurchaseService = Depends(get_purchase_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: PurchaseService = Depends(get_purchase_service)):
    return svc.import_confirm(data.get("rows", []))


@router.get("/{order_id}")
def get_purchase(order_id: int, svc: PurchaseService = Depends(get_purchase_service)):
    detail = svc.get_purchase_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="进货单不存在")
    return detail


@router.post("/{order_id}/confirm")
def confirm_purchase(order_id: int, data: PurchaseConfirm = PurchaseConfirm(), svc: PurchaseService = Depends(get_purchase_service)):
    try:
        return svc.confirm_order(order_id, [it.model_dump() for it in data.items] if data.items else None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel")
def cancel_purchase(order_id: int, svc: PurchaseService = Depends(get_purchase_service)):
    try:
        return svc.cancel_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
