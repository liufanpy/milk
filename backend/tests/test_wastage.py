"""测试损耗单创建/列表/详情/撤销"""


class TestWastageCreate:
    def test_create_wastage_writes_stock_out(self, client, seed_data):
        """创建损耗单：库存减少"""
        # 先进货入库 10 箱
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 10, "unit_price": 35}],
            "status": "confirmed",
        })

        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 3, "reason": "expired"}],
        })

        assert resp.status_code == 201
        assert resp.json()["item_count"] == 1

        # 库存剩 7
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is not None
        assert stock["stock"] == 7

    def test_create_wastage_invalid_reason_fails(self, client, seed_data):
        """无效的 reason 被拒绝"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
            "status": "confirmed",
        })

        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 1, "reason": "giveaway"}],
        })
        assert resp.status_code == 400

    def test_create_wastage_insufficient_stock_fails(self, client, seed_data):
        """库存不足时拒绝"""
        p = seed_data["products"][0]
        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 100, "reason": "damaged"}],
        })
        assert resp.status_code == 400


class TestWastageListAndDetail:
    def test_list_returns_order_structure(self, client, seed_data):
        """损耗列表返回单头结构"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
            "status": "confirmed",
        })
        client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 2, "reason": "expired"}],
        })

        resp = client.get("/api/wastage")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "items_summary" in data[0]
        assert "reasons" in data[0]
        assert "status" in data[0]

    def test_detail_includes_reason(self, client, seed_data):
        """损耗详情包含品项 reason"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
            "status": "confirmed",
        })
        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 2, "reason": "self_consumed"}],
        })
        order_id = resp.json()["id"]

        detail = client.get(f"/api/wastage/{order_id}").json()
        assert detail["items"][0]["reason"] == "self_consumed"


class TestWastageCancel:
    def test_cancel_reverses_stock(self, client, seed_data):
        """撤销损耗：库存恢复"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
            "status": "confirmed",
        })
        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 2, "reason": "expired"}],
        })
        order_id = resp.json()["id"]

        client.post(f"/api/wastage/{order_id}/cancel")

        # 库存恢复 5
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock["stock"] == 5
