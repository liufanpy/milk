from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.supplier_service import SupplierService
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierOut
import io

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def get_supplier_service(db: Session = Depends(get_db)):
    return SupplierService(db)


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    keyword: str = Query(""),
    svc: SupplierService = Depends(get_supplier_service),
):
    return svc.list_suppliers(keyword)


@router.get("/export")
def export_suppliers(svc: SupplierService = Depends(get_supplier_service)):
    csv_content = svc.export_csv()
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=suppliers.csv"},
    )


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, svc: SupplierService = Depends(get_supplier_service)):
    return svc.get_supplier(supplier_id)


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierCreate, svc: SupplierService = Depends(get_supplier_service)):
    return svc.create_supplier(data)


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, data: SupplierUpdate, svc: SupplierService = Depends(get_supplier_service)):
    return svc.update_supplier(supplier_id, data)


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int, svc: SupplierService = Depends(get_supplier_service)):
    svc.delete_supplier(supplier_id)


@router.post("/import")
async def import_suppliers(file: UploadFile = File(...), svc: SupplierService = Depends(get_supplier_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: SupplierService = Depends(get_supplier_service)):
    return svc.import_confirm(data.get("rows", []))
