"""
APScheduler-based cron scheduler for automatic device backups.
Schedules are persisted in the BackupSchedule table; this module keeps the
live in-memory scheduler jobs in sync with that table.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app import models
from app.vault import decrypt_secret
from app.services.backup_service import run_backup, enforce_retention

scheduler = BackgroundScheduler()


def _job_id(schedule_id: int) -> str:
    return f"backup_schedule_{schedule_id}"


def _run_scheduled_backup(schedule_id: int):
    db = SessionLocal()
    try:
        sched = db.query(models.BackupSchedule).filter(models.BackupSchedule.id == schedule_id).first()
        if not sched or not sched.is_enabled:
            return
        device = db.query(models.Device).filter(models.Device.id == sched.device_id).first()
        if not device or not device.is_active:
            return

        remote_password = decrypt_secret(sched.remote_password_enc) if sched.remote_password_enc else None

        run_backup(
            db, device, triggered_by="scheduler", trigger_type="auto",
            push_remote=sched.remote_push_enabled,
            remote_host=sched.remote_host, remote_user=sched.remote_user,
            remote_password=remote_password, remote_path=sched.remote_path,
        )
        enforce_retention(db, device.id, sched.retain_count)
    finally:
        db.close()


def add_or_update_job(schedule: models.BackupSchedule):
    job_id = _job_id(schedule.id)
    scheduler.add_job(
        _run_scheduled_backup,
        trigger=CronTrigger.from_crontab(schedule.cron_expression),
        args=[schedule.id],
        id=job_id,
        replace_existing=True,
    )


def remove_job(schedule_id: int):
    job_id = _job_id(schedule_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def load_all_schedules():
    """Called at startup to (re)register all enabled schedules from the DB."""
    db = SessionLocal()
    try:
        schedules = db.query(models.BackupSchedule).filter(models.BackupSchedule.is_enabled == True).all()  # noqa: E712
        for s in schedules:
            add_or_update_job(s)
    finally:
        db.close()


def start():
    if not scheduler.running:
        load_all_schedules()
        scheduler.start()
