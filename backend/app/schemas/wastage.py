from pydantic import BaseModel
from typing import List

VALID_REASONS = {"expired", "damaged", "self_consumed"}


class WastageItem(BaseModel):
    product_id: int
    quantity: int
    reason: str          # expired / damaged / self_consumed


class WastageCreate(BaseModel):
    items: List[WastageItem]
    note: str = ""
