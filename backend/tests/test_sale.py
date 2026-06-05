"""测试零售创建"""
import pytest


class TestSaleCreate:
    def test_create_sale_with_unit_price(self, client, seed_data):
        """创建零售，传入 unit_price"""
        sh = seed_data["shelves"][0]
        p = seed_data["products"][0]

        # 先入库
        client.post("/api/purchases", json={
            "supplier_id": seed_data["suppliers"][0].id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 10, "unit_price": 35, "shelf_id": sh.id},
            ],
            "status": "confirmed",
        })

        # 创建零售
        resp = client.post("/api/sales", json={
            "customer_id": seed_data["customers"][0].id,
            "items": [
                {"product_id": p.id, "quantity": 2, "unit_price": 45, "shelf_id": sh.id},
            ],
        })

        assert resp.status_code == 201
        assert resp.json()["total"] == 90  # 2 × 45

        # 库存减少
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock["stock"] == 8

    def test_create_sale_without_customer(self, client, seed_data):
        """不选客户(散客)也能创建零售"""
        sh = seed_data["shelves"][0]
        p = seed_data["products"][0]

        # 先入库
        client.post("/api/purchases", json={
            "supplier_id": seed_data["suppliers"][0].id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 5, "unit_price": 35, "shelf_id": sh.id},
            ],
            "status": "confirmed",
        })

        resp = client.post("/api/sales", json={
            "customer_id": None,
            "items": [
                {"product_id": p.id, "quantity": 1, "unit_price": 50, "shelf_id": sh.id},
            ],
        })

        assert resp.status_code == 201
        assert resp.json()["total"] == 50
