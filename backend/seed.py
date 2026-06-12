"""Seed demo data for 奶记"""
import sys
sys.path.insert(0, '.')

from app.database import engine, SessionLocal, Base
from app.models import *
from app.enums import DocumentType, Direction, TransactionCategory
from app.services.document_helpers import create_document
from datetime import date, datetime

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    # ── Products ──
    p1 = Product(name="蒙牛鲜奶", brand="蒙牛", category="鲜奶", unit="箱",
                 default_purchase_price=35, default_retail_price=45, default_wholesale_price=38, shelf_life_days=7)
    p2 = Product(name="伊利酸奶", brand="伊利", category="酸奶", unit="箱",
                 default_purchase_price=42, default_retail_price=55, default_wholesale_price=48, shelf_life_days=15)
    p3 = Product(name="光明纯牛奶", brand="光明", category="常温奶", unit="箱",
                 default_purchase_price=50, default_retail_price=60, default_wholesale_price=52, shelf_life_days=180)
    db.add_all([p1, p2, p3])
    db.commit()

    # ── Customers ──
    c1 = Customer(name="张老板超市", phone="13800001111", address="中山路1号", price_tier="批发", default_payment="周结")
    c2 = Customer(name="李阿姨订奶", phone="13800002222", address="解放路2号", price_tier="零售", default_payment="现结")
    db.add_all([c1, c2])
    db.commit()

    # ── Suppliers ──
    s1 = Supplier(name="蒙牛代理", contact="王经理", phone="13900001111")
    db.add(s1)
    db.commit()

    # ── Store ──
    store = Store(name="张老板超市门店", customer_id=c1.id, address="中山路1号")
    db.add(store)
    db.commit()

    # ── Purchase (进货) ──
    doc1 = create_document(db, DocumentType.purchase)
    po = PurchaseOrder(document_id=doc1.id, supplier_id=s1.id, purchase_date=date.today(),
                       total_amount=50*35+30*42, status="confirmed")
    db.add(po)
    db.add(PurchaseItem(document_id=doc1.id, product_id=p1.id, quantity=50, unit_price=35))
    db.add(PurchaseItem(document_id=doc1.id, product_id=p2.id, quantity=30, unit_price=42))
    db.add_all([
        StockMovement(product_id=p1.id, direction=Direction.in_, quantity=50,
                      source_type=DocumentType.purchase, source_id=doc1.id),
        StockMovement(product_id=p2.id, direction=Direction.in_, quantity=30,
                      source_type=DocumentType.purchase, source_id=doc1.id),
    ])
    db.add(Transaction(category=TransactionCategory.purchase, amount=50*35+30*42,
                       source_type=DocumentType.purchase, source_id=doc1.id))
    db.commit()

    # ── Distribution (铺货) ──
    doc2 = create_document(db, DocumentType.distribution)
    do = DistributionOrder(document_id=doc2.id, customer_id=c1.id, delivery_date=date.today(),
                           status="delivered", store_id=store.id, note="首批铺货")
    db.add(do)
    db.add(DistributionOrderItem(document_id=doc2.id, product_id=p1.id, quantity=10, unit_price=38))
    db.add(DistributionOrderItem(document_id=doc2.id, product_id=p2.id, quantity=5, unit_price=48))
    # 总仓出库 + 店铺入库
    db.add_all([
        StockMovement(product_id=p1.id, direction=Direction.out, quantity=10,
                      source_type=DocumentType.distribution, source_id=doc2.id),
        StockMovement(product_id=p2.id, direction=Direction.out, quantity=5,
                      source_type=DocumentType.distribution, source_id=doc2.id),
        StockMovement(product_id=p1.id, direction=Direction.in_, quantity=10,
                      source_type=DocumentType.distribution, source_id=doc2.id, store_id=store.id),
        StockMovement(product_id=p2.id, direction=Direction.in_, quantity=5,
                      source_type=DocumentType.distribution, source_id=doc2.id, store_id=store.id),
    ])
    db.add(Transaction(category=TransactionCategory.distribution, amount=10*38+5*48,
                       customer_id=c1.id, source_type=DocumentType.distribution, source_id=doc2.id))
    # 部分回款
    db.add(Transaction(category=TransactionCategory.payment, amount=300,
                       customer_id=c1.id, source_type=DocumentType.distribution, source_id=doc2.id))
    db.commit()

    print("Seed data created successfully!")
    print(f"  Products: {p1.name}, {p2.name}, {p3.name}")
    print(f"  Customers: {c1.name}, {c2.name}")
    print(f"  Supplier: {s1.name}")
    print(f"  Store: {store.name}")
    print(f"  Purchase: PO{doc1.order_number} — {50+30} items, ¥{50*35+30*42}")
    print(f"  Distribution: DO{doc2.order_number} — {10+5} items, ¥{10*38+5*48}, paid ¥300")

finally:
    db.close()
