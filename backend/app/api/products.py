from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.product_service import ProductService
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut
import io

router = APIRouter(prefix="/api/products", tags=["products"])


def get_product_service(db: Session = Depends(get_db)):
    return ProductService(db)


@router.get("", response_model=list[ProductOut])
def list_products(
    keyword: str = Query(""),
    svc: ProductService = Depends(get_product_service),
):
    return svc.list_products(keyword)


@router.get("/export")
def export_products(svc: ProductService = Depends(get_product_service)):
    csv_content = svc.export_csv()
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, svc: ProductService = Depends(get_product_service)):
    return svc.get_product(product_id)


@router.post("", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, svc: ProductService = Depends(get_product_service)):
    return svc.create_product(data)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, svc: ProductService = Depends(get_product_service)):
    return svc.update_product(product_id, data)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, svc: ProductService = Depends(get_product_service)):
    svc.delete_product(product_id)


@router.post("/import")
async def import_products(file: UploadFile = File(...), svc: ProductService = Depends(get_product_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: ProductService = Depends(get_product_service)):
    return svc.import_confirm(data.get("rows", []))
