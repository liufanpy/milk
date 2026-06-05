import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.delivery_service import DeliveryService
from app.schemas.delivery import DeliveryCreate, ExchangeCreate
from app.models.delivery import Delivery
from app.models.customer import Customer

router = APIRouter(prefix="/api/deliveries", tags=["deliveries"])


def get_delivery_service(db: Session = Depends(get_db)):
    return DeliveryService(db)


@router.post("", status_code=201)
def create_delivery(data: DeliveryCreate, svc: DeliveryService = Depends(get_delivery_service)):
    try:
        return svc.create_delivery(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_deliveries(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    svc: DeliveryService = Depends(get_delivery_service),
):
    return svc.list_with_amounts(customer_id, status)


@router.get("/export")
def export_deliveries(db: Session = Depends(get_db)):
    rows = db.query(Delivery).order_by(Delivery.delivery_date.desc()).all()
    customers = {c.id: c.name for c in db.query(Customer).all()}
    csv_lines = ["客户名称,日期,状态,备注"]
    for r in rows:
        cname = customers.get(r.customer_id, str(r.customer_id))
        csv_lines.append(f"{cname},{r.delivery_date},{r.status},{r.note or ''}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=deliveries.csv"})


@router.get("/{delivery_id}")
def get_delivery(delivery_id: int, svc: DeliveryService = Depends(get_delivery_service)):
    detail = svc.get_delivery_detail(delivery_id)
    if not detail:
        raise HTTPException(status_code=404, detail="送货单不存在")
    return detail


@router.post("/{delivery_id}/exchange")
def exchange(delivery_id: int, data: ExchangeCreate, svc: DeliveryService = Depends(get_delivery_service)):
    try:
        return svc.exchange(delivery_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
