"""测试进货单创建"""
import pytest


class TestPurchaseCreate:
    def test_create_confirmed_purchase_with_unit_price(self, client, seed_data):
        """确认入库，unit_price 写入 stock_movements"""
        s = seed_data["suppliers"][0]
        sh = seed_data["shelves"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 10, "unit_price": 35, "shelf_id": sh.id},
            ],
            "status": "confirmed",
        })

        assert resp.status_code == 201
        order_id = resp.json()["id"]

        # 验证库存
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is not None
        assert stock["stock"] == 10

        # 验证进货单详情中的 unit_price
        detail = client.get(f"/api/purchases/{order_id}").json()
        assert detail["total_amount"] == 350  # 10 × 35
        assert detail["items"][0]["unit_price"] == 35

    def test_create_draft_purchase(self, client, seed_data):
        """草稿进货单不写库存"""
        s = seed_data["suppliers"][0]
        sh = seed_data["shelves"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 5, "unit_price": 40, "shelf_id": sh.id},
            ],
            "status": "draft",
        })

        assert resp.status_code == 201
        assert resp.json()["status"] == "draft"

        # 库存不应变化
        inventory = client.get("/api/inventory").json()
        assert inventory == [] or all(ri["stock"] == 0 for ri in inventory)

    def test_confirm_draft_writes_stock(self, client, seed_data):
        """草稿确认后写库存，unit_price 保留"""
        s = seed_data["suppliers"][0]
        sh = seed_data["shelves"][0]
        p = seed_data["products"][0]

        # 创建草稿
        r = client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 3, "unit_price": 36, "shelf_id": sh.id},
            ],
            "status": "draft",
        })
        order_id = r.json()["id"]

        # 确认草稿（重新传 items）
        client.post(f"/api/purchases/{order_id}/confirm", json={
            "items": [
                {"product_id": p.id, "quantity": 3, "unit_price": 36, "shelf_id": sh.id},
            ],
        })

        # 库存应该有 3 箱
        inventory = client.get("/api/inventory").json()
        assert inventory[0]["stock"] == 3

    def test_cancel_confirmed_purchase_reverses_stock(self, client, seed_data):
        """撤销已确认的进货单，库存反向冲抵"""
        s = seed_data["suppliers"][0]
        sh = seed_data["shelves"][0]
        p = seed_data["products"][0]

        # 创建并确认
        r = client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 8, "unit_price": 35, "shelf_id": sh.id},
            ],
            "status": "confirmed",
        })
        order_id = r.json()["id"]

        # 撤销
        client.post(f"/api/purchases/{order_id}/cancel")

        # 库存应该归零（入库 8 + 冲抵 -8 = 0）
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is None or stock["stock"] == 0
