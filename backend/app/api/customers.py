from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.customer_service import CustomerService
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerOut
import io

router = APIRouter(prefix="/api/customers", tags=["customers"])


def get_customer_service(db: Session = Depends(get_db)):
    return CustomerService(db)


@router.get("", response_model=list[CustomerOut])
def list_customers(
    keyword: str = Query(""),
    price_tier: str = Query(""),
    svc: CustomerService = Depends(get_customer_service),
):
    return svc.list_customers(keyword, price_tier=price_tier)


@router.get("/export")
def export_customers(svc: CustomerService = Depends(get_customer_service)):
    csv_content = svc.export_csv()
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, svc: CustomerService = Depends(get_customer_service)):
    return svc.get_customer(customer_id)


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(data: CustomerCreate, svc: CustomerService = Depends(get_customer_service)):
    return svc.create_customer(data)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerUpdate, svc: CustomerService = Depends(get_customer_service)):
    return svc.update_customer(customer_id, data)


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int, svc: CustomerService = Depends(get_customer_service)):
    svc.delete_customer(customer_id)


@router.get("/{customer_id}/prices")
def get_customer_prices(customer_id: int, svc: CustomerService = Depends(get_customer_service)):
    return svc.get_prices(customer_id)


@router.post("/{customer_id}/prices", status_code=201)
def add_customer_price(customer_id: int, product_id: int, price: float, svc: CustomerService = Depends(get_customer_service)):
    return svc.add_price(customer_id, product_id, price)


@router.delete("/{customer_id}/prices/{price_id}", status_code=204)
def delete_customer_price(customer_id: int, price_id: int, svc: CustomerService = Depends(get_customer_service)):
    svc.delete_price(price_id)


@router.get("/{customer_id}/resolve-price")
def resolve_product_price(customer_id: int, product_id: int, svc: CustomerService = Depends(get_customer_service)):
    try:
        return svc.resolve_product_price(customer_id, product_id)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/import")
async def import_customers(file: UploadFile = File(...), svc: CustomerService = Depends(get_customer_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: CustomerService = Depends(get_customer_service)):
    return svc.import_confirm(data.get("rows", []))
