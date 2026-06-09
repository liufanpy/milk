from pydantic import BaseModel
from typing import Optional


class StoreCreate(BaseModel):
    name: str
    customer_id: Optional[int] = None
    address: str = ""


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    customer_id: Optional[int] = None
    address: Optional[str] = None
    status: Optional[str] = None


class StoreOut(BaseModel):
    id: int
    name: str
    customer_id: int | None
    customer_name: str
    address: str
    status: str
    created_at: str

    class Config:
        from_attributes = True
