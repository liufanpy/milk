"""Create API vs CSV Import 一致性：相同数据产生相同的库存 + 流水"""

import io
import pytest


class TestCreateVsImport:
    def test_purchase_create_vs_import_same_result(self, client, seed_data):
        """API 创建与 CSV 导入产生相同的库存和流水结构"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]

        # ── 1. API 创建 ──
        api_resp = client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 10, "unit_price": 35}],
            "status": "confirmed",
        })
        assert api_resp.status_code == 201
        api_order_id = api_resp.json()["id"]

        # 验证库存
        inv1 = client.get("/api/inventory").json()
        stock1 = next((r for r in inv1 if r["product_id"] == p.id), None)
        assert stock1["stock"] == 10

        # 验证流水
        txns1 = client.get("/api/transaction-ledger").json()
        txn1 = [t for t in txns1 if t["category"] == "purchase" and t["amount"] == 350]
        assert len(txn1) >= 1

        # 撤销，清空库存以便下一步
        client.post(f"/api/purchases/{api_order_id}/cancel")

        # ── 2. CSV 导入 ──
        csv = "产品名称,数量,进价,供应商名称,日期\r\n蒙牛鲜奶,10,35,蒙牛代理,2026-06-05"
        prev_resp = client.post("/api/purchases/import",
                                files=[("file", ("test.csv",
                                                 io.BytesIO(csv.encode("utf-8-sig")),
                                                 "text/csv"))])
        assert prev_resp.status_code == 200
        ok_rows = [r for r in prev_resp.json()["rows"] if r["status"] == "ok"]

        imp_resp = client.post("/api/purchases/import/confirm",
                               json={"rows": ok_rows})
        assert imp_resp.status_code == 200
        assert imp_resp.json()["success"] >= 1

        # 验证库存与 API 创建一致
        inv2 = client.get("/api/inventory").json()
        stock2 = next((r for r in inv2 if r["product_id"] == p.id), None)
        assert stock2["stock"] == 10  # 与 API 创建一样

        # 验证存在非取消的 purchase 流水，金额 350
        txns2 = client.get("/api/transaction-ledger").json()
        txn2 = [t for t in txns2 if t["category"] == "purchase" and t["amount"] > 0]
        positive_350 = [t for t in txn2 if t["amount"] == 350]
        # API 创建（已撤） + CSV 导入 = 2 笔正向 350 的 purchase 流水
        assert len(positive_350) == 2
