"""测试进货单的 expiry_date 自动计算"""

import io
from datetime import date, timedelta
import pytest


class TestPurchaseExpiry:
    def test_create_purchase_calculates_expiry(self, client, seed_data, db_session):
        """创建进货单时传入 production_date -> expiry = production_date + shelf_life_days"""
        p = seed_data["products"][0]
        p.shelf_life_days = 7
        db_session.commit()

        s = seed_data["suppliers"][0]
        resp = client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{
                "product_id": p.id,
                "quantity": 10,
                "unit_price": 35,
                "production_date": "2026-01-01",
            }],
            "status": "confirmed",
        })
        assert resp.status_code == 201
        order_id = resp.json()["id"]

        from app.models import PurchaseItem
        item = db_session.query(PurchaseItem).filter(
            PurchaseItem.document_id == order_id
        ).first()
        assert item is not None
        assert item.expiry_date == date(2026, 1, 8)  # 2026-01-01 + 7 days

    def test_import_calculates_expiry(self, client, seed_data, db_session):
        """导入进货单 CSV 时自动计算 expiry"""
        p = seed_data["products"][0]
        p.shelf_life_days = 7
        db_session.commit()

        s = seed_data["suppliers"][0]
        csv = "产品名称,数量,进价,供应商名称,日期\r\n蒙牛鲜奶,10,35,蒙牛代理,2026-01-01"
        prev_resp = client.post("/api/purchases/import",
                                files=[("file", ("test.csv",
                                                 io.BytesIO(csv.encode("utf-8-sig")),
                                                 "text/csv"))])
        assert prev_resp.status_code == 200
        ok_rows = [r for r in prev_resp.json()["rows"] if r["status"] == "ok"]

        confirm_resp = client.post("/api/purchases/import/confirm",
                                   json={"rows": ok_rows})
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["success"] >= 1

        from app.models import PurchaseItem
        item = db_session.query(PurchaseItem).order_by(PurchaseItem.id.desc()).first()
        assert item is not None
        assert item.expiry_date == date(2026, 1, 8)  # 2026-01-01 + 7 days
