from sqlalchemy.orm import Session
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.delivery_repo import DeliveryRepository


class SettlementService:
    def __init__(self, db: Session):
        self.db = db
        self.txn_repo = TransactionRepository(db)
        self.delivery_repo = DeliveryRepository(db)

    def settle(self, delivery_id: int, amount: float):
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            raise ValueError("送货单不存在")

        self.txn_repo.create(
            customer_id=delivery.customer_id,
            category="payment",
            amount=amount,
            delivery_id=delivery_id,
        )
        self.db.commit()
        return {"delivery_id": delivery_id, "paid": amount}
