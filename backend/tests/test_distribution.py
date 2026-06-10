"""测试铺货单创建"""
import pytest


class TestDistributionCreate:
    def test_create_distribution_records_unit_price(self, client, seed_data):
        """创建铺货单，transaction 金额应写入售价"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        c = seed_data["customers"][0]

        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 20, "unit_price": 35},
            ],
            "status": "confirmed",
        })

        resp = client.post("/api/distribution-orders", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 3, "unit_price": 38},
            ],
        })

        assert resp.status_code == 201
        assert resp.json()["total"] == 114

        detail = client.get(f"/api/distribution-orders/{resp.json()['id']}").json()
        assert detail["total_amount"] == 114

    def test_distribution_insufficient_stock_fails(self, client, seed_data):
        """库存不足时创建铺货单应返回 400"""
        p = seed_data["products"][0]
        c = seed_data["customers"][0]

        resp = client.post("/api/distribution-orders", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 5, "unit_price": 38},
            ],
        })

        assert resp.status_code == 400
        assert "库存不足" in resp.json()["detail"]
