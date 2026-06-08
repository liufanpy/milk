"""测试退货单创建/列表/详情/撤销"""


class TestReturnCreate:
    def test_create_return_writes_stock_and_refund(self, client, seed_data):
        """创建退货单：库存入库 + 退款 transaction"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [
                {"product_id": p.id, "quantity": 2, "unit_price": 45},
            ],
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["refund_total"] == 90

        # 验证库存变化（退货入库 2 箱）
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is not None
        assert stock["stock"] == 2

    def test_create_return_generates_order_number(self, client, seed_data):
        """退货单自动生成单号"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [
                {"product_id": p.id, "quantity": 1, "unit_price": 45},
            ],
        })

        assert resp.status_code == 201
        order_id = resp.json()["id"]
        detail = client.get(f"/api/returns/{order_id}").json()
        assert detail["order_number"] is not None
        assert detail["order_number"].startswith("RT")

    def test_create_return_writes_stock_in(self, client, seed_data):
        """退货入库：库存增加"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [
                {"product_id": p.id, "quantity": 3, "unit_price": 45},
            ],
        })

        assert resp.status_code == 201
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is not None
        assert stock["stock"] == 3


class TestReturnListAndDetail:
    def test_list_returns_order_structure(self, client, seed_data):
        """退货列表返回单头结构"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [{"product_id": p.id, "quantity": 2, "unit_price": 45}],
        })

        resp = client.get("/api/returns")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        order = data[0]
        assert "order_number" in order
        assert "customer_name" in order
        assert "items_summary" in order
        assert "total_refund" in order
        assert "status" in order

    def test_detail_includes_items(self, client, seed_data):
        """退货详情包含品项明细"""
        c = seed_data["customers"][0]
        p1 = seed_data["products"][0]
        p2 = seed_data["products"][1]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [
                {"product_id": p1.id, "quantity": 2, "unit_price": 45},
                {"product_id": p2.id, "quantity": 1, "unit_price": 55},
            ],
        })

        order_id = resp.json()["id"]
        detail = client.get(f"/api/returns/{order_id}").json()
        assert len(detail["items"]) == 2
        assert detail["total_refund"] == 145  # 90 + 55


class TestReturnCancel:
    def test_cancel_reverses_stock_and_refund(self, client, seed_data):
        """撤销退货：库存反向 + 退款冲抵"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [{"product_id": p.id, "quantity": 2, "unit_price": 45}],
        })
        order_id = resp.json()["id"]

        # 撤销
        resp = client.post(f"/api/returns/{order_id}/cancel")
        assert resp.status_code == 200

        # 库存归零（入库 2 + 冲抵 out 2 = 0）
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is None or stock["stock"] == 0

        # 状态变为 cancelled
        detail = client.get(f"/api/returns/{order_id}").json()
        assert detail["status"] == "cancelled"

    def test_cancel_already_cancelled_fails(self, client, seed_data):
        """已撤销的退货不可再撤销"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [{"product_id": p.id, "quantity": 1, "unit_price": 45}],
        })
        order_id = resp.json()["id"]

        client.post(f"/api/returns/{order_id}/cancel")
        resp = client.post(f"/api/returns/{order_id}/cancel")
        assert resp.status_code == 400
