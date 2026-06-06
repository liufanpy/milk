from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # 兼容已有数据库: 确保新增的列存在
    from sqlalchemy import text, inspect
    insp = inspect(engine)

    # 新增列列表
    new_cols = [
        ("stock_movements", "purchase_order_id", "INTEGER REFERENCES purchase_orders(id)"),
        ("transactions", "purchase_order_id", "INTEGER REFERENCES purchase_orders(id)"),
        ("stock_movements", "retail_order_id", "INTEGER REFERENCES retail_orders(id)"),
        ("transactions", "subscription_order_id", "INTEGER REFERENCES subscription_orders(id)"),
        ("transactions", "retail_order_id", "INTEGER REFERENCES retail_orders(id)"),
    ]
    for table, col, col_type in new_cols:
        cols = [c["name"] for c in insp.get_columns(table)]
        if col not in cols:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()

    # subscription_orders 重命名列 + 新增 note
    sub_cols = [c["name"] for c in insp.get_columns("subscription_orders")]
    rename_map = [
        ("total_amount", "paid_amount"),
        ("remaining_bottles", "remaining_amount"),
    ]
    for old_name, new_name in rename_map:
        if old_name in sub_cols and new_name not in sub_cols:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE subscription_orders RENAME COLUMN {old_name} TO {new_name}"))
                conn.commit()

    if "note" not in sub_cols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE subscription_orders ADD COLUMN note VARCHAR(500) DEFAULT ''"))
            conn.commit()

    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
