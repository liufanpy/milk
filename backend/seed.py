"""Seed demo data for 奶记"""
import sys
sys.path.insert(0, '.')

from app.database import engine, SessionLocal, Base
from app.models import *
from datetime import date, timedelta, datetime

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    # Products
    p1 = Product(name="蒙牛鲜奶", brand="蒙牛", category="鲜奶", unit="箱", default_retail_price=45, default_wholesale_price=38, shelf_life_days=7)
    p2 = Product(name="伊利酸奶", brand="伊利", category="酸奶", unit="箱", default_retail_price=55, default_wholesale_price=48, shelf_life_days=15)
    p3 = Product(name="光明纯牛奶", brand="光明", category="常温奶", unit="箱", default_retail_price=60, default_wholesale_price=52, shelf_life_days=180)
    db.add_all([p1, p2, p3])
    db.commit()

    # Customers
    c1 = Customer(name="张老板超市", phone="13800001111", address="中山路1号", price_tier="wholesale", default_payment="credit")
    c2 = Customer(name="李阿姨订奶", phone="13800002222", address="解放路2号", price_tier="subscription", default_payment="immediate")
    db.add_all([c1, c2])
    db.commit()

    # Suppliers
    s1 = Supplier(name="蒙牛代理", contact="王经理", phone="13900001111")
    db.add(s1)
    db.commit()

    # Shelves
    sh1 = Shelf(name="仓库A区")
    sh2 = Shelf(name="门店货架")
    db.add_all([sh1, sh2])
    db.commit()

    # A purchase (seed stock)
    sm1 = StockMovement(product_id=p1.id, shelf_id=sh1.id, direction="in", reason="purchase", quantity=50, unit_cost=35, created_at=datetime.utcnow())
    sm2 = StockMovement(product_id=p2.id, shelf_id=sh1.id, direction="in", reason="purchase", quantity=30, unit_cost=42, created_at=datetime.utcnow())
    db.add_all([sm1, sm2])
    txn1 = Transaction(supplier_id=s1.id, category="purchase", amount=50*35+30*42, created_at=datetime.utcnow())
    db.add(txn1)
    db.commit()

    # A delivery
    d1 = Delivery(customer_id=c1.id, delivery_date=date.today(), status="delivered", note="首批铺货")
    db.add(d1)
    db.flush()

    sm3 = StockMovement(product_id=p1.id, shelf_id=sh2.id, direction="out", reason="sale", quantity=10, delivery_id=d1.id, created_at=datetime.utcnow())
    sm4 = StockMovement(product_id=p2.id, shelf_id=sh2.id, direction="out", reason="sale", quantity=5, delivery_id=d1.id, created_at=datetime.utcnow())
    db.add_all([sm3, sm4])
    txn2 = Transaction(customer_id=c1.id, category="sale", amount=10*38+5*48, delivery_id=d1.id, created_at=datetime.utcnow())
    db.add(txn2)

    # Partial payment
    txn3 = Transaction(customer_id=c1.id, category="payment", amount=300, delivery_id=d1.id, created_at=datetime.utcnow())
    db.add(txn3)
    db.commit()

    print("Seed data created successfully!")
    print(f"  Products: {p1.name}, {p2.name}, {p3.name}")
    print(f"  Customers: {c1.name}, {c2.name}")
    print(f"  Supplier: {s1.name}")
    print(f"  Shelves: {sh1.name}, {sh2.name}")
    print(f"  Delivery #{d1.id}: {10+5} items, total ¥{10*38+5*48}, paid ¥300")

finally:
    db.close()
