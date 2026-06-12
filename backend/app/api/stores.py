from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.store_service import StoreService
from app.schemas.store import StoreCreate, StoreUpdate

router = APIRouter(prefix="/api/stores", tags=["stores"])


def get_store_service(db: Session = Depends(get_db)):
    return StoreService(db)


@router.get("")
def list_stores(svc: StoreService = Depends(get_store_service)):
    return svc.list_stores()


@router.post("", status_code=201)
def create_store(data: StoreCreate, svc: StoreService = Depends(get_store_service)):
    try:
        return svc.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export")
def export_stores(svc: StoreService = Depends(get_store_service)):
    return svc.export_csv()


@router.post("/import")
async def import_stores(file: UploadFile = File(...), svc: StoreService = Depends(get_store_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: StoreService = Depends(get_store_service)):
    return svc.import_confirm(data.get("rows", []))


@router.get("/{store_id}")
def get_store(store_id: int, svc: StoreService = Depends(get_store_service)):
    detail = svc.get_store(store_id)
    if not detail:
        raise HTTPException(status_code=404, detail="店铺不存在")
    return detail


@router.put("/{store_id}")
def update_store(store_id: int, data: StoreUpdate, svc: StoreService = Depends(get_store_service)):
    try:
        return svc.update(store_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{store_id}")
def delete_store(store_id: int, svc: StoreService = Depends(get_store_service)):
    try:
        return svc.delete(store_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
