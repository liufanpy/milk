from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime


class PurchaseItem(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float
    shelf_id: int


class PurchaseCreate(BaseModel):
    """创建进货单（前端提交）"""
    supplier_id: int
    purchase_date: date
    items: List[PurchaseItem]
    note: str = ""
    status: str = "confirmed"  # "draft" 或 "confirmed"


class PurchaseOrderOut(BaseModel):
    """进货单列表项"""
    id: int
    order_number: str
    supplier_id: int
    supplier_name: str
    purchase_date: str
    total_amount: float
    status: str
    note: str
    created_at: str

    class Config:
        from_attributes = True


class PurchaseOrderDetail(PurchaseOrderOut):
    """进货单详情 = 单头 + 品项"""
    items: List[dict]


class PurchaseConfirm(BaseModel):
    """确认草稿单（可不传 items 直接用已有数据）"""
    items: Optional[List[PurchaseItem]] = None


class PurchaseCancel(BaseModel):
    """撤销"""
    pass
