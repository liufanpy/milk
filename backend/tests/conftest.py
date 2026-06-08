import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import *


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db_session):
    p1 = Product(name="蒙牛鲜奶", brand="蒙牛", category="鲜奶", unit="箱",
                 default_purchase_price=35, default_retail_price=45, default_wholesale_price=38)
    p2 = Product(name="伊利酸奶", brand="伊利", category="酸奶", unit="箱",
                 default_purchase_price=42, default_retail_price=55, default_wholesale_price=48)
    db_session.add_all([p1, p2])

    c1 = Customer(name="张老板超市", price_tier="批发", default_payment="周结")
    c2 = Customer(name="散客小王", price_tier="零售", default_payment="现结")
    db_session.add_all([c1, c2])

    s1 = Supplier(name="蒙牛代理")
    db_session.add(s1)

    db_session.commit()

    return {
        "products": [p1, p2],
        "customers": [c1, c2],
        "suppliers": [s1],
    }
