from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.subscription_service import SubscriptionService
from app.schemas.subscription import SubscriptionCreate, SubscriptionDeduct

router = APIRouter(prefix="/api/subscription-orders", tags=["subscriptions"])


def get_subscription_service(db: Session = Depends(get_db)):
    return SubscriptionService(db)


@router.post("", status_code=201)
def create_order(data: SubscriptionCreate, svc: SubscriptionService = Depends(get_subscription_service)):
    return svc.create_order(data)


@router.post("/{order_id}/deduct")
def deduct(order_id: int, data: SubscriptionDeduct, svc: SubscriptionService = Depends(get_subscription_service)):
    try:
        return svc.deduct(order_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_orders(svc: SubscriptionService = Depends(get_subscription_service)):
    return svc.sub_repo.list_all()
