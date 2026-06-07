from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.return_service import ReturnService
from app.schemas.return_schema import ReturnCreate

router = APIRouter(prefix="/api/returns", tags=["returns"])


def get_return_service(db: Session = Depends(get_db)):
    return ReturnService(db)


@router.post("", status_code=201)
def create_return(data: ReturnCreate, svc: ReturnService = Depends(get_return_service)):
    return svc.create_return(data)


@router.get("")
def list_returns(svc: ReturnService = Depends(get_return_service)):
    return svc.list_returns()


@router.get("/{order_id}")
def get_return(order_id: int, svc: ReturnService = Depends(get_return_service)):
    detail = svc.get_return_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="退货单不存在")
    return detail


@router.post("/{order_id}/cancel")
def cancel_return(order_id: int, svc: ReturnService = Depends(get_return_service)):
    try:
        return svc.cancel_return(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
