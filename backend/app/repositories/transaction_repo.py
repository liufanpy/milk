from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Transaction:
        txn = Transaction(**kwargs)
        self.db.add(txn)
        self.db.flush()
        return txn

    def get_by_source(self, source_type: str, source_id: int) -> List[Transaction]:
        return self.db.query(Transaction).filter(
            Transaction.source_type == source_type,
            Transaction.source_id == source_id,
        ).all()

    def get_ar_by_customer(self, customer_id: int) -> float:
        result = self.db.query(
            func.sum(
                case(
                    (Transaction.category.in_(["distribution", "retail", "subscription"]), Transaction.amount),
                    (Transaction.category == "payment", -Transaction.amount),
                    (Transaction.category == "refund", -Transaction.amount),
                    else_=0,
                )
            )
        ).filter(Transaction.customer_id == customer_id).scalar()
        return result or 0.0

    def get_receivables(self) -> list:
        case_expr = case(
            (Transaction.category.in_(["distribution", "retail", "subscription"]), Transaction.amount),
            (Transaction.category == "payment", -Transaction.amount),
            (Transaction.category == "refund", -Transaction.amount),
            else_=0,
        )
        return (
            self.db.query(
                Transaction.customer_id,
                func.sum(case_expr).label("ar_balance"),
            )
            .filter(Transaction.customer_id.isnot(None))
            .group_by(Transaction.customer_id)
            .having(func.sum(case_expr) != 0)
            .all()
        )

    def get_amounts_by_deliveries(self, delivery_ids: list[int]) -> dict[int, dict]:
        if not delivery_ids:
            return {}
        rows = (
            self.db.query(
                Transaction.source_id,
                Transaction.category,
                func.sum(Transaction.amount).label("total"),
            )
            .filter(
                Transaction.source_type == "delivery",
                Transaction.source_id.in_(delivery_ids),
            )
            .group_by(Transaction.source_id, Transaction.category)
            .all()
        )
        result: dict[int, dict] = {did: {"total_amount": 0.0, "paid_amount": 0.0} for did in delivery_ids}
        for row in rows:
            if row.category in ("distribution", "delivery", "delivery_cancel"):
                result[row.source_id]["total_amount"] += row.total
            elif row.category == "payment":
                result[row.source_id]["paid_amount"] += row.total
        for did, amounts in result.items():
            amounts["unpaid_amount"] = amounts["total_amount"] - amounts["paid_amount"]
        return result

    def list_all(self):
        return self.db.query(Transaction).order_by(Transaction.created_at.desc()).limit(200).all()
