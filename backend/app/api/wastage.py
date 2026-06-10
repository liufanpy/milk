from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.wastage_service import WastageService
from app.schemas.wastage import WastageCreate

router = APIRouter(prefix="/api/wastage", tags=["wastage"])


def get_wastage_service(db: Session = Depends(get_db)):
    return WastageService(db)


@router.post("", status_code=201)
def create_wastage(data: WastageCreate, svc: WastageService = Depends(get_wastage_service)):
    try:
        return svc.create_wastage(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_wastage(svc: WastageService = Depends(get_wastage_service)):
    return svc.list_wastage()


@router.get("/export")
def export_wastage(svc: WastageService = Depends(get_wastage_service)):
    return svc.export_csv()


@router.post("/import")
async def import_wastage(file: UploadFile = File(...), svc: WastageService = Depends(get_wastage_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: WastageService = Depends(get_wastage_service)):
    return svc.import_confirm(data.get("rows", []))


@router.get("/{order_id}")
def get_wastage(order_id: int, svc: WastageService = Depends(get_wastage_service)):
    detail = svc.get_wastage_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="损耗单不存在")
    return detail


@router.post("/{order_id}/cancel")
def cancel_wastage(order_id: int, svc: WastageService = Depends(get_wastage_service)):
    try:
        return svc.cancel_wastage(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
