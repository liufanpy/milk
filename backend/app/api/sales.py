from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.sale_service import SaleService
from app.schemas.sale import SaleCreate

router = APIRouter(prefix="/api/sales", tags=["sales"])


def get_sale_service(db: Session = Depends(get_db)):
    return SaleService(db)


@router.post("", status_code=201)
def create_sale(data: SaleCreate, svc: SaleService = Depends(get_sale_service)):
    return svc.create_sale(data)


@router.get("")
def list_sales(svc: SaleService = Depends(get_sale_service)):
    return svc.list_sales()
