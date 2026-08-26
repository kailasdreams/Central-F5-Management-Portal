import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app import models, schemas
from app.auth import get_current_user, require_role
from app.config import settings
from app.vault import decrypt_secret
from app.services.ssh_service import open_shell_channel, run_command, SSHServiceError

router = APIRouter(prefix="/api/cli", tags=["cli"])

# A small allowlist-style guard for the structured runner - blocks obviously
# destructive raw shell escapes while still allowing normal tmsh usage.
BLOCKED_TOKENS = ["rm -rf", "; rm", "&& rm", "mkfs", ":(){:|:&};:"]


@router.post("/run", response_model=schemas.CommandRunResponse)
def run_structured_command(payload: schemas.CommandRunRequest, db: Session = Depends(get_db),
                            user: models.User = Depends(require_role("admin", "operator"))):
    device = db.query(models.Device).filter(models.Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    cmd = payload.command.strip()
    if any(tok in cmd for tok in BLOCKED_TOKENS):
        raise HTTPException(status_code=400, detail="Command blocked by safety policy.")

    username = decrypt_secret(device.username_enc)
    password = decrypt_secret(device.password_enc)

    try:
        output = run_command(device.mgmt_ip, device.ssh_port, username, password, cmd)
        success = True
    except SSHServiceError as e:
        output = str(e)
        success = False

    db.add(models.AuditLog(username=user.username, action="CLI_COMMAND", target=device.name,
                            detail=cmd, success=success))
    db.commit()

    return schemas.CommandRunResponse(device_id=device.id, command=cmd, output=output, success=success)


def _authenticate_ws_token(token: str) -> models.User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid user")
        return user
    finally:
        db.close()


@router.websocket("/ws/{device_id}")
async def cli_terminal_ws(websocket: WebSocket, device_id: int, token: str = Query(...)):
    """
    Interactive SSH terminal bridge for xterm.js frontends.
    Frontend protocol (JSON text frames):
      -> {"type": "resize", "cols": 120, "rows": 32}
      -> {"type": "input", "data": "ls\\n"}
      <- raw text frames = terminal output
    """
    await websocket.accept()

    try:
        user = _authenticate_ws_token(token)
    except HTTPException as e:
        await websocket.send_text(f"\r\n[AUTH ERROR] {e.detail}\r\n")
        await websocket.close()
        return

    db = SessionLocal()
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        await websocket.send_text("\r\n[ERROR] Device not found\r\n")
        await websocket.close()
        db.close()
        return

    username = decrypt_secret(device.username_enc)
    password = decrypt_secret(device.password_enc)

    try:
        client, channel = open_shell_channel(device.mgmt_ip, device.ssh_port, username, password)
    except SSHServiceError as e:
        await websocket.send_text(f"\r\n[SSH ERROR] {e}\r\n")
        await websocket.close()
        db.close()
        return

    db.add(models.AuditLog(username=user.username, action="CLI_SESSION_START", target=device.name))
    db.commit()

    async def read_from_ssh():
        loop = asyncio.get_event_loop()
        while True:
            try:
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if not data:
                        break
                    await websocket.send_text(data.decode(errors="replace"))
                elif channel.closed:
                    break
                else:
                    await asyncio.sleep(0.05)
            except Exception:
                break

    ssh_reader_task = asyncio.ensure_future(read_from_ssh())

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                payload = json.loads(msg)
            except json.JSONDecodeError:
                continue

            if payload.get("type") == "input":
                channel.send(payload.get("data", ""))
            elif payload.get("type") == "resize":
                try:
                    channel.resize_pty(width=int(payload.get("cols", 120)),
                                        height=int(payload.get("rows", 32)))
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        ssh_reader_task.cancel()
        try:
            channel.close()
            client.close()
        except Exception:
            pass
        db.add(models.AuditLog(username=user.username, action="CLI_SESSION_END", target=device.name))
        db.commit()
        db.close()
