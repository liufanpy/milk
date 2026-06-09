from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.inventory_check_service import InventoryCheckService
from app.schemas.inventory_check import InventoryCheckCreate

router = APIRouter(prefix="/api/inventory-checks", tags=["inventory-checks"])


def get_service(db: Session = Depends(get_db)):
    return InventoryCheckService(db)


@router.post("", status_code=201)
def create_check(data: InventoryCheckCreate, svc: InventoryCheckService = Depends(get_service)):
    try:
        return svc.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_checks(
    store_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    svc: InventoryCheckService = Depends(get_service),
):
    return svc.list_checks(store_id, date_from, date_to)


@router.get("/{check_id}")
def get_check(check_id: int, svc: InventoryCheckService = Depends(get_service)):
    detail = svc.get_detail(check_id)
    if not detail:
        raise HTTPException(status_code=404, detail="盘点单不存在")
    return detail


@router.post("/{check_id}/cancel")
def cancel_check(check_id: int, svc: InventoryCheckService = Depends(get_service)):
    try:
        return svc.cancel(check_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
