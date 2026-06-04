from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.operation_log import OperationLog

router = APIRouter(prefix="/api/operation-logs", tags=["operation-logs"])


@router.get("")
def list_logs(db: Session = Depends(get_db)):
    return db.query(OperationLog).order_by(OperationLog.created_at.desc()).limit(200).all()
