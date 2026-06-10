"""测试换货 — 金额一致换货 + 金额不一致拒绝"""
import pytest


class TestExchange:
    def test_exchange_same_product(self, client, seed_data):
        """同产品换货：库存增减相抵，应收不变"""
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
        doc_id = resp.json()["id"]
        detail_before = client.get(f"/api/distribution-orders/{doc_id}").json()
        assert detail_before["total_amount"] == 114

        resp = client.post(f"/api/distribution-orders/{doc_id}/exchange", json={
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

        detail = client.get(f"/api/distribution-orders/{doc_id}").json()
        assert detail["total_amount"] == 114
        assert len(detail["items"]) >= 1
        assert len(detail["exchanges"]) == 1
        assert detail["exchanges"][0]["return_items"][0]["quantity"] == 1
        assert detail["exchanges"][0]["new_items"][0]["quantity"] == 1

    def test_exchange_same_value_different_product(self, client, seed_data):
        """等值换不同产品：库存变化，应收不变"""
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

        resp = client.post("/api/distribution-orders", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 2, "unit_price": 38},
            ],
        })
        doc_id = resp.json()["id"]

        resp = client.post(f"/api/distribution-orders/{doc_id}/exchange", json={
            "return_items": [
                {"product_id": p1.id, "quantity": 2, "unit_price": 38},
            ],
            "new_items": [
                {"product_id": p2.id, "quantity": 2, "unit_price": 38},
            ],
        })
        assert resp.status_code == 200

        detail = client.get(f"/api/distribution-orders/{doc_id}").json()
        assert detail["total_amount"] == 76
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

        resp = client.post("/api/distribution-orders", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 1, "unit_price": 38},
            ],
        })
        doc_id = resp.json()["id"]

        resp = client.post(f"/api/distribution-orders/{doc_id}/exchange", json={
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

        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 20, "unit_price": 35},
            ],
            "status": "confirmed",
        })

        resp = client.post("/api/distribution-orders", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 5, "unit_price": 38},
            ],
        })
        doc_id = resp.json()["id"]

        resp = client.post(f"/api/distribution-orders/{doc_id}/exchange", json={
            "return_items": [
                {"product_id": p1.id, "quantity": 1, "unit_price": 38},
            ],
            "new_items": [
                {"product_id": p2.id, "quantity": 1, "unit_price": 38},
            ],
        })
        assert resp.status_code == 400
        assert "库存不足" in resp.json()["detail"]
