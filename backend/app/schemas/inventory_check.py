from pydantic import BaseModel
from typing import List
from datetime import date


class CheckItem(BaseModel):
    product_id: int
    actual_quantity: int


class InventoryCheckCreate(BaseModel):
    store_id: int
    check_date: date
    items: List[CheckItem]
    note: str = ""


class InventoryCheckOut(BaseModel):
    id: int
    order_number: str
    store_id: int
    store_name: str
    check_date: str
    status: str
    item_count: int
    note: str
    created_at: str
