from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.inventory_check_service import InventoryCheckService

router = APIRouter(prefix="/api/inventory-checks", tags=["inventory-checks"])


class SaveItemsBody(BaseModel):
    items: list[dict]


@router.post("")
def create_inventory_check(
    check_date: str | None = Query(None),
    note: str = Query(""),
    db: Session = Depends(get_db),
):
    svc = InventoryCheckService(db)
    d = date.fromisoformat(check_date) if check_date else None
    return svc.create(check_date=d, note=note)


@router.get("")
def list_inventory_checks(db: Session = Depends(get_db)):
    svc = InventoryCheckService(db)
    return svc.list_checks()


@router.get("/{document_id}")
def get_inventory_check(document_id: int, db: Session = Depends(get_db)):
    svc = InventoryCheckService(db)
    result = svc.get_detail(document_id)
    if not result:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "盘点单不存在"}, status_code=404)
    return result


@router.put("/{document_id}/items")
def save_inventory_check_items(
    document_id: int,
    body: SaveItemsBody,
    db: Session = Depends(get_db),
):
    svc = InventoryCheckService(db)
    return svc.save_items(document_id, body.items)


@router.post("/{document_id}/confirm")
def confirm_inventory_check(document_id: int, db: Session = Depends(get_db)):
    svc = InventoryCheckService(db)
    return svc.confirm(document_id)
