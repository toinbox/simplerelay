from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from backend.database import get_db
from backend.models import (
    User, UserRole, Provider, ProviderStatus, Proxy, ProxyProtocol,
    MailLog, MailStatus, ProviderTypeLimit,
)
from backend.services.auth import get_current_admin, hash_password
from backend.services.crypto import encrypt_password

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================
# USER MANAGEMENT
# ============================================================

class UserListOut(BaseModel):
    id: int
    email: str
    name: str | None
    role: str
    is_active: bool
    max_relays: int
    relay_expiry_days: int | None
    relay_count: int = 0
    created_at: datetime
    last_login: datetime | None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = None
    max_relays: int | None = None
    relay_expiry_days: int | None = None  # 0 or None = no expiry
    name: str | None = None


@router.get("/users", response_model=list[UserListOut])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List all users with relay counts."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        relay_count = db.query(func.count(Provider.id)).filter(
            Provider.user_id == u.id
        ).scalar() or 0
        out = UserListOut.model_validate(u)
        out.relay_count = relay_count
        result.append(out)
    return result


@router.patch("/users/{user_id}", response_model=UserListOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Update user settings (limits, role, active status)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Prevent self-demotion from admin
    if user.id == admin.id and data.role and data.role != "admin":
        raise HTTPException(400, "Cannot remove your own admin role")

    if data.is_active is not None:
        user.is_active = data.is_active
        # If deactivating, lock all their relays
        if not data.is_active:
            db.query(Provider).filter(Provider.user_id == user.id).update({
                Provider.status: ProviderStatus.SUSPENDED,
                Provider.locked_reason: "Account deactivated",
            })

    if data.role is not None:
        user.role = UserRole(data.role)

    if data.max_relays is not None:
        user.max_relays = data.max_relays

    if data.relay_expiry_days is not None:
        user.relay_expiry_days = data.relay_expiry_days if data.relay_expiry_days > 0 else None

    if data.name is not None:
        user.name = data.name

    db.commit()
    db.refresh(user)

    relay_count = db.query(func.count(Provider.id)).filter(
        Provider.user_id == user.id
    ).scalar() or 0
    out = UserListOut.model_validate(user)
    out.relay_count = relay_count
    return out


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Delete a user and all their data."""
    if user_id == admin.id:
        raise HTTPException(400, "Cannot delete yourself")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    db.delete(user)  # CASCADE deletes providers, clients, etc.
    db.commit()
    return {"deleted": True}


# ============================================================
# PROXY MANAGEMENT
# ============================================================

class ProxyCreate(BaseModel):
    name: str
    protocol: str = "direct"  # direct, socks5, http
    host: str  # IP address
    port: int | None = None
    username: str | None = None
    password: str | None = None
    provider_types: list[str] | None = None  # ["gmail", "seznam"] or null = all


class ProxyOut(BaseModel):
    id: int
    name: str
    protocol: str
    host: str
    port: int | None
    username: str | None
    is_active: bool
    current_assignments: int
    provider_types: list[str] | None
    created_at: datetime

    class Config:
        from_attributes = True


class ProxyUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    provider_types: list[str] | None = None


@router.get("/proxies", response_model=list[ProxyOut])
def list_proxies(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List all proxy/IP entries."""
    return db.query(Proxy).order_by(Proxy.id).all()


@router.post("/proxies", response_model=ProxyOut)
def create_proxy(
    data: ProxyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Add a new proxy/outbound IP."""
    proxy = Proxy(
        name=data.name,
        protocol=ProxyProtocol(data.protocol),
        host=data.host,
        port=data.port,
        username=data.username,
        password_encrypted=encrypt_password(data.password) if data.password else None,
        is_active=True,
        provider_types=data.provider_types,
    )
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


@router.patch("/proxies/{proxy_id}", response_model=ProxyOut)
def update_proxy(
    proxy_id: int,
    data: ProxyUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Update a proxy entry."""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(404, "Proxy not found")

    if data.name is not None:
        proxy.name = data.name
    if data.is_active is not None:
        proxy.is_active = data.is_active
    if data.host is not None:
        proxy.host = data.host
    if data.port is not None:
        proxy.port = data.port
    if data.username is not None:
        proxy.username = data.username
    if data.password is not None:
        proxy.password_encrypted = encrypt_password(data.password)
    if data.provider_types is not None:
        proxy.provider_types = data.provider_types if data.provider_types else None

    db.commit()
    db.refresh(proxy)
    return proxy


@router.delete("/proxies/{proxy_id}")
def delete_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Delete a proxy. Providers using it will have proxy_id set to NULL."""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(404, "Proxy not found")

    db.delete(proxy)
    db.commit()
    return {"deleted": True}


@router.post("/proxies/{proxy_id}/test")
async def test_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Test proxy connectivity: check outbound IP + SMTP reachability."""
    import httpx
    import socket
    import time
    from backend.services.crypto import decrypt_password as _decrypt

    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(404, "Proxy not found")

    # Decrypt proxy password
    password = None
    if proxy.password_encrypted:
        try:
            password = _decrypt(proxy.password_encrypted)
        except Exception:
            password = proxy.password_encrypted  # fallback: might be plaintext

    result = {"success": False, "proxy_name": proxy.name}

    # 1. Test HTTP — get outbound IP
    try:
        if proxy.protocol == ProxyProtocol.SOCKS5:
            from urllib.parse import quote
            auth = f"{quote(proxy.username, safe='')}:{quote(password, safe='')}@" if proxy.username else ""
            proxy_url = f"socks5://{auth}{proxy.host}:{proxy.port}"
        else:
            proxy_url = None

        t0 = time.time()
        async with httpx.AsyncClient(proxy=proxy_url, timeout=10) as client:
            resp = await client.get("https://api.ipify.org?format=json")
            data = resp.json()
        latency_ms = int((time.time() - t0) * 1000)

        result["success"] = True
        result["ip"] = data.get("ip", "unknown")
        result["latency_ms"] = latency_ms
    except Exception as e:
        result["error"] = f"HTTP: {str(e)[:150]}"
        return result

    # 2. Test SMTP — try connecting to smtp.gmail.com:587 through proxy
    try:
        has_socks = False
        try:
            import socks
            has_socks = True
        except ImportError:
            pass

        smtp_ok = False
        if has_socks and proxy.protocol == ProxyProtocol.SOCKS5:
            import smtplib
            original = socket.create_connection

            def proxied(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
                s = socks.socksocket()
                s.set_proxy(socks.SOCKS5, proxy.host, proxy.port or 1080,
                            rdns=True, username=proxy.username, password=password)
                if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                    s.settimeout(timeout)
                s.connect(address)
                return s

            socket.create_connection = proxied
            try:
                smtp = smtplib.SMTP("smtp.gmail.com", 587, timeout=10,
                                     local_hostname=f"[{result['ip']}]")
                smtp.ehlo(f"[{result['ip']}]")
                smtp.quit()
                smtp_ok = True
            except Exception as e:
                result["smtp_error"] = str(e)[:150]
            finally:
                socket.create_connection = original
        else:
            smtp_ok = None  # skipped (no SOCKS5)

        result["smtp_ok"] = smtp_ok
    except Exception:
        result["smtp_ok"] = False

    return result


@router.get("/proxy-domains")
def list_proxy_domains(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get unique provider types from all providers — for proxy domain assignment UI."""
    rows = db.query(Provider.provider_type).distinct().all()
    active_types = sorted(set(r[0] for r in rows if r[0]))
    return active_types


# ============================================================
# PROXY ASSIGNMENT (round-robin)
# ============================================================

def assign_proxy_round_robin(db: Session, provider_type: str = None) -> Proxy | None:
    """Pick the active proxy with fewest assignments, filtered by provider type.

    Known providers (gmail, outlook …) only match proxies that explicitly
    list them in provider_types.  Catch-all proxies (provider_types IS NULL)
    are reserved for custom / unknown provider types.
    """
    _KNOWN_PROVIDERS = {"gmail", "outlook", "yahoo", "seznam", "mailcz",
                        "icloud", "amazon_ses", "sendgrid"}

    proxies = db.query(Proxy).filter(
        Proxy.is_active == True
    ).order_by(
        Proxy.current_assignments.asc()
    ).all()

    matching = []
    for p in proxies:
        if p.provider_types is not None and provider_type and provider_type in p.provider_types:
            # Explicit type match — always OK
            matching.append(p)
        elif p.provider_types is None and provider_type not in _KNOWN_PROVIDERS:
            # Catch-all — only for custom / unknown provider types
            matching.append(p)

    if matching:
        proxy = matching[0]
        proxy.current_assignments += 1
        db.flush()
        return proxy

    return None


def release_proxy(db: Session, proxy_id: int):
    """Decrease assignment count when a provider is deleted."""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if proxy and proxy.current_assignments > 0:
        proxy.current_assignments -= 1
        db.flush()


# ============================================================
# ADMIN DASHBOARD STATS
# ============================================================

class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_relays: int
    active_relays: int
    locked_relays: int
    total_proxies: int
    active_proxies: int
    sent_today: int
    errors_today: int


@router.get("/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Global admin statistics."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    return AdminStats(
        total_users=db.query(func.count(User.id)).scalar() or 0,
        active_users=db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0,
        total_relays=db.query(func.count(Provider.id)).scalar() or 0,
        active_relays=db.query(func.count(Provider.id)).filter(
            Provider.status == ProviderStatus.ACTIVE
        ).scalar() or 0,
        locked_relays=db.query(func.count(Provider.id)).filter(
            Provider.status.in_([ProviderStatus.LOCKED, ProviderStatus.SUSPENDED])
        ).scalar() or 0,
        total_proxies=db.query(func.count(Proxy.id)).scalar() or 0,
        active_proxies=db.query(func.count(Proxy.id)).filter(Proxy.is_active == True).scalar() or 0,
        sent_today=db.query(func.count(MailLog.id)).filter(
            MailLog.status == MailStatus.SENT,
            MailLog.created_at >= today_start,
        ).scalar() or 0,
        errors_today=db.query(func.count(MailLog.id)).filter(
            MailLog.status.in_([MailStatus.FAILED, MailStatus.BOUNCED]),
            MailLog.created_at >= today_start,
        ).scalar() or 0,
    )


# ============================================================
# ADMIN: VIEW ANY USER'S RELAYS
# ============================================================

@router.get("/users/{user_id}/providers")
def admin_list_user_providers(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List providers for a specific user (admin view)."""
    providers = db.query(Provider).filter(Provider.user_id == user_id).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "email": p.email,
            "provider_type": p.provider_type,
            "status": p.status.value,
            "is_locked": p.is_locked,
            "locked_reason": p.locked_reason,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            "proxy_id": p.proxy_id,
            "daily_sent": p.daily_sent,
            "daily_limit": p.daily_limit,
            "created_at": p.created_at.isoformat(),
        }
        for p in providers
    ]


@router.patch("/providers/{provider_id}/lock")
def admin_lock_provider(
    provider_id: int,
    reason: str = "Locked by admin",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Lock/unlock a specific provider."""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")

    if provider.is_locked:
        # Unlock
        provider.is_locked = False
        provider.locked_reason = None
        provider.status = ProviderStatus.ACTIVE
    else:
        # Lock
        provider.is_locked = True
        provider.locked_reason = reason
        provider.status = ProviderStatus.LOCKED

    db.commit()
    return {"is_locked": provider.is_locked, "status": provider.status.value}


# ============================================================
# GLOBAL PROVIDER TYPE LIMITS
# ============================================================

class ProviderTypeLimitOut(BaseModel):
    provider_type: str
    daily_limit: int

class ProviderTypeLimitUpdate(BaseModel):
    daily_limit: int


@router.get("/provider-limits", response_model=list[ProviderTypeLimitOut])
def list_provider_limits(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """List all global provider type limits."""
    return db.query(ProviderTypeLimit).order_by(ProviderTypeLimit.provider_type).all()


@router.patch("/provider-limits/{provider_type}", response_model=ProviderTypeLimitOut)
def update_provider_limit(
    provider_type: str,
    data: ProviderTypeLimitUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Update global daily limit for a provider type."""
    limit = db.query(ProviderTypeLimit).get(provider_type)
    if not limit:
        # Create if doesn't exist (e.g. new custom type)
        limit = ProviderTypeLimit(provider_type=provider_type, daily_limit=data.daily_limit)
        db.add(limit)
    else:
        limit.daily_limit = data.daily_limit
    db.commit()
    db.refresh(limit)
    return limit