from fastapi import APIRouter
from app.api import products, customers, suppliers, shelves, purchases, sales, deliveries

api_router = APIRouter()
api_router.include_router(products.router)
api_router.include_router(customers.router)
api_router.include_router(suppliers.router)
api_router.include_router(shelves.router)
api_router.include_router(purchases.router)
api_router.include_router(sales.router)
api_router.include_router(deliveries.router)
