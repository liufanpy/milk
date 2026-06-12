"""测试铺货单 CSV 导入功能"""

import io
import pytest


class TestDistributionImport:
    def test_import_preview_distribution(self, client, seed_data):
        """预览铺货导入，解析价格正常"""
        csv = "产品名称,数量,售价,客户名称\r\n蒙牛鲜奶,3,45,张老板超市"
        resp = client.post("/api/distribution-orders/import",
                           files=[("file", ("test.csv",
                                            io.BytesIO(csv.encode("utf-8-sig")),
                                            "text/csv"))])
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["ok"] >= 1
        ok_rows = [r for r in data["rows"] if r["status"] == "ok"]
        assert ok_rows[0]["data"].get("售价") == "45"

    def test_import_confirm_distribution(self, client, seed_data):
        """确认铺货导入 -> 创建订单 + 品项 + 库存变动 + 流水"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        c = seed_data["customers"][0]

        # 先入库
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 20, "unit_price": 35}],
            "status": "confirmed",
        })

        # 预览
        csv = "产品名称,数量,售价,客户名称\r\n蒙牛鲜奶,3,45,张老板超市"
        prev_resp = client.post("/api/distribution-orders/import",
                                files=[("file", ("test.csv",
                                                 io.BytesIO(csv.encode("utf-8-sig")),
                                                 "text/csv"))])
        ok_rows = [r for r in prev_resp.json()["rows"] if r["status"] == "ok"]

        # 确认
        confirm_resp = client.post("/api/distribution-orders/import/confirm",
                                   json={"rows": ok_rows})
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["success"] == 1

        # 验证订单已创建
        orders = client.get("/api/distribution-orders").json()
        assert len(orders) >= 1

        # 库存从 20 减少到 17
        inv = client.get("/api/inventory").json()
        stock = next((r for r in inv if r["product_id"] == p.id), None)
        assert stock is not None and stock["stock"] == 17

        # 验证流水
        txns = client.get("/api/transaction-ledger").json()
        dist_txns = [t for t in txns if t["category"] == "distribution"]
        assert any(t["amount"] == 135 for t in dist_txns)  # 3×45=135
