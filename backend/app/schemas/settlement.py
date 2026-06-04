from pydantic import BaseModel


class SettlementCreate(BaseModel):
    amount: float
