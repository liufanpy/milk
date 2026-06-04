import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.sale_service import SaleService
from app.schemas.sale import SaleCreate
from app.models.transaction import Transaction

router = APIRouter(prefix="/api/sales", tags=["sales"])


def get_sale_service(db: Session = Depends(get_db)):
    return SaleService(db)


@router.post("", status_code=201)
def create_sale(data: SaleCreate, svc: SaleService = Depends(get_sale_service)):
    return svc.create_sale(data)


@router.get("")
def list_sales(svc: SaleService = Depends(get_sale_service)):
    return svc.list_sales()


@router.get("/export")
def export_sales(db: Session = Depends(get_db)):
    rows = db.query(Transaction).filter(Transaction.category == "sale").order_by(Transaction.created_at.desc()).all()
    csv_lines = ["ID,客户ID,金额,送货单ID,时间"]
    for r in rows:
        csv_lines.append(f"{r.id},{r.customer_id or ''},{r.amount},{r.delivery_id or ''},{r.created_at}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=sales.csv"})
