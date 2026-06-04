from sqlalchemy.orm import Session
from app.repositories.product_repo import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.csv_importer import parse_csv

PRODUCT_HEADERS = [
    "name", "名称", "brand", "品牌", "category", "分类",
    "unit", "单位", "barcode", "条码",
    "default_retail_price", "零售默认价",
    "default_wholesale_price", "批发默认价",
    "shelf_life_days", "保质期天",
]

# 缓存上传解析结果，key 为临时 id
_import_sessions: dict[str, list[dict]] = {}


class ProductService:
    def __init__(self, db: Session):
        self.repo = ProductRepository(db)
        self.db = db

    def list_products(self, keyword: str = ""):
        return self.repo.search(keyword)

    def get_product(self, product_id: int):
        return self.repo.get_by_id(product_id)

    def create_product(self, data: ProductCreate):
        return self.repo.create(**data.model_dump())

    def update_product(self, product_id: int, data: ProductUpdate):
        return self.repo.update(product_id, **data.model_dump(exclude_unset=True))

    def delete_product(self, product_id: int):
        return self.repo.delete(product_id)

    def export_csv(self) -> str:
        products = self.repo.get_all(limit=10000)
        headers = ["名称", "品牌", "分类", "单位", "条码", "零售默认价", "批发默认价", "保质期天"]
        lines = [",".join(headers)]
        for p in products:
            lines.append(",".join([
                p.name, p.brand, p.category, p.unit, p.barcode,
                str(p.default_retail_price), str(p.default_wholesale_price), str(p.shelf_life_days),
            ]))
        return "\n".join(lines)

    def import_preview(self, file_content: bytes) -> dict:
        def validate(row: dict) -> str | bool:
            name = (row.get("name") or row.get("名称") or "").strip()
            if not name:
                return "名称为空"
            if self.repo.get_by_name(name):
                return f"'{name}' 已存在"
            try:
                price = float(row.get("default_retail_price") or row.get("零售默认价") or 0)
                if price < 0:
                    return "零售默认价不能为负"
                price = float(row.get("default_wholesale_price") or row.get("批发默认价") or 0)
                if price < 0:
                    return "批发默认价不能为负"
            except ValueError:
                return "价格格式错误"
            return True

        return parse_csv(file_content, validate, PRODUCT_HEADERS)

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
                    brand=(data.get("brand") or data.get("品牌") or "").strip(),
                    category=(data.get("category") or data.get("分类") or "").strip(),
                    unit=(data.get("unit") or data.get("单位") or "箱").strip(),
                    barcode=(data.get("barcode") or data.get("条码") or "").strip(),
                    default_retail_price=float(data.get("default_retail_price") or data.get("零售默认价") or 0),
                    default_wholesale_price=float(data.get("default_wholesale_price") or data.get("批发默认价") or 0),
                    shelf_life_days=int(float(data.get("shelf_life_days") or data.get("保质期天") or 0)),
                )
                success += 1
            except Exception as e:
                errors.append({"row": row.get("index", "?"), "msg": str(e)})

        return {"success": success, "errors": errors}
