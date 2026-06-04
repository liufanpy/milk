from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.settlement_service import SettlementService
from app.schemas.settlement import SettlementCreate, BatchSettlement

router = APIRouter(prefix="/api/deliveries", tags=["settlements"])


def get_settlement_service(db: Session = Depends(get_db)):
    return SettlementService(db)


@router.post("/{delivery_id}/settle")
def settle_delivery(delivery_id: int, data: SettlementCreate, svc: SettlementService = Depends(get_settlement_service)):
    try:
        return svc.settle(delivery_id, data.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
def batch_settle(data: BatchSettlement, svc: SettlementService = Depends(get_settlement_service)):
    try:
        return svc.batch_settle(data.customer_id, [it.model_dump() for it in data.items])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
