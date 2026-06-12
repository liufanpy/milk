"""测试 Enum 以 value（而非 name）存储在数据库中"""

from sqlalchemy import text
import pytest


class TestEnumValues:
    def test_direction_enum_stored_as_value(self, client, seed_data, db_session):
        """create purchase → StockMovement.direction 存储为 'in' 而非 'in_'"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 10, "unit_price": 35}],
            "status": "confirmed",
        })

        # 直接查数据库原始值
        result = db_session.execute(
            text("SELECT direction FROM stock_movements LIMIT 1")
        ).scalar()
        assert result == "in", f"期望 'in'，实际为 {result!r}"

        # ORM 反序列化为 Enum，value 也应该为 'in'
        from app.models import StockMovement
        sm = db_session.query(StockMovement).first()
        assert sm.direction.value == "in"

    def test_transaction_category_stored_as_value(self, client, seed_data, db_session):
        """create purchase → Transaction.category 存储为 'purchase'"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 10, "unit_price": 35}],
            "status": "confirmed",
        })

        result = db_session.execute(
            text("SELECT category FROM transactions LIMIT 1")
        ).scalar()
        assert result == "purchase", f"期望 'purchase'，实际为 {result!r}"

        from app.models import Transaction
        txn = db_session.query(Transaction).first()
        assert txn.category.value == "purchase"
