from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Enum, JSON,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship
from backend.database import Base
import enum


# --- Enums ---

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class AuthMethod(str, enum.Enum):
    PLAIN = "plain"
    APP_PASSWORD = "app_password"
    API_KEY = "api_key"


class ProviderStatus(str, enum.Enum):
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
    LOCKED = "locked"      # expired / admin-locked
    SUSPENDED = "suspended"  # user suspended


class MailStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


class ProxyProtocol(str, enum.Enum):
    SOCKS5 = "socks5"
    HTTP = "http"
    DIRECT = "direct"  # local IP binding (no proxy)


# --- Users ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)

    # Limits (admin-configurable per user)
    max_relays = Column(Integer, nullable=False, default=1)
    relay_expiry_days = Column(Integer, nullable=True)  # None = no expiry

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    providers = relationship("Provider", back_populates="user", lazy="dynamic")


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(100), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(100), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# --- Proxies ---

class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    protocol = Column(Enum(ProxyProtocol), nullable=False, default=ProxyProtocol.DIRECT)
    host = Column(String(255), nullable=False)  # IP or hostname; for DIRECT = local bind IP
    port = Column(Integer, nullable=True)  # null for DIRECT
    username = Column(String(255), nullable=True)
    password_encrypted = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    current_assignments = Column(Integer, nullable=False, default=0)  # for round-robin balancing
    provider_types = Column(JSON, nullable=True)  # ["gmail", "seznam"] or null = all
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    providers = relationship("Provider", back_populates="proxy")


# --- Providers (now per-user) ---

class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    proxy_id = Column(Integer, ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True)

    name = Column(String(100), nullable=False)
    provider_type = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    smtp_host = Column(String(255), nullable=False)
    smtp_port = Column(Integer, nullable=False, default=587)
    tls_mode = Column(String(20), nullable=False, default="starttls")
    auth_method = Column(Enum(AuthMethod), nullable=False, default=AuthMethod.PLAIN)
    username = Column(String(255), nullable=True)
    password_encrypted = Column(Text, nullable=True)

    priority = Column(Integer, nullable=False, default=10)
    is_default = Column(Boolean, nullable=False, default=False)
    status = Column(Enum(ProviderStatus), nullable=False, default=ProviderStatus.ACTIVE)

    daily_limit = Column(Integer, nullable=True)
    daily_sent = Column(Integer, nullable=False, default=0)
    daily_reset_at = Column(DateTime, nullable=True)

    # Expiration
    expires_at = Column(DateTime, nullable=True)  # null = no expiry
    is_locked = Column(Boolean, nullable=False, default=False)
    locked_reason = Column(String(255), nullable=True)

    last_health_check = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="providers")
    proxy = relationship("Proxy", back_populates="providers")

    __table_args__ = (
        Index("ix_providers_user_status", "user_id", "status"),
    )


# --- Access control (per-user) ---

class AllowedClient(Base):
    __tablename__ = "allowed_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    client_type = Column(String(20), nullable=False)
    ip_address = Column(String(45), nullable=True)
    ip_cidr = Column(String(49), nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password_hash = Column(String(255), nullable=True)
    smtp_password_plain = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    provider = relationship("Provider", backref="clients")


# --- Global daily limits per provider type (admin-managed) ---

class ProviderTypeLimit(Base):
    __tablename__ = "provider_type_limits"

    provider_type = Column(String(50), primary_key=True)  # gmail, outlook, seznam, custom, ...
    daily_limit = Column(Integer, nullable=False, default=100)


# --- Mail log (per-user) ---

class MailLog(Base):
    __tablename__ = "mail_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    queue_id = Column(String(20), nullable=True)
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True)
    provider_id = Column(Integer, nullable=True)
    provider_name = Column(String(100), nullable=True)
    proxy_ip = Column(String(45), nullable=True)
    status = Column(Enum(MailStatus), nullable=False, default=MailStatus.QUEUED)
    error_message = Column(Text, nullable=True)
    client_ip = Column(String(45), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# --- Health checks ---

class HealthCheck(Base):
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    is_healthy = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# --- App settings ---

class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
