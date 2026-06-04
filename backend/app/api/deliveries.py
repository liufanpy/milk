from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.delivery_service import DeliveryService
from app.schemas.delivery import DeliveryCreate, ExchangeCreate

router = APIRouter(prefix="/api/deliveries", tags=["deliveries"])


def get_delivery_service(db: Session = Depends(get_db)):
    return DeliveryService(db)


@router.post("", status_code=201)
def create_delivery(data: DeliveryCreate, svc: DeliveryService = Depends(get_delivery_service)):
    return svc.create_delivery(data)


@router.get("")
def list_deliveries(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    svc: DeliveryService = Depends(get_delivery_service),
):
    return svc.delivery_repo.list_all(customer_id, status)


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
