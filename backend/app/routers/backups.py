from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, require_role
from app.vault import encrypt_secret
from app.services.backup_service import run_backup
from app.services import scheduler as sched_module

router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.post("/run", response_model=schemas.BackupRecordOut)
def trigger_backup(payload: schemas.BackupTriggerRequest, background_tasks: BackgroundTasks,
                    db: Session = Depends(get_db),
                    user: models.User = Depends(require_role("admin", "operator"))):
    device = db.query(models.Device).filter(models.Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Run synchronously - UCS backups typically complete in well under a minute,
    # and the caller needs the resulting record immediately for the UI.
    record = run_backup(
        db, device, triggered_by=user.username, trigger_type="manual",
        push_remote=payload.push_remote, remote_host=payload.remote_host,
        remote_user=payload.remote_user, remote_password=payload.remote_password,
        remote_path=payload.remote_path,
    )
    return record


@router.get("/history", response_model=list[schemas.BackupRecordOut])
def backup_history(device_id: int = None, limit: int = 100, db: Session = Depends(get_db),
                    user: models.User = Depends(get_current_user)):
    q = db.query(models.BackupRecord)
    if device_id:
        q = q.filter(models.BackupRecord.device_id == device_id)
    return q.order_by(models.BackupRecord.started_at.desc()).limit(limit).all()


@router.get("/{record_id}/download")
def download_backup(record_id: int, db: Session = Depends(get_db),
                     user: models.User = Depends(get_current_user)):
    record = db.query(models.BackupRecord).filter(models.BackupRecord.id == record_id).first()
    if not record or not record.local_path or not os.path.exists(record.local_path):
        raise HTTPException(status_code=404, detail="Backup file not found")
    return FileResponse(record.local_path, filename=record.filename,
                         media_type="application/octet-stream")


# ---------- Schedules ----------
@router.post("/schedules", response_model=schemas.BackupScheduleOut)
def create_schedule(payload: schemas.BackupScheduleCreate, db: Session = Depends(get_db),
                     user: models.User = Depends(require_role("admin", "operator"))):
    device = db.query(models.Device).filter(models.Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    sched = models.BackupSchedule(
        device_id=payload.device_id,
        cron_expression=payload.cron_expression,
        remote_push_enabled=payload.remote_push_enabled,
        remote_host=payload.remote_host or "",
        remote_user=payload.remote_user or "",
        remote_password_enc=encrypt_secret(payload.remote_password) if payload.remote_password else "",
        remote_path=payload.remote_path or "/backups/f5",
        retain_count=payload.retain_count,
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)

    sched_module.add_or_update_job(sched)

    db.add(models.AuditLog(username=user.username, action="BACKUP_SCHEDULE_CREATE", target=device.name))
    db.commit()
    return sched


@router.get("/schedules", response_model=list[schemas.BackupScheduleOut])
def list_schedules(device_id: int = None, db: Session = Depends(get_db),
                    user: models.User = Depends(get_current_user)):
    q = db.query(models.BackupSchedule)
    if device_id:
        q = q.filter(models.BackupSchedule.device_id == device_id)
    return q.all()


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db),
                     user: models.User = Depends(require_role("admin", "operator"))):
    sched = db.query(models.BackupSchedule).filter(models.BackupSchedule.id == schedule_id).first()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    sched_module.remove_job(schedule_id)
    db.delete(sched)
    db.commit()
    return {"detail": "Schedule deleted"}


@router.post("/schedules/{schedule_id}/toggle", response_model=schemas.BackupScheduleOut)
def toggle_schedule(schedule_id: int, db: Session = Depends(get_db),
                     user: models.User = Depends(require_role("admin", "operator"))):
    sched = db.query(models.BackupSchedule).filter(models.BackupSchedule.id == schedule_id).first()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    sched.is_enabled = not sched.is_enabled
    db.commit()
    db.refresh(sched)
    if sched.is_enabled:
        sched_module.add_or_update_job(sched)
    else:
        sched_module.remove_job(schedule_id)
    return sched
