import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operator"


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Devices ----------
class DeviceCreate(BaseModel):
    name: str
    mgmt_ip: str
    https_port: int = 443
    ssh_port: int = 22
    site: str = ""
    device_type: str = "F5_BIGIP"
    ha_role: str = "standalone"
    username: str
    password: str
    tags: str = ""
    notes: str = ""


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    mgmt_ip: Optional[str] = None
    https_port: Optional[int] = None
    ssh_port: Optional[int] = None
    site: Optional[str] = None
    ha_role: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class DeviceOut(BaseModel):
    id: int
    name: str
    mgmt_ip: str
    https_port: int
    ssh_port: int
    site: str
    device_type: str
    ha_role: str
    is_active: bool
    tags: str
    notes: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class DeviceTestResult(BaseModel):
    device_id: int
    reachable: bool
    detail: str
    hostname: Optional[str] = None
    version: Optional[str] = None


# ---------- Backups ----------
class BackupTriggerRequest(BaseModel):
    device_id: int
    push_remote: bool = False
    remote_host: Optional[str] = None
    remote_user: Optional[str] = None
    remote_password: Optional[str] = None
    remote_path: Optional[str] = None


class BackupRecordOut(BaseModel):
    id: int
    device_id: int
    filename: Optional[str]
    trigger_type: str
    triggered_by: str
    status: str
    remote_pushed: bool
    error_detail: str
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime]
    size_bytes: int

    class Config:
        from_attributes = True


class BackupScheduleCreate(BaseModel):
    device_id: int
    cron_expression: str = Field(..., description="Standard 5-field cron, e.g. '0 2 * * *'")
    remote_push_enabled: bool = False
    remote_host: Optional[str] = ""
    remote_user: Optional[str] = ""
    remote_password: Optional[str] = ""
    remote_path: Optional[str] = "/backups/f5"
    retain_count: int = 14


class BackupScheduleOut(BaseModel):
    id: int
    device_id: int
    cron_expression: str
    remote_push_enabled: bool
    remote_path: str
    retain_count: int
    is_enabled: bool

    class Config:
        from_attributes = True


# ---------- Logs ----------
class LogSummaryRequest(BaseModel):
    device_id: int
    log_file: str = "ltm"   # ltm | gtm | audit | secure
    lines: int = 500


class LogEntry(BaseModel):
    raw: str
    timestamp: Optional[str] = None
    severity: Optional[str] = None
    process: Optional[str] = None
    message: Optional[str] = None


class LogSummaryResponse(BaseModel):
    device_id: int
    log_file: str
    total_lines: int
    severity_counts: dict
    process_counts: dict
    entries: List[LogEntry]


# ---------- CLI structured runner ----------
class CommandRunRequest(BaseModel):
    device_id: int
    command: str


class CommandRunResponse(BaseModel):
    device_id: int
    command: str
    output: str
    success: bool
