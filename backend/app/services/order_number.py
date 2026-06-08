from datetime import date
from sqlalchemy.orm import Session


def next_order_number(db: Session, model, prefix: str) -> str:
    """生成下一个单号: XXYYYYMMDDNNNN"""
    today = date.today().strftime("%Y%m%d")
    full_prefix = f"{prefix}{today}"
    last = (
        db.query(model)
        .filter(model.order_number.like(f"{full_prefix}%"))
        .order_by(model.id.desc())
        .first()
    )
    if last and last.order_number and len(last.order_number) == 14:
        seq = int(last.order_number[-4:]) + 1
    else:
        seq = 1
    return f"{full_prefix}{seq:04d}"
