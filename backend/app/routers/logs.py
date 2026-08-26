from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.vault import decrypt_secret
from app.services.ssh_service import tail_log_file, SSHServiceError
from app.services.log_service import LOG_FILE_PATHS, parse_log_text, summarize

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.post("/summary", response_model=schemas.LogSummaryResponse)
def get_log_summary(payload: schemas.LogSummaryRequest, db: Session = Depends(get_db),
                     user: models.User = Depends(get_current_user)):
    device = db.query(models.Device).filter(models.Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    log_path = LOG_FILE_PATHS.get(payload.log_file)
    if not log_path:
        raise HTTPException(status_code=400, detail=f"Unknown log_file '{payload.log_file}'. "
                                                       f"Choose from {list(LOG_FILE_PATHS)}")

    username = decrypt_secret(device.username_enc)
    password = decrypt_secret(device.password_enc)

    try:
        raw_text = tail_log_file(device.mgmt_ip, device.ssh_port, username, password,
                                  log_path, lines=payload.lines)
    except SSHServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    entries = parse_log_text(raw_text)
    summary = summarize(entries)

    db.add(models.AuditLog(username=user.username, action="LOG_PULL", target=device.name,
                            detail=payload.log_file))
    db.commit()

    return schemas.LogSummaryResponse(
        device_id=device.id,
        log_file=payload.log_file,
        total_lines=len(entries),
        severity_counts=summary["severity_counts"],
        process_counts=summary["process_counts"],
        entries=[schemas.LogEntry(**e) for e in entries[-200:]],  # cap payload size
    )
