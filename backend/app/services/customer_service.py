from sqlalchemy.orm import Session
from app.repositories.customer_repo import CustomerRepository
from app.repositories.product_customer_price_repo import ProductCustomerPriceRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.csv_importer import parse_csv

CUSTOMER_HEADERS = [
    "name", "名称", "phone", "电话", "address", "地址",
    "price_tier", "价格档位", "default_payment", "默认结账",
]


class CustomerService:
    def __init__(self, db: Session):
        self.repo = CustomerRepository(db)
        self.price_repo = ProductCustomerPriceRepository(db)
        self.db = db

    def list_customers(self, keyword: str = ""):
        return self.repo.search(keyword)

    def get_customer(self, customer_id: int):
        return self.repo.get_by_id(customer_id)

    def create_customer(self, data: CustomerCreate):
        return self.repo.create(**data.model_dump())

    def update_customer(self, customer_id: int, data: CustomerUpdate):
        return self.repo.update(customer_id, **data.model_dump(exclude_unset=True))

    def delete_customer(self, customer_id: int):
        return self.repo.delete(customer_id)

    def get_prices(self, customer_id: int):
        return self.price_repo.get_by_customer(customer_id)

    def add_price(self, customer_id: int, product_id: int, price: float):
        return self.price_repo.create(customer_id=customer_id, product_id=product_id, price=price)

    def delete_price(self, price_id: int):
        return self.price_repo.delete(price_id)

    def import_preview(self, file_content: bytes) -> dict:
        def validate(row: dict) -> str | bool:
            name = (row.get("name") or row.get("名称") or "").strip()
            if not name:
                return "名称为空"
            if self.repo.get_by_name(name):
                return f"'{name}' 已存在"
            return True

        return parse_csv(file_content, validate, CUSTOMER_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        success = 0
        errors: list[dict] = []
        for row in rows:
            data = row.get("data", row)
            name = (data.get("name") or data.get("名称") or "").strip()
            if not name:
                errors.append({"row": row.get("index", "?"), "msg": "名称为空"})
                continue
            if self.repo.get_by_name(name):
                errors.append({"row": row.get("index", "?"), "msg": f"'{name}' 已存在"})
                continue
            try:
                self.repo.create(
                    name=name,
                    phone=(data.get("phone") or data.get("电话") or "").strip(),
                    address=(data.get("address") or data.get("地址") or "").strip(),
                    price_tier=(data.get("price_tier") or data.get("价格档位") or "retail").strip(),
                    default_payment=(data.get("default_payment") or data.get("默认结账") or "immediate").strip(),
                )
                success += 1
            except Exception as e:
                errors.append({"row": row.get("index", "?"), "msg": str(e)})

        return {"success": success, "errors": errors}
