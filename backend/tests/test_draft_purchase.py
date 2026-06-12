"""测试草稿进货单确认时 auto-read items"""

import pytest


class TestDraftPurchase:
    def test_confirm_draft_without_items(self, client, seed_data):
        """创建草稿，确认时不传 items -> 从 purchase_items 自动读取"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
            "status": "draft",
        })
        assert resp.status_code == 201
        order_id = resp.json()["id"]

        # 确认时不传 items
        client.post(f"/api/purchases/{order_id}/confirm")

        # 库存应增加 5
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is not None and stock["stock"] == 5

    def test_confirm_draft_with_items(self, client, seed_data):
        """创建草稿，确认时传 items -> 使用传入的 items（覆盖草稿）"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]

        # 草稿 items 数量为 2
        resp = client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 2, "unit_price": 35}],
            "status": "draft",
        })
        assert resp.status_code == 201
        order_id = resp.json()["id"]

        # 确认时传入不同的 items（数量 5）
        client.post(f"/api/purchases/{order_id}/confirm", json={
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
        })

        # 库存应增加 5（传入的值），而不是 2（草稿的值）
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is not None and stock["stock"] == 5
