from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.subscription_service import SubscriptionService
from app.schemas.subscription import SubscriptionCreate, SubscriptionDeduct
from app.models.subscription_item import SubscriptionItem
from app.models.document import Document

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
    orders = svc.sub_repo.list_all()
    doc_ids = [o.document_id for o in orders]
    docs = {d.id: d for d in svc.db.query(Document).filter(Document.id.in_(doc_ids)).all()}
    return [
        {
            "id": o.document_id,
            "order_number": docs[o.document_id].order_number if o.document_id in docs else "",
            "customer_id": o.customer_id,
            "paid_amount": o.paid_amount,
            "remaining_amount": o.remaining_amount,
            "status": o.status,
            "note": o.note,
            "created_at": str(o.created_at),
        }
        for o in orders
    ]


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    from app.repositories.subscription_order_repo import SubscriptionOrderRepository
    sub_repo = SubscriptionOrderRepository(db)
    order = sub_repo.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订奶单不存在")

    doc = db.query(Document).filter(Document.id == order_id).first()
    items = db.query(SubscriptionItem).filter(SubscriptionItem.document_id == order_id).all()

    return {
        "id": order_id,
        "order_number": doc.order_number if doc else "",
        "customer_id": order.customer_id,
        "paid_amount": order.paid_amount,
        "remaining_amount": order.remaining_amount,
        "note": order.note,
        "status": order.status,
        "created_at": str(order.created_at),
        "deductions": [
            {
                "id": it.id,
                "product_id": it.product_id,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "is_promo": it.is_promo,
                "created_at": str(it.created_at) if it.created_at else "",
            }
            for it in items
        ],
    }
