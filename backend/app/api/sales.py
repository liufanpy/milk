import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.sale_service import SaleService
from app.schemas.sale import SaleCreate
from app.models.retail_order import RetailOrder
from app.models.customer import Customer

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


# ── CSV 导出（必须在 /{order_id} 之前注册，否则路径段被当作 order_id） ──

@router.get("/export")
def export_sales(db: Session = Depends(get_db)):
    orders = db.query(RetailOrder).order_by(RetailOrder.created_at.desc()).all()
    customers = {c.id: c.name for c in db.query(Customer).all()}
    csv_lines = ["客户名称,金额,状态,时间"]
    for o in orders:
        cname = (customers.get(o.customer_id, "散客") if o.customer_id else "散客")
        csv_lines.append(f"{cname},,{o.status},{o.created_at}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales.csv"},
    )


# ── 销售单详情（动态路径放在静态路径之后） ─────

@router.get("/{order_id}")
def get_sale(order_id: int, svc: SaleService = Depends(get_sale_service)):
    detail = svc.get_sale_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="销售记录不存在")
    return detail


@router.post("/{order_id}/cancel")
def cancel_sale(order_id: int, svc: SaleService = Depends(get_sale_service)):
    try:
        return svc.cancel_sale(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
