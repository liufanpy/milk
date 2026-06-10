from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.distribution_service import DistributionService
from app.schemas.distribution import DistributionCreate, ExchangeCreate

router = APIRouter(prefix="/api/distribution-orders", tags=["distribution"])


def get_service(db: Session = Depends(get_db)):
    return DistributionService(db)


@router.post("", status_code=201)
def create_distribution(data: DistributionCreate, svc: DistributionService = Depends(get_service)):
    try:
        return svc.create_distribution(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_distributions(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    svc: DistributionService = Depends(get_service),
):
    return svc.list_with_amounts(customer_id, status)


@router.get("/export")
def export_distributions(svc: DistributionService = Depends(get_service)):
    return svc.export_csv()


@router.post("/import")
async def import_distributions(file: UploadFile = File(...), svc: DistributionService = Depends(get_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: DistributionService = Depends(get_service)):
    return svc.import_confirm(data.get("rows", []))


@router.get("/{document_id}")
def get_distribution(document_id: int, svc: DistributionService = Depends(get_service)):
    detail = svc.get_detail(document_id)
    if not detail:
        raise HTTPException(status_code=404, detail="铺货单不存在")
    return detail


@router.post("/{document_id}/exchange")
def exchange(document_id: int, data: ExchangeCreate, svc: DistributionService = Depends(get_service)):
    try:
        return svc.exchange(document_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{document_id}/settle")
def settle(document_id: int, data: dict, svc: DistributionService = Depends(get_service)):
    try:
        return svc.settle(document_id, data.get("amount", 0))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch-settle")
def batch_settle(data: dict, svc: DistributionService = Depends(get_service)):
    try:
        return svc.batch_settle(data.get("customer_id", 0), data.get("items", []))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
