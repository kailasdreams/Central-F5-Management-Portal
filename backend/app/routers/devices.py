from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, require_role
from app.vault import encrypt_secret, decrypt_secret
from app.services.f5_client import F5Client, F5ClientError

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.post("", response_model=schemas.DeviceOut)
def create_device(payload: schemas.DeviceCreate, db: Session = Depends(get_db),
                   user: models.User = Depends(require_role("admin", "operator"))):
    device = models.Device(
        name=payload.name,
        mgmt_ip=payload.mgmt_ip,
        https_port=payload.https_port,
        ssh_port=payload.ssh_port,
        site=payload.site,
        device_type=payload.device_type,
        ha_role=payload.ha_role,
        username_enc=encrypt_secret(payload.username),
        password_enc=encrypt_secret(payload.password),
        tags=payload.tags,
        notes=payload.notes,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    db.add(models.AuditLog(username=user.username, action="DEVICE_CREATE", target=device.name))
    db.commit()
    return device


@router.get("", response_model=list[schemas.DeviceOut])
def list_devices(site: str = None, db: Session = Depends(get_db),
                  user: models.User = Depends(get_current_user)):
    q = db.query(models.Device)
    if site:
        q = q.filter(models.Device.site == site)
    return q.order_by(models.Device.name).all()


@router.get("/{device_id}", response_model=schemas.DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.put("/{device_id}", response_model=schemas.DeviceOut)
def update_device(device_id: int, payload: schemas.DeviceUpdate, db: Session = Depends(get_db),
                   user: models.User = Depends(require_role("admin", "operator"))):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    data = payload.dict(exclude_unset=True)
    if "username" in data:
        device.username_enc = encrypt_secret(data.pop("username"))
    if "password" in data:
        device.password_enc = encrypt_secret(data.pop("password"))
    for k, v in data.items():
        setattr(device, k, v)

    db.commit()
    db.refresh(device)
    db.add(models.AuditLog(username=user.username, action="DEVICE_UPDATE", target=device.name))
    db.commit()
    return device


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db),
                   user: models.User = Depends(require_role("admin"))):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
    db.add(models.AuditLog(username=user.username, action="DEVICE_DELETE", target=device.name))
    db.commit()
    return {"detail": "Device deleted"}


@router.post("/{device_id}/test", response_model=schemas.DeviceTestResult)
def test_device(device_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    username = decrypt_secret(device.username_enc)
    password = decrypt_secret(device.password_enc)
    client = F5Client(device.mgmt_ip, device.https_port, username, password)
    try:
        info = client.test_connection()
        return schemas.DeviceTestResult(
            device_id=device.id, reachable=True, detail="Connection successful",
            hostname=info.get("hostname"), version=info.get("version"),
        )
    except F5ClientError as e:
        return schemas.DeviceTestResult(device_id=device.id, reachable=False, detail=str(e))


@router.get("/{device_id}/gui-link")
def gui_launch_link(device_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Returns the direct TMUI URL for the device. F5's TMUI sends its own
    X-Frame-Options/CSP headers, so it cannot be embedded in an iframe without
    modifying the device's HTTPD config (not recommended). We provide a
    secure launch link instead, opened in a new browser tab."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    url = f"https://{device.mgmt_ip}:{device.https_port}/tmui/login.jsp"
    db.add(models.AuditLog(username=user.username, action="GUI_LAUNCH", target=device.name))
    db.commit()
    return {"device_id": device.id, "gui_url": url}
