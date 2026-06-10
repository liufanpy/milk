from datetime import date
from sqlalchemy.orm import Session


def next_order_number(db: Session, model, prefix: str, doc_type=None) -> str:
    today = date.today().strftime("%Y%m%d")
    full_prefix = f"{prefix}{today}"
    q = db.query(model).filter(model.order_number.like(f"{full_prefix}%"))
    if doc_type is not None:
        q = q.filter(model.doc_type == doc_type)
    last = q.order_by(model.id.desc()).first()
    if last and last.order_number and len(last.order_number) == 14:
        seq = int(last.order_number[-4:]) + 1
    else:
        seq = 1
    return f"{full_prefix}{seq:04d}"
