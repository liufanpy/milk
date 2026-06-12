import csv
import io
from datetime import date, datetime
from fastapi.responses import StreamingResponse


DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]


def resolve_product(db, name: str) -> int | None:
    from app.models.product import Product
    p = db.query(Product).filter(Product.name == name.strip()).first()
    return p.id if p else None


def resolve_customer(db, name: str) -> int | None:
    from app.models.customer import Customer
    c = db.query(Customer).filter(Customer.name == name.strip()).first()
    return c.id if c else None


def resolve_supplier(db, name: str) -> int | None:
    from app.models.supplier import Supplier
    s = db.query(Supplier).filter(Supplier.name == name.strip()).first()
    return s.id if s else None


def resolve_store(db, name: str) -> int | None:
    from app.models.store import Store
    s = db.query(Store).filter(Store.name == name.strip()).first()
    return s.id if s else None


def parse_date(s: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


def make_csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    if not rows:
        return StreamingResponse(iter([""]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
