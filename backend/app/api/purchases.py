import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.purchase_service import PurchaseService
from app.schemas.purchase import PurchaseCreate, PurchaseConfirm
from app.models.purchase_order import PurchaseOrder
from app.models.supplier import Supplier

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


def get_purchase_service(db: Session = Depends(get_db)):
    return PurchaseService(db)


# ── 进货单 CRUD ───────────────────────────────────

@router.post("", status_code=201)
def create_purchase(data: PurchaseCreate, svc: PurchaseService = Depends(get_purchase_service)):
    return svc.create_purchase(data)


@router.get("")
def list_purchases(svc: PurchaseService = Depends(get_purchase_service)):
    return svc.list_purchases()


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


# ── CSV 导出（基于 purchase_orders） ──────────────

@router.get("/export")
def export_purchases(db: Session = Depends(get_db)):
    orders = db.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).all()
    suppliers = {s.id: s.name for s in db.query(Supplier).all()}
    csv_lines = ["单号,供应商,日期,金额,状态,备注"]
    for o in orders:
        sname = suppliers.get(o.supplier_id, "")
        csv_lines.append(f"{o.order_number},{sname},{o.purchase_date},{o.total_amount},{o.status},{o.note or ''}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=purchases.csv"})


# ── CSV 导入（不变） ──────────────────────────────

@router.post("/import")
async def import_purchases(file: UploadFile = File(...), svc: PurchaseService = Depends(get_purchase_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: PurchaseService = Depends(get_purchase_service)):
    return svc.import_confirm(data.get("rows", []))
