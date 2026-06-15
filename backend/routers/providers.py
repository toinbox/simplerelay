import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from backend.database import get_db
from backend.models import Provider, ProviderStatus, AuthMethod, User
from backend.services.provider_presets import (
    PROVIDER_PRESETS, detect_provider, get_preset, get_provider_note,
    guess_smtp_from_mx,
)
from backend.services.postfix_config import write_and_reload
from backend.services.dns_checker import check_domain
from backend.services.crypto import encrypt_password
from backend.services.auth import get_current_user
from backend.routers.admin import assign_proxy_round_robin, release_proxy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/providers", tags=["providers"])


class ProviderCreate(BaseModel):
    provider_type: str
    email: str
    name: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    tls_mode: str = "starttls"
    auth_method: str = "plain"
    username: str | None = None
    password: str | None = None
    is_default: bool = False
    daily_limit: int | None = None


class ProviderOut(BaseModel):
    id: int
    name: str
    provider_type: str
    email: str
    smtp_host: str
    smtp_port: int
    tls_mode: str
    auth_method: str
    is_default: bool
    status: str
    daily_limit: int | None
    daily_sent: int
    is_locked: bool
    locked_reason: str | None
    expires_at: datetime | None
    last_error: str | None

    class Config:
        from_attributes = True


class DetectRequest(BaseModel):
    email: str


class DetectResponse(BaseModel):
    provider_type: str | None
    provider_name: str | None
    preset: dict | None


class DnsCheckRequest(BaseModel):
    domain: str
    provider_type: str


# --- Endpoints ---

@router.get("/presets")
def list_presets():
    """List available provider presets."""
    return {
        key: {
            "name": preset["name"],
            "smtp_host": preset["smtp_host"],
            "smtp_port": preset["smtp_port"],
            "tls_mode": preset["tls_mode"],
            "auth_methods": preset["auth_methods"],
            "daily_limit": preset.get("daily_limit"),
            "app_password_url": preset.get("app_password_url"),
        }
        for key, preset in PROVIDER_PRESETS.items()
    }


@router.post("/detect", response_model=DetectResponse)
def detect_email_provider(req: DetectRequest):
    """Auto-detect provider from email address."""
    provider_type = detect_provider(req.email)
    if provider_type:
        preset = get_preset(provider_type)
        return DetectResponse(
            provider_type=provider_type,
            provider_name=preset["name"],
            preset=preset,
        )
    # Provider not in presets - try to guess SMTP from MX/DNS
    guessed = guess_smtp_from_mx(req.email)
    if guessed:
        return DetectResponse(
            provider_type="custom",
            provider_name=None,
            preset=guessed,
        )
    return DetectResponse(provider_type=None, provider_name=None, preset=None)


@router.get("/", response_model=list[ProviderOut])
def list_providers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List providers for current user."""
    return db.query(Provider).filter(
        Provider.user_id == user.id
    ).order_by(Provider.priority).all()


@router.post("/", response_model=ProviderOut)
def create_provider(
    data: ProviderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add a new provider for current user."""
    # Check relay limit
    current_count = db.query(func.count(Provider.id)).filter(
        Provider.user_id == user.id
    ).scalar() or 0
    if current_count >= user.max_relays:
        raise HTTPException(
            400,
            f"Relay limit reached ({user.max_relays}). Contact admin for more."
        )

    # Apply preset defaults
    preset = get_preset(data.provider_type)
    if preset:
        if not data.smtp_host:
            data.smtp_host = preset["smtp_host"]
        if not data.smtp_port:
            data.smtp_port = preset["smtp_port"]
        if not data.name:
            data.name = preset["name"]
        if data.daily_limit is None:
            data.daily_limit = preset.get("daily_limit")

    # Check duplicate email globally
    existing = db.query(Provider).filter(Provider.email == data.email).first()
    if existing:
        raise HTTPException(400, f"Provider for {data.email} already exists")

    # If setting as default, unset other defaults for this user
    if data.is_default:
        db.query(Provider).filter(
            Provider.user_id == user.id
        ).update({Provider.is_default: False})

    # Calculate expiration
    expires_at = None
    if user.relay_expiry_days and user.relay_expiry_days > 0:
        expires_at = datetime.utcnow() + timedelta(days=user.relay_expiry_days)

    # Assign proxy (round-robin by provider type)
    proxy = assign_proxy_round_robin(db, data.provider_type)

    provider = Provider(
        user_id=user.id,
        proxy_id=proxy.id if proxy else None,
        name=data.name or data.email,
        provider_type=data.provider_type,
        email=data.email,
        smtp_host=data.smtp_host,
        smtp_port=data.smtp_port or 587,
        tls_mode=data.tls_mode,
        auth_method=AuthMethod(data.auth_method),
        username=data.username or data.email,
        password_encrypted=encrypt_password(data.password) if data.password else None,
        is_default=data.is_default,
        daily_limit=data.daily_limit,
        expires_at=expires_at,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)

    # Regenerate Postfix config — log error + set last_error on provider
    postfix_ok = _reload_postfix(db, provider)

    result = ProviderOut.model_validate(provider).model_dump()
    if not postfix_ok:
        result["warning"] = "Provider created but Postfix reload failed. Check server logs."
    return result


@router.delete("/{provider_id}")
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a provider."""
    provider = db.query(Provider).filter(
        Provider.id == provider_id,
        Provider.user_id == user.id,
    ).first()
    if not provider:
        raise HTTPException(404, "Provider not found")

    # Release proxy assignment
    if provider.proxy_id:
        release_proxy(db, provider.proxy_id)

    db.delete(provider)
    db.commit()

    # Regenerate Postfix config
    try:
        write_and_reload(db)
    except Exception as e:
        logger.error(f"Postfix reload failed after deleting provider {provider_id}: {e}", exc_info=True)
        return {"deleted": True, "warning": "Postfix reload failed. Check server logs."}

    return {"deleted": True}


@router.post("/{provider_id}/test")
async def test_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Test SMTP connection to a provider."""
    from backend.services.health_checker import check_provider

    provider = db.query(Provider).filter(
        Provider.id == provider_id,
        Provider.user_id == user.id,
    ).first()
    if not provider:
        raise HTTPException(404, "Provider not found")

    healthy, response_time, error = await check_provider(provider)
    return {
        "healthy": healthy,
        "response_time_ms": response_time,
        "error": error,
    }


@router.post("/dns-check")
def dns_check(req: DnsCheckRequest):
    """Check DNS records for a domain."""
    results = check_domain(req.domain, req.provider_type)
    return [
        {
            "record_type": r.record_type,
            "status": r.status,
            "current_value": r.current_value,
            "suggestion": r.suggestion,
        }
        for r in results
    ]


def _reload_postfix(db: Session, provider: Provider) -> bool:
    """Reload Postfix config. Returns True on success, False on failure.
    On failure, logs error and sets provider.last_error.
    """
    try:
        write_and_reload(db)
        return True
    except Exception as e:
        error_msg = f"Postfix reload failed: {e}"
        logger.error(f"{error_msg} (provider {provider.id})", exc_info=True)
        try:
            provider.last_error = error_msg
            db.commit()
        except Exception as db_e:
            logger.error(f"Failed to write error to DB: {db_e}", exc_info=True)
        return False