from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.subscription_service import SubscriptionService
from app.schemas.subscription import SubscriptionCreate, SubscriptionDeduct
from app.repositories.stock_movement_repo import StockMovementRepository
from app.models.stock_movement import StockMovement

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


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    from app.repositories.subscription_order_repo import SubscriptionOrderRepository
    sub_repo = SubscriptionOrderRepository(db)
    order = sub_repo.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订奶单不存在")

    stock_repo = StockMovementRepository(db)
    movements = stock_repo.get_by_source("subscription", order_id)

    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "paid_amount": order.paid_amount,
        "remaining_amount": order.remaining_amount,
        "note": order.note,
        "status": order.status,
        "created_at": str(order.created_at),
        "deductions": [
            {
                "id": m.id,
                "product_id": m.product_id,
                "quantity": m.quantity,
                "unit_price": m.unit_price,
                "created_at": str(m.created_at),
            }
            for m in movements
        ],
    }
