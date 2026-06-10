from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.store_sales_service import StoreSalesService
from app.schemas.store_sales import StoreSalesCreate

router = APIRouter(prefix="/api/store-sales", tags=["store-sales"])


def get_service(db: Session = Depends(get_db)):
    return StoreSalesService(db)


@router.post("", status_code=201)
def create_store_sales(data: StoreSalesCreate, svc: StoreSalesService = Depends(get_service)):
    try:
        return svc.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_store_sales(
    store_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    svc: StoreSalesService = Depends(get_service),
):
    return svc.list_checks(store_id, date_from, date_to)


@router.get("/export")
def export_store_sales(svc: StoreSalesService = Depends(get_service)):
    return svc.export_csv()


@router.post("/import")
async def import_store_sales(file: UploadFile = File(...), svc: StoreSalesService = Depends(get_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: StoreSalesService = Depends(get_service)):
    return svc.import_confirm(data.get("rows", []))


@router.get("/{document_id}")
def get_store_sales(document_id: int, svc: StoreSalesService = Depends(get_service)):
    detail = svc.get_detail(document_id)
    if not detail:
        raise HTTPException(status_code=404, detail="巡店记录不存在")
    return detail


@router.post("/{document_id}/cancel")
def cancel_store_sales(document_id: int, svc: StoreSalesService = Depends(get_service)):
    try:
        return svc.cancel(document_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
