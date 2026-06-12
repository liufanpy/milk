from datetime import date, datetime

from sqlalchemy.orm import Session

from app.enums import Direction, DocumentType
from app.models.document import Document
from app.models.inventory_check import InventoryCheck
from app.models.inventory_check_item import InventoryCheckItem
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.services.document_helpers import create_document


class InventoryCheckService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, check_date: date | None = None, note: str = "") -> dict:
        doc = create_document(self.db, DocumentType.inventory_check)
        order = InventoryCheck(
            document_id=doc.id,
            check_date=check_date or date.today(),
            note=note,
        )
        self.db.add(order)
        self.db.commit()
        return {"id": doc.id, "order_number": doc.order_number, "check_date": str(order.check_date), "status": order.status}

    def list_checks(self) -> list[dict]:
        orders = self.db.query(InventoryCheck).order_by(InventoryCheck.created_at.desc()).all()
        if not orders:
            return []

        doc_ids = [o.document_id for o in orders]
        docs = {d.id: d for d in self.db.query(Document).filter(Document.id.in_(doc_ids)).all()}

        result = []
        for o in orders:
            item_count = self.db.query(InventoryCheckItem).filter(
                InventoryCheckItem.document_id == o.document_id
            ).count()
            doc = docs.get(o.document_id)
            result.append({
                "id": o.document_id,
                "order_number": doc.order_number if doc else "",
                "check_date": str(o.check_date),
                "status": o.status,
                "item_count": item_count,
                "note": o.note,
                "confirmed_at": str(o.confirmed_at) if o.confirmed_at else None,
                "created_at": str(o.created_at),
            })
        return result

    def get_detail(self, document_id: int) -> dict | None:
        order = self.db.query(InventoryCheck).filter(
            InventoryCheck.document_id == document_id
        ).first()
        if not order:
            return None

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        products = {p.id: p for p in self.db.query(Product).all()}

        if order.status == "draft":
            return self._build_draft_detail(order, doc, products)

        items = self.db.query(InventoryCheckItem).filter(
            InventoryCheckItem.document_id == document_id
        ).all()

        item_list = []
        for it in items:
            p = products.get(it.product_id)
            item_list.append({
                "product_id": it.product_id,
                "product_name": p.name if p else "",
                "theoretical_qty": it.theoretical_qty,
                "actual_qty": it.actual_qty,
                "difference": it.difference,
            })

        return {
            "id": document_id,
            "order_number": doc.order_number if doc else "",
            "check_date": str(order.check_date),
            "status": order.status,
            "note": order.note,
            "confirmed_at": str(order.confirmed_at) if order.confirmed_at else None,
            "created_at": str(order.created_at),
            "items": item_list,
        }

    def _build_draft_detail(self, order, doc, products: dict) -> dict:
        theoretical = self._compute_warehouse_inventory()

        saved_items = self.db.query(InventoryCheckItem).filter(
            InventoryCheckItem.document_id == order.document_id
        ).all()
        saved_map = {it.product_id: it for it in saved_items}

        item_list = []
        for pid, theo_qty in theoretical.items():
            saved = saved_map.get(pid)
            actual_qty = saved.actual_qty if saved else None
            difference = (actual_qty - theo_qty) if actual_qty is not None else None
            p = products.get(pid)
            item_list.append({
                "product_id": pid,
                "product_name": p.name if p else "",
                "theoretical_qty": theo_qty,
                "actual_qty": actual_qty,
                "difference": difference,
            })

        return {
            "id": order.document_id,
            "order_number": doc.order_number if doc else "",
            "check_date": str(order.check_date),
            "status": order.status,
            "note": order.note,
            "confirmed_at": None,
            "created_at": str(order.created_at),
            "items": item_list,
        }

    def _compute_warehouse_inventory(self) -> dict[int, int]:
        from sqlalchemy import func, case
        rows = (
            self.db.query(
                StockMovement.product_id,
                func.sum(
                    case(
                        (StockMovement.direction == Direction.in_, StockMovement.quantity),
                        (StockMovement.direction == Direction.out, -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .filter(StockMovement.store_id.is_(None))
            .group_by(StockMovement.product_id)
            .all()
        )
        return {r.product_id: (r.stock or 0) for r in rows}

    def save_items(self, document_id: int, items: list[dict]) -> dict:
        order = self.db.query(InventoryCheck).filter(
            InventoryCheck.document_id == document_id
        ).first()
        if not order:
            raise ValueError("盘点单不存在")
        if order.status != "draft":
            raise ValueError("只有草稿状态的盘点单可以修改")

        self.db.query(InventoryCheckItem).filter(
            InventoryCheckItem.document_id == document_id
        ).delete()

        for it in items:
            self.db.add(InventoryCheckItem(
                document_id=document_id,
                product_id=it["product_id"],
                actual_qty=it.get("actual_qty"),
            ))

        self.db.commit()
        return {"id": document_id, "item_count": len(items)}

    def confirm(self, document_id: int) -> dict:
        order = self.db.query(InventoryCheck).filter(
            InventoryCheck.document_id == document_id
        ).first()
        if not order:
            raise ValueError("盘点单不存在")
        if order.status != "draft":
            raise ValueError("只有草稿状态的盘点单可以确认")

        theoretical = self._compute_warehouse_inventory()

        items = self.db.query(InventoryCheckItem).filter(
            InventoryCheckItem.document_id == document_id
        ).all()

        for it in items:
            theo = theoretical.get(it.product_id, 0)
            it.theoretical_qty = theo
            it.difference = (it.actual_qty or 0) - theo

        order.status = "confirmed"
        order.confirmed_at = datetime.now()
        self.db.commit()
        return {"id": document_id, "status": "confirmed"}
