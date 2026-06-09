from datetime import datetime, date
import json
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.purchase import PurchaseCreate
from app.models.purchase_order import PurchaseOrder
from app.models.product import Product
from app.models.supplier import Supplier

PURCHASE_HEADERS = ["产品名称", "product_name", "数量", "quantity", "进价", "unit_price", "供应商名称", "supplier_name", "日期", "date"]

DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]


def _parse_date(s: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    # ── 单号生成 ──────────────────────────────────

    def _next_order_number(self) -> str:
        from app.services.order_number import next_order_number
        return next_order_number(self.db, PurchaseOrder, "PO")

    # ── 创建进货单 ────────────────────────────────

    def create_purchase(self, data: PurchaseCreate):
        total = sum(item.quantity * item.unit_price for item in data.items)
        items_data = [{"product_id": it.product_id, "quantity": it.quantity, "unit_price": it.unit_price} for it in data.items]
        order = PurchaseOrder(
            order_number=self._next_order_number(),
            supplier_id=data.supplier_id,
            purchase_date=data.purchase_date,
            total_amount=total,
            note=data.note,
            status=data.status,
            _items_json=json.dumps(items_data, ensure_ascii=False),
        )
        self.db.add(order)
        self.db.flush()

        if data.status == "confirmed":
            self._confirm_items(order.id, data.items)

        self.db.commit()
        return {"id": order.id, "order_number": order.order_number, "status": order.status}

    # ── 确认草稿单 ────────────────────────────────

    def confirm_order(self, order_id: int, items: list | None = None):
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if not order:
            raise ValueError("进货单不存在")
        if order.status != "draft":
            raise ValueError("仅草稿状态可确认")

        if items:
            total = sum(
                (it["quantity"] if isinstance(it, dict) else it.quantity) *
                (it["unit_price"] if isinstance(it, dict) else it.unit_price)
                for it in items
            )
            order.total_amount = total
        else:
            items = []

        order.status = "confirmed"
        self._confirm_items(order_id, items)
        self.db.commit()
        return {"id": order.id, "status": "confirmed"}

    def _confirm_items(self, order_id: int, items: list):
        total = 0.0
        movements = []
        for item in items:
            qty = item["quantity"] if isinstance(item, dict) else item.quantity
            cost = item["unit_price"] if isinstance(item, dict) else item.unit_price
            total += qty * cost
            movements.append({
                "product_id": item["product_id"] if isinstance(item, dict) else item.product_id,
                "direction": "in",
                "reason": "purchase",
                "quantity": qty,
                "unit_price": cost,
                "source_type": "purchase",
                "source_id": order_id,
            })

        if movements:
            self.stock_repo.bulk_create(movements)

        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if total > 0:
            self.txn_repo.create(
                supplier_id=order.supplier_id,
                category="purchase",
                amount=total,
                source_type="purchase",
                source_id=order_id,
            )

    # ── 撤销进货单 ────────────────────────────────

    def cancel_order(self, order_id: int):
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if not order:
            raise ValueError("进货单不存在")

        if order.status == "draft":
            order.status = "cancelled"
            self.db.commit()
            return {"id": order.id, "status": "cancelled"}

        if order.status == "confirmed":
            # 反向冲抵库存
            original_items = self.stock_repo.get_by_source("purchase", order_id)
            # 校验：已出库的商品不能撤销
            inventory = {r.product_id: r.stock for r in self.stock_repo.get_inventory()}
            for item in original_items:
                stock = inventory.get(item.product_id, 0)
                if stock < item.quantity:
                    raise ValueError(f"该进货单商品已被部分售出，库存不足，无法撤销")
            reverses = []
            reverse_total = 0.0
            for item in original_items:
                reverses.append({
                    "product_id": item.product_id,
                    "direction": "out",
                    "reason": "cancel",
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "source_type": "purchase",
                    "source_id": order_id,
                })
                reverse_total += item.quantity * item.unit_price

            if reverses:
                self.stock_repo.bulk_create(reverses)
            if reverse_total > 0:
                self.txn_repo.create(
                    supplier_id=order.supplier_id,
                    category="purchase",
                    amount=-reverse_total,
                    source_type="purchase",
                    source_id=order_id,
                )

            order.status = "cancelled"
            order.updated_at = datetime.now()
            self.db.commit()
            return {"id": order.id, "status": "cancelled"}

    # ── 列表 ──────────────────────────────────────

    def list_purchases(self):
        orders = (
            self.db.query(PurchaseOrder)
            .order_by(PurchaseOrder.created_at.desc())
            .all()
        )
        suppliers = {s.id: s.name for s in self.db.query(Supplier).all()}
        return [
            {
                "id": o.id,
                "order_number": o.order_number,
                "supplier_id": o.supplier_id,
                "supplier_name": suppliers.get(o.supplier_id, ""),
                "purchase_date": str(o.purchase_date),
                "total_amount": o.total_amount,
                "status": o.status,
                "note": o.note,
                "created_at": str(o.created_at),
            }
            for o in orders
        ]

    # ── 详情 ──────────────────────────────────────

    def get_purchase_detail(self, order_id: int):
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if not order:
            return None
        items = self.stock_repo.get_by_source_reason("purchase", order_id, "purchase")
        products = {p.id: p.name for p in self.db.query(Product).all()}
        suppliers = {s.id: s.name for s in self.db.query(Supplier).all()}

        # 草稿无 stock_movement，从 _items_json 读取
        if not items and order._items_json:
            try:
                raw = json.loads(order._items_json)
                items = []
                for r in raw:
                    items.append({
                        "product_id": r["product_id"],
                        "product_name": products.get(r["product_id"], ""),
                        "quantity": r["quantity"],
                        "unit_price": r["unit_price"],
                    })
            except (json.JSONDecodeError, KeyError):
                items = []

        def item_dir(i):
            if isinstance(i, dict):
                return {
                    "product_id": i["product_id"],
                    "product_name": i.get("product_name", products.get(i["product_id"], "")),
                    "quantity": i["quantity"],
                    "unit_price": i["unit_price"],
                }
            return {
                "product_id": i.product_id,
                "product_name": products.get(i.product_id, ""),
                "quantity": i.quantity,
                "unit_price": i.unit_price,
            }

        return {
            "id": order.id,
            "order_number": order.order_number,
            "supplier_id": order.supplier_id,
            "supplier_name": suppliers.get(order.supplier_id, ""),
            "purchase_date": str(order.purchase_date),
            "total_amount": order.total_amount,
            "status": order.status,
            "note": order.note,
            "created_at": str(order.created_at),
            "items": [item_dir(i) for i in items],
        }

    # ── CSV 导入（保持兼容，直接创建 confirmed 单） ──

    DFLT_SUPPLIER = "金健牛奶"

    def _name_maps(self):
        prods = {p.name: (p.id, p.default_purchase_price) for p in self.db.query(Product).all()}
        suppliers = {s.name: s.id for s in self.db.query(Supplier).all()}
        return prods, suppliers

    def import_preview(self, file_content: bytes) -> dict:
        prods, suppliers = self._name_maps()

        def validate(row: dict) -> str | bool:
            pname = (row.get("产品名称") or row.get("product_name") or "").strip()
            if not pname:
                return "产品名称为空"
            if pname not in prods:
                return f"产品'{pname}'不存在"
            qty = row.get("数量") or row.get("quantity") or "0"
            try:
                if int(float(qty)) <= 0:
                    return "数量必须大于0"
            except ValueError:
                return "数量格式错误"
            supname = (row.get("供应商名称") or row.get("supplier_name") or "").strip() or self.DFLT_SUPPLIER
            if supname not in suppliers:
                return f"供应商'{supname}'不存在"
            return True

        from app.services.csv_importer import parse_csv
        return parse_csv(file_content, validate, PURCHASE_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        prods, suppliers = self._name_maps()
        success = 0
        errors: list[dict] = []

        groups: dict[str, list[dict]] = {}
        for row in rows:
            data = row.get("data", row)
            supname = (data.get("供应商名称") or data.get("supplier_name") or "").strip() or self.DFLT_SUPPLIER
            if supname not in groups:
                groups[supname] = []
            groups[supname].append(data)

        for supname, items in groups.items():
            sid = suppliers.get(supname)
            if not sid:
                for item in items:
                    errors.append({"row": item.get("index", "?"), "msg": f"供应商'{supname}'不存在"})
                continue

            order = PurchaseOrder(
                order_number=self._next_order_number(),
                supplier_id=sid,
                purchase_date=date.today(),
                total_amount=0.0,
                status="confirmed",
            )
            self.db.add(order)
            self.db.flush()

            total = 0.0
            movements = []
            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                p = prods.get(pname)
                if not p:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                pid, default_cost = p
                qty = int(float(data.get("数量") or data.get("quantity") or 0))
                cost = data.get("进价") or data.get("unit_price") or ""
                cost = float(cost) if cost else default_cost
                date_str = (data.get("日期") or data.get("date") or "").strip()
                item_date = _parse_date(date_str) if date_str else date.today()
                total += qty * cost
                movements.append({
                    "product_id": pid,
                    "direction": "in", "reason": "purchase",
                    "quantity": qty, "unit_price": cost,
                    "source_type": "purchase",
                    "source_id": order.id,
                    "created_at": datetime.now(),
                })

            if movements:
                self.stock_repo.bulk_create(movements)
                if total > 0:
                    self.txn_repo.create(supplier_id=sid, category="purchase", amount=total, source_type="purchase", source_id=order.id)
                order.total_amount = total
                success += len(movements)

        self.db.commit()
        return {"success": success, "errors": errors}
