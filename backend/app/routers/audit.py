from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.auth import require_role

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_log(limit: int = 200, db: Session = Depends(get_db),
                    admin: models.User = Depends(require_role("admin"))):
    rows = (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "timestamp": r.timestamp, "username": r.username,
            "action": r.action, "target": r.target, "detail": r.detail, "success": r.success,
        }
        for r in rows
    ]
