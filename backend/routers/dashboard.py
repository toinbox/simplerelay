from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from backend.database import get_db
from backend.models import (
    MailLog, MailStatus, Provider, ProviderStatus, HealthCheck, User
)
from backend.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["logs", "dashboard"])


class MailLogOut(BaseModel):
    id: int
    queue_id: str | None
    sender: str
    recipient: str
    subject: str | None
    provider_name: str | None
    status: str
    error_message: str | None
    client_ip: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    sent_today: int
    errors_today: int
    providers_healthy: int
    providers_total: int
    relay_limit: int
    recent_logs: list[MailLogOut]
    provider_health: list[dict]


# --- Logs ---

@router.get("/logs", response_model=list[MailLogOut])
def get_logs(
    status: str | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get mail logs for current user."""
    query = db.query(MailLog).filter(
        MailLog.user_id == user.id
    ).order_by(MailLog.created_at.desc())

    if status:
        query = query.filter(MailLog.status == status)

    return query.offset(offset).limit(limit).all()


# --- Dashboard ---

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dashboard statistics for current user."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    sent_today = db.query(func.count(MailLog.id)).filter(
        MailLog.user_id == user.id,
        MailLog.status == MailStatus.SENT,
        MailLog.created_at >= today_start,
    ).scalar() or 0

    errors_today = db.query(func.count(MailLog.id)).filter(
        MailLog.user_id == user.id,
        MailLog.status.in_([MailStatus.FAILED, MailStatus.BOUNCED]),
        MailLog.created_at >= today_start,
    ).scalar() or 0

    providers = db.query(Provider).filter(Provider.user_id == user.id).all()
    providers_healthy = sum(1 for p in providers if p.status == ProviderStatus.ACTIVE)

    provider_health = []
    for p in providers:
        last_check = db.query(HealthCheck).filter(
            HealthCheck.provider_id == p.id
        ).order_by(HealthCheck.checked_at.desc()).first()

        provider_health.append({
            "id": p.id,
            "name": p.name,
            "email": p.email,
            "status": p.status.value if p.status else "unknown",
            "is_default": p.is_default,
            "is_locked": p.is_locked,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            "daily_sent": p.daily_sent,
            "daily_limit": p.daily_limit,
            "last_check": last_check.checked_at.isoformat() if last_check else None,
            "response_time_ms": last_check.response_time_ms if last_check else None,
        })

    recent_logs = db.query(MailLog).filter(
        MailLog.user_id == user.id
    ).order_by(MailLog.created_at.desc()).limit(10).all()

    return DashboardStats(
        sent_today=sent_today,
        errors_today=errors_today,
        providers_healthy=providers_healthy,
        providers_total=len(providers),
        relay_limit=user.max_relays,
        recent_logs=recent_logs,
        provider_health=provider_health,
    )


# --- Setup status ---

@router.get("/setup-status")
def setup_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check if initial setup is needed for current user."""
    provider_count = db.query(func.count(Provider.id)).filter(
        Provider.user_id == user.id
    ).scalar() or 0

    return {
        "needs_setup": provider_count == 0,
        "has_providers": provider_count > 0,
        "relay_limit": user.max_relays,
        "relay_count": provider_count,
    }
