from pydantic import BaseModel, Field
from typing import Optional


class ShelfCreate(BaseModel):
    name: str = Field(..., max_length=200)
    customer_id: Optional[int] = None


class ShelfUpdate(BaseModel):
    name: Optional[str] = None
    customer_id: Optional[int] = None


class ShelfOut(BaseModel):
    id: int
    name: str
    customer_id: Optional[int] = None

    class Config:
        from_attributes = True
