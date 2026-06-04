from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # 兼容已有数据库: 确保新增的 purchase_order_id 列存在
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    for table, col in [("stock_movements", "purchase_order_id"), ("transactions", "purchase_order_id")]:
        cols = [c["name"] for c in insp.get_columns(table)]
        if col not in cols:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER REFERENCES purchase_orders(id)"))
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
