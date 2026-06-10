from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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


@router.get("/export")
def export_returns(svc: ReturnService = Depends(get_return_service)):
    return svc.export_csv()


@router.post("/import")
async def import_returns(file: UploadFile = File(...), svc: ReturnService = Depends(get_return_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: ReturnService = Depends(get_return_service)):
    return svc.import_confirm(data.get("rows", []))


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
