from fastapi import APIRouter
from app.api import products, customers, suppliers, purchases, sales, deliveries, returns, wastage, settlements, subscriptions, inventory, dashboard, operation_logs, stock_ledger, transaction_ledger

api_router = APIRouter()
api_router.include_router(products.router)
api_router.include_router(customers.router)
api_router.include_router(suppliers.router)
api_router.include_router(purchases.router)
api_router.include_router(sales.router)
api_router.include_router(deliveries.router)
api_router.include_router(returns.router)
api_router.include_router(wastage.router)
api_router.include_router(settlements.router)
api_router.include_router(subscriptions.router)
api_router.include_router(inventory.router)
api_router.include_router(dashboard.router)
api_router.include_router(operation_logs.router)
api_router.include_router(stock_ledger.router)
api_router.include_router(transaction_ledger.router)
