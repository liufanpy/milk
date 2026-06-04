from pydantic import BaseModel


class SettlementCreate(BaseModel):
    amount: float


from typing import List


class BatchSettlementItem(BaseModel):
    delivery_id: int
    amount: float


class BatchSettlement(BaseModel):
    customer_id: int
    items: List[BatchSettlementItem]
