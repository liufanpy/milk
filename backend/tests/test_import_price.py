"""分布导入中的价格解析：CSV 不含售价时通过客户/产品自动解析"""

import io
import pytest


class TestImportPriceResolution:
    def test_preview_resolves_empty_price(self, client, seed_data):
        """CSV 没有 售价 列 -> preview OK rows 自动解析 售价"""
        csv = "产品名称,数量,客户名称\r\n蒙牛鲜奶,10,散客小王"
        resp = client.post("/api/distribution-orders/import",
                           files=[("file", ("test.csv", io.BytesIO(csv.encode("utf-8-sig")), "text/csv"))])
        assert resp.status_code == 200
        data = resp.json()
        ok_rows = [r for r in data["rows"] if r["status"] == "ok"]
        assert len(ok_rows) >= 1
        # 散客小王零售价 45
        assert ok_rows[0]["data"].get("售价") == "45.0"

    def test_preview_resolves_when_customer_missing(self, client, seed_data):
        """CSV 用 customer_name（英文列名）而非 客户名称，依然能解析售价（回落默认零售价）"""
        csv = "产品名称,数量,customer_name\r\n蒙牛鲜奶,10,散客小王"
        resp = client.post("/api/distribution-orders/import",
                           files=[("file", ("test.csv", io.BytesIO(csv.encode("utf-8-sig")), "text/csv"))])
        assert resp.status_code == 200
        data = resp.json()
        ok_rows = [r for r in data["rows"] if r["status"] == "ok"]
        assert len(ok_rows) >= 1
        assert ok_rows[0]["data"].get("售价") == "45.0"

    def test_preview_always_includes_price_header(self, client, seed_data):
        """CSV 没有 售价 列，返回的 headers 仍然包含 售价"""
        csv = "产品名称,数量,客户名称\r\n蒙牛鲜奶,10,张老板超市"
        resp = client.post("/api/distribution-orders/import",
                           files=[("file", ("test.csv", io.BytesIO(csv.encode("utf-8-sig")), "text/csv"))])
        assert resp.status_code == 200
        data = resp.json()
        assert "售价" in data["headers"]

    def test_import_confirm_without_price_uses_resolved(self, client, seed_data):
        """导入确认时不传 售价 -> 系统自动解析价格，生成正确的流水"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        # 先入库供铺货出库
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 20, "unit_price": 35}],
            "status": "confirmed",
        })

        # 铺货导入确认，不传售价
        resp = client.post("/api/distribution-orders/import/confirm", json={
            "rows": [{"data": {
                "产品名称": "蒙牛鲜奶",
                "数量": "3",
                "客户名称": "散客小王",
                # 不传 售价
            }}]
        })
        assert resp.status_code == 200
        assert resp.json()["success"] == 1

        # 验证流水：3箱 × 零售价45 = 135
        txns = client.get("/api/transaction-ledger").json()
        dist_txns = [t for t in txns if t["category"] == "distribution"
                     and t["customer_name"] == "散客小王"]
        assert any(t["amount"] == 135 for t in dist_txns)

        # 库存 20-3=17
        inv = client.get("/api/inventory").json()
        stock = next((r for r in inv if r["product_id"] == p.id), None)
        assert stock is not None and stock["stock"] == 17
