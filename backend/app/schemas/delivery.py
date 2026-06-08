from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class DeliveryCreateItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class DeliveryCreate(BaseModel):
    customer_id: int
    delivery_date: date
    items: List[DeliveryCreateItem]
    subscription_order_id: Optional[int] = None
    paid: bool = False
    note: str = ""


class DeliveryOut(BaseModel):
    id: int
    customer_id: int
    delivery_date: date
    status: str
    subscription_order_id: Optional[int] = None
    note: str
    total_amount: float = 0.0
    paid_amount: float = 0.0
    unpaid_amount: float = 0.0

    class Config:
        from_attributes = True


class ExchangeItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class ExchangeCreate(BaseModel):
    return_items: List[ExchangeItem]
    new_items: List[ExchangeItem]
