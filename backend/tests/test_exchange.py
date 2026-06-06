"""测试换货 — 金额一致换货 + 金额不一致拒绝"""
import pytest


class TestExchange:
    def test_exchange_same_product(self, client, seed_data):
        """同产品换货：库存增减相抵，应收不变"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        c = seed_data["customers"][0]

        # 备货
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 20, "unit_price": 35},
            ],
            "status": "confirmed",
        })

        # 创建送货单
        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 3, "unit_price": 38},
            ],
        })
        delivery_id = resp.json()["id"]
        detail_before = client.get(f"/api/deliveries/{delivery_id}").json()
        assert detail_before["total_amount"] == 114  # 3 × 38

        # 同产品换货：退 1 换 1，同价
        resp = client.post(f"/api/deliveries/{delivery_id}/exchange", json={
            "return_items": [
                {"product_id": p.id, "quantity": 1, "unit_price": 38},
            ],
            "new_items": [
                {"product_id": p.id, "quantity": 1, "unit_price": 38},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["return_total"] == 38
        assert resp.json()["new_total"] == 38

        # 验证详情
        detail = client.get(f"/api/deliveries/{delivery_id}").json()
        assert detail["total_amount"] == 114  # 应收不变
        assert len(detail["items"]) == 1  # 只有原始送货品项
        assert len(detail["exchanges"]) == 1  # 一条换货记录
        assert detail["exchanges"][0]["return_items"][0]["quantity"] == 1
        assert detail["exchanges"][0]["new_items"][0]["quantity"] == 1

    def test_exchange_same_value_different_product(self, client, seed_data):
        """等值换不同产品：库存变化，应收不变"""
        s = seed_data["suppliers"][0]
        p1 = seed_data["products"][0]
        p2 = seed_data["products"][1]
        c = seed_data["customers"][0]

        # 备货两种产品
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 20, "unit_price": 35},
                {"product_id": p2.id, "quantity": 20, "unit_price": 42},
            ],
            "status": "confirmed",
        })

        # 创建送货单
        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 2, "unit_price": 38},
            ],
        })
        delivery_id = resp.json()["id"]

        # p1 退 2(¥76) 换 p2 2(单价改 38，¥76，等值)
        resp = client.post(f"/api/deliveries/{delivery_id}/exchange", json={
            "return_items": [
                {"product_id": p1.id, "quantity": 2, "unit_price": 38},
            ],
            "new_items": [
                {"product_id": p2.id, "quantity": 2, "unit_price": 38},
            ],
        })
        assert resp.status_code == 200

        detail = client.get(f"/api/deliveries/{delivery_id}").json()
        assert detail["total_amount"] == 76  # 应收不变
        assert len(detail["exchanges"]) == 1
        assert detail["exchanges"][0]["return_items"][0]["product_id"] == p1.id
        assert detail["exchanges"][0]["new_items"][0]["product_id"] == p2.id

    def test_exchange_amount_mismatch_rejected(self, client, seed_data):
        """金额不一致拒绝换货"""
        s = seed_data["suppliers"][0]
        p1 = seed_data["products"][0]
        p2 = seed_data["products"][1]
        c = seed_data["customers"][0]

        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 20, "unit_price": 35},
                {"product_id": p2.id, "quantity": 20, "unit_price": 42},
            ],
            "status": "confirmed",
        })

        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 1, "unit_price": 38},
            ],
        })
        delivery_id = resp.json()["id"]

        # 退 1(¥38) 换 3(¥114)，金额不一致
        resp = client.post(f"/api/deliveries/{delivery_id}/exchange", json={
            "return_items": [
                {"product_id": p1.id, "quantity": 1, "unit_price": 38},
            ],
            "new_items": [
                {"product_id": p2.id, "quantity": 3, "unit_price": 38},
            ],
        })
        assert resp.status_code == 400
        assert "金额不一致" in resp.json()["detail"]

    def test_exchange_insufficient_stock_fails(self, client, seed_data):
        """换货新发品项库存不足时拒绝"""
        s = seed_data["suppliers"][0]
        p1 = seed_data["products"][0]
        p2 = seed_data["products"][1]
        c = seed_data["customers"][0]

        # 只给 p1 备货，不给 p2
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 20, "unit_price": 35},
            ],
            "status": "confirmed",
        })

        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 5, "unit_price": 38},
            ],
        })
        delivery_id = resp.json()["id"]

        # 退 p1 换 p2，但 p2 无库存
        resp = client.post(f"/api/deliveries/{delivery_id}/exchange", json={
            "return_items": [
                {"product_id": p1.id, "quantity": 1, "unit_price": 38},
            ],
            "new_items": [
                {"product_id": p2.id, "quantity": 1, "unit_price": 38},
            ],
        })
        assert resp.status_code == 400
        assert "库存不足" in resp.json()["detail"]
