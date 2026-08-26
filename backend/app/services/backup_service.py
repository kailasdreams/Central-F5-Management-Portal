import os
import datetime
import paramiko
from scp import SCPClient
from sqlalchemy.orm import Session

from app.config import settings
from app import models
from app.vault import decrypt_secret
from app.services.f5_client import F5Client, F5ClientError


class BackupServiceError(Exception):
    pass


def _timestamped_filename(device_name: str) -> str:
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in device_name)
    return f"{safe_name}_{ts}.ucs"


def run_backup(db: Session, device: models.Device, triggered_by: str, trigger_type: str,
                push_remote: bool = False, remote_host: str = None, remote_user: str = None,
                remote_password: str = None, remote_path: str = None) -> models.BackupRecord:
    """Executes a full UCS backup cycle for one device and records history."""
    filename = _timestamped_filename(device.name)
    record = models.BackupRecord(
        device_id=device.id,
        filename=filename,
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        status="running",
        started_at=datetime.datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        username = decrypt_secret(device.username_enc)
        password = decrypt_secret(device.password_enc)
        client = F5Client(device.mgmt_ip, device.https_port, username, password)

        client.create_ucs(filename)
        ok = client.wait_for_ucs(filename, poll_interval=5, max_wait=600)
        if not ok:
            raise BackupServiceError("Timed out waiting for UCS file to be generated on device.")

        local_path = os.path.join(settings.BACKUP_STORAGE_DIR, filename)
        size = client.download_ucs(filename, local_path)

        record.local_path = local_path
        record.size_bytes = size
        record.status = "success"

        if push_remote:
            target_host = remote_host or settings.DEFAULT_REMOTE_BACKUP_HOST
            target_user = remote_user or settings.DEFAULT_REMOTE_BACKUP_USER
            target_path = remote_path or settings.DEFAULT_REMOTE_BACKUP_PATH
            if not target_host or not target_user or not remote_password:
                raise BackupServiceError(
                    "Remote push requested but host/user/password not fully provided."
                )
            _scp_push(local_path, target_host, target_user, remote_password, target_path, filename)
            record.remote_pushed = True

    except (F5ClientError, BackupServiceError, Exception) as e:
        record.status = "failed"
        record.error_detail = str(e)
    finally:
        record.completed_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(record)

    return record


def _scp_push(local_path: str, host: str, user: str, password: str, remote_dir: str, filename: str):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname=host, username=user, password=password, timeout=15)
        ssh.exec_command(f"mkdir -p {remote_dir}")
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(local_path, remote_path=f"{remote_dir.rstrip('/')}/{filename}")
    except Exception as e:
        raise BackupServiceError(f"SCP push to {host} failed: {e}")
    finally:
        ssh.close()


def enforce_retention(db: Session, device_id: int, retain_count: int):
    """Deletes oldest local backup files beyond retain_count for a device."""
    records = (
        db.query(models.BackupRecord)
        .filter(models.BackupRecord.device_id == device_id, models.BackupRecord.status == "success")
        .order_by(models.BackupRecord.started_at.desc())
        .all()
    )
    for old in records[retain_count:]:
        if old.local_path and os.path.exists(old.local_path):
            try:
                os.remove(old.local_path)
            except OSError:
                pass
        db.delete(old)
    db.commit()
