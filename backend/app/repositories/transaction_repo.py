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

    def get_by_delivery(self, delivery_id: int) -> List[Transaction]:
        return self.db.query(Transaction).filter(
            Transaction.delivery_id == delivery_id
        ).all()

    def get_ar_by_customer(self, customer_id: int) -> float:
        result = self.db.query(
            func.sum(
                case(
                    (Transaction.category == "sale", Transaction.amount),
                    (Transaction.category == "payment", -Transaction.amount),
                    (Transaction.category == "subscription", -Transaction.amount),
                    (Transaction.category == "refund", -Transaction.amount),
                    else_=0,
                )
            )
        ).filter(Transaction.customer_id == customer_id).scalar()
        return result or 0.0

    def get_receivables(self) -> list:
        return (
            self.db.query(
                Transaction.customer_id,
                func.sum(
                    case(
                        (Transaction.category == "sale", Transaction.amount),
                        (Transaction.category == "payment", -Transaction.amount),
                        (Transaction.category == "subscription", -Transaction.amount),
                        (Transaction.category == "refund", -Transaction.amount),
                        else_=0,
                    )
                ).label("ar_balance"),
            )
            .filter(Transaction.customer_id.isnot(None))
            .group_by(Transaction.customer_id)
            .having(
                func.sum(
                    case(
                        (Transaction.category == "sale", Transaction.amount),
                        (Transaction.category == "payment", -Transaction.amount),
                        (Transaction.category == "subscription", -Transaction.amount),
                        (Transaction.category == "refund", -Transaction.amount),
                        else_=0,
                    )
                ) != 0
            )
            .all()
        )

    def list_all(self):
        return self.db.query(Transaction).order_by(Transaction.created_at.desc()).limit(200).all()
