import secrets
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import bcrypt as _bcrypt
from backend.database import get_db
from backend.models import AllowedClient, Provider, User
from backend.services.postfix_config import write_and_reload
from backend.services.auth import get_current_user

router = APIRouter(prefix="/api/clients", tags=["clients"])


class ClientCreate(BaseModel):
    name: str
    client_type: str  # ip, smtp_auth
    provider_id: int | None = None
    ip_address: str | None = None
    ip_cidr: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    ip_address: str | None = None
    ip_cidr: str | None = None
    is_active: bool | None = None


class ClientOut(BaseModel):
    id: int
    name: str
    client_type: str
    provider_id: int | None
    ip_address: str | None
    ip_cidr: str | None
    smtp_username: str | None
    smtp_password_plain: str | None
    is_active: bool

    class Config:
        from_attributes = True


class ClientWithCredentials(ClientOut):
    smtp_password_plain: str | None = None


@router.get("/", response_model=list[ClientOut])
def list_clients(
    provider_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List allowed clients, optionally filtered by provider."""
    q = db.query(AllowedClient).filter(AllowedClient.user_id == user.id)
    if provider_id is not None:
        q = q.filter(AllowedClient.provider_id == provider_id)
    return q.order_by(AllowedClient.id).all()


@router.post("/", response_model=ClientWithCredentials)
def create_client(data: ClientCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Add a new allowed client, optionally bound to a provider."""
    # Verify provider belongs to user
    if data.provider_id:
        provider = db.query(Provider).filter(
            Provider.id == data.provider_id,
            Provider.user_id == user.id,
        ).first()
        if not provider:
            raise HTTPException(404, "Provider not found")

    client = AllowedClient(
        user_id=user.id,
        provider_id=data.provider_id,
        name=data.name,
        client_type=data.client_type,
        is_active=True,
    )

    plain_password = None

    if data.client_type == "ip":
        if not data.ip_address and not data.ip_cidr:
            raise HTTPException(400, "IP address or CIDR required")
        client.ip_address = data.ip_address
        client.ip_cidr = data.ip_cidr or data.ip_address

    elif data.client_type == "smtp_auth":
        username = data.name.lower().replace(" ", "_")
        plain_password = secrets.token_urlsafe(16)
        client.smtp_username = username
        client.smtp_password_hash = _bcrypt.hashpw(plain_password.encode(), _bcrypt.gensalt()).decode()
        client.smtp_password_plain = plain_password

    db.add(client)
    db.commit()
    db.refresh(client)

    try:
        write_and_reload(db)
    except Exception:
        pass

    result = ClientWithCredentials.model_validate(client)
    if plain_password:
        result.smtp_password_plain = plain_password
    return result


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update an allowed client (name, IP, active status)."""
    client = db.query(AllowedClient).filter(
        AllowedClient.id == client_id,
        AllowedClient.user_id == user.id,
    ).first()
    if not client:
        raise HTTPException(404, "Client not found")

    if data.name is not None:
        client.name = data.name
    if data.is_active is not None:
        client.is_active = data.is_active
    if client.client_type == "ip":
        if data.ip_cidr is not None:
            client.ip_cidr = data.ip_cidr
            client.ip_address = data.ip_address or data.ip_cidr
        elif data.ip_address is not None:
            client.ip_address = data.ip_address

    db.commit()
    db.refresh(client)

    try:
        write_and_reload(db)
    except Exception:
        pass

    return client


@router.post("/{client_id}/regenerate", response_model=ClientWithCredentials)
def regenerate_password(
    client_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Regenerate SMTP auth password for a client."""
    client = db.query(AllowedClient).filter(
        AllowedClient.id == client_id,
        AllowedClient.user_id == user.id,
        AllowedClient.client_type == "smtp_auth",
    ).first()
    if not client:
        raise HTTPException(404, "SMTP auth client not found")

    plain_password = secrets.token_urlsafe(16)
    client.smtp_password_hash = _bcrypt.hashpw(plain_password.encode(), _bcrypt.gensalt()).decode()
    client.smtp_password_plain = plain_password
    db.commit()
    db.refresh(client)

    try:
        write_and_reload(db)
    except Exception:
        pass

    result = ClientWithCredentials.model_validate(client)
    result.smtp_password_plain = plain_password
    return result


@router.delete("/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Remove an allowed client."""
    client = db.query(AllowedClient).filter(
        AllowedClient.id == client_id,
        AllowedClient.user_id == user.id,
    ).first()
    if not client:
        raise HTTPException(404, "Client not found")

    db.delete(client)
    db.commit()

    try:
        write_and_reload(db)
    except Exception:
        pass

    return {"deleted": True}


@router.patch("/{client_id}/toggle")
def toggle_client(client_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Toggle client active status."""
    client = db.query(AllowedClient).filter(
        AllowedClient.id == client_id,
        AllowedClient.user_id == user.id,
    ).first()
    if not client:
        raise HTTPException(404, "Client not found")

    client.is_active = not client.is_active
    db.commit()

    try:
        write_and_reload(db)
    except Exception:
        pass

    return {"is_active": client.is_active}
