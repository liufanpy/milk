def resolve_price(customer_id: int, product_id: int, db, fallback: str = "retail") -> float:
    """客户价格解析：专属价 > 批发价(若tier=批发) > 兜底价

    fallback 为 "retail" 时兜底用零售价，"wholesale" 时兜底用批发价。
    巡店场景固定传 "wholesale"，因为门店与奶站按批发价结算。
    """
    from app.models.product import Product
    from app.models.customer import Customer
    from app.models.product_customer_price import ProductCustomerPrice

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return 0.0

    custom = db.query(ProductCustomerPrice).filter(
        ProductCustomerPrice.customer_id == customer_id,
        ProductCustomerPrice.product_id == product_id,
    ).first()
    if custom:
        return custom.price

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer and customer.price_tier == "批发":
        return product.default_wholesale_price

    return product.default_retail_price if fallback == "retail" else product.default_wholesale_price
