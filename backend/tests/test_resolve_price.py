"""测试价格解析 API"""
import pytest


class TestResolvePrice:
    def test_wholesale_customer_gets_wholesale_price(self, client, seed_data):
        """批发客户得到批发价"""
        c = seed_data["customers"][0]  # 张老板超市, price_tier=批发
        p = seed_data["products"][0]   # 蒙牛鲜奶, wholesale=38

        resp = client.get(f"/api/customers/{c.id}/resolve-price?product_id={p.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["price"] == 38
        assert "批发" in data["source"]

    def test_retail_customer_gets_retail_price(self, client, seed_data):
        """零售客户得到零售价"""
        c = seed_data["customers"][1]  # 散客小王, price_tier=零售
        p = seed_data["products"][0]   # 蒙牛鲜奶, retail=45

        resp = client.get(f"/api/customers/{c.id}/resolve-price?product_id={p.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["price"] == 45

    def test_nonexistent_customer_gets_retail_price(self, client, seed_data):
        """不存在的客户 ID 返回默认零售价"""
        p = seed_data["products"][0]  # retail=45

        resp = client.get(f"/api/customers/99999/resolve-price?product_id={p.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["price"] == 45

    def test_customer_zero_gets_retail_price(self, client, seed_data):
        """customer_id=0（散客）返回默认零售价"""
        p = seed_data["products"][1]  # 伊利酸奶, retail=55

        resp = client.get(f"/api/customers/0/resolve-price?product_id={p.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["price"] == 55

    def test_custom_price_overrides_tier(self, client, seed_data):
        """客户专属价优先于等级价"""
        c = seed_data["customers"][0]  # 张老板超市, 批发
        p = seed_data["products"][0]   # wholesale=38

        # 设置专属价 36
        client.post(f"/api/customers/{c.id}/prices?product_id={p.id}&price=36")

        resp = client.get(f"/api/customers/{c.id}/resolve-price?product_id={p.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["price"] == 36
        assert "专属" in data["source"]

    def test_nonexistent_product_returns_404(self, client):
        """不存在的产品返回 404"""
        resp = client.get("/api/customers/1/resolve-price?product_id=99999")

        assert resp.status_code == 404
