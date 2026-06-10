from pydantic import BaseModel
from typing import List
from datetime import date


class StoreSalesItem(BaseModel):
    product_id: int
    actual_quantity: int


class StoreSalesCreate(BaseModel):
    store_id: int
    check_date: date
    items: List[StoreSalesItem]
    note: str = ""


class StoreSalesOut(BaseModel):
    id: int
    order_number: str
    store_id: int
    store_name: str
    check_date: str
    status: str
    item_count: int
    note: str
    created_at: str
