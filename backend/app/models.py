import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="operator")  # admin | operator | viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    mgmt_ip = Column(String(64), nullable=False)
    https_port = Column(Integer, default=443)
    ssh_port = Column(Integer, default=22)
    site = Column(String(64))          # DC_SIFY / DR_BCP / DC_CHAND
    device_type = Column(String(32), default="F5_BIGIP")
    ha_role = Column(String(32), default="standalone")  # active/standby/standalone
    username_enc = Column(Text, nullable=False)   # encrypted
    password_enc = Column(Text, nullable=False)   # encrypted
    is_active = Column(Boolean, default=True)
    tags = Column(String(255), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    backups = relationship("BackupRecord", back_populates="device", cascade="all,delete")
    schedules = relationship("BackupSchedule", back_populates="device", cascade="all,delete")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    username = Column(String(64))
    action = Column(String(64))
    target = Column(String(128))
    detail = Column(Text, default="")
    success = Column(Boolean, default=True)


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    filename = Column(String(255))
    local_path = Column(String(512))
    triggered_by = Column(String(64))          # username or "scheduler"
    trigger_type = Column(String(16))           # manual | auto
    status = Column(String(32), default="pending")  # pending|running|success|failed
    remote_pushed = Column(Boolean, default=False)
    error_detail = Column(Text, default="")
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    size_bytes = Column(Integer, default=0)

    device = relationship("Device", back_populates="backups")


class BackupSchedule(Base):
    __tablename__ = "backup_schedules"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    cron_expression = Column(String(64))   # e.g. "0 2 * * *" = daily 2AM
    remote_push_enabled = Column(Boolean, default=False)
    remote_host = Column(String(128), default="")
    remote_user = Column(String(64), default="")
    remote_password_enc = Column(Text, default="")
    remote_path = Column(String(255), default="/backups/f5")
    retain_count = Column(Integer, default=14)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    device = relationship("Device", back_populates="schedules")
