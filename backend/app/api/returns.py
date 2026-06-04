from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.return_service import ReturnService
from app.schemas.return_schema import ReturnCreate
from app.models.stock_movement import StockMovement

router = APIRouter(prefix="/api/returns", tags=["returns"])


def get_return_service(db: Session = Depends(get_db)):
    return ReturnService(db)


@router.post("", status_code=201)
def create_return(data: ReturnCreate, svc: ReturnService = Depends(get_return_service)):
    return svc.create_return(data)


@router.get("")
def list_returns(db: Session = Depends(get_db)):
    return db.query(StockMovement).filter(StockMovement.reason == "return").order_by(
        StockMovement.created_at.desc()
    ).limit(100).all()
