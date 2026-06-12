from enum import Enum


class DocumentType(str, Enum):
    purchase = "purchase"
    retail = "retail"
    distribution = "distribution"
    return_order = "return"
    wastage = "wastage"
    subscription = "subscription"
    store_sales = "store_sales"
    inventory_check = "inventory_check"


class Direction(str, Enum):
    in_ = "in"
    out = "out"


class TransactionCategory(str, Enum):
    purchase = "purchase"
    retail = "retail"
    distribution = "distribution"
    subscription = "subscription"
    payment = "payment"
    refund = "refund"
    wastage = "wastage"
    promo = "promo"
    store_sales = "store_sales"


class OrderStatus(str, Enum):
    draft = "draft"
    confirmed = "confirmed"
    cancelled = "cancelled"
    pending = "pending"
    delivered = "delivered"
    settled = "settled"
    active = "active"
    completed = "completed"


class DistributionItemType(str, Enum):
    exchange_return = "exchange_return"
    exchange_new = "exchange_new"


class WastageReason(str, Enum):
    expired = "expired"
    damaged = "damaged"
    self_consumed = "self_consumed"
