from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.purchase_service import PurchaseService
from app.schemas.purchase import PurchaseCreate

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


def get_purchase_service(db: Session = Depends(get_db)):
    return PurchaseService(db)


@router.post("", status_code=201)
def create_purchase(data: PurchaseCreate, svc: PurchaseService = Depends(get_purchase_service)):
    return svc.create_purchase(data)


@router.get("")
def list_purchases(svc: PurchaseService = Depends(get_purchase_service)):
    return svc.list_purchases()
