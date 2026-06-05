"""测试送货单创建 — unit_price 写入 stock_movements"""
import pytest


class TestDeliveryCreate:
    def test_create_delivery_records_unit_price(self, client, seed_data):
        """创建送货单，stock_movements.unit_price 应写入售价"""
        # 先备货：做一笔进货入库
        s = seed_data["suppliers"][0]
        sh1 = seed_data["shelves"][0]  # 仓库
        sh2 = seed_data["shelves"][1]  # 门店
        p = seed_data["products"][0]
        c = seed_data["customers"][0]

        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 20, "unit_price": 35, "shelf_id": sh1.id},
            ],
            "status": "confirmed",
        })

        # 创建送货单（售价不同于进价）
        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 3, "unit_price": 38, "shelf_id": sh1.id},
            ],
        })

        assert resp.status_code == 201
        assert resp.json()["total"] == 114  # 3 × 38

        # 验证 transactions 金额
        detail = client.get(f"/api/deliveries/{resp.json()['id']}").json()
        assert detail["total_amount"] == 114

    def test_delivery_insufficient_stock_fails(self, client, seed_data):
        """库存不足时创建送货单应返回 400"""
        p = seed_data["products"][0]
        sh = seed_data["shelves"][0]
        c = seed_data["customers"][0]

        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 5, "unit_price": 38, "shelf_id": sh.id},
            ],
        })

        assert resp.status_code == 400
        assert "库存不足" in resp.json()["detail"]
