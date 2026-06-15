import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from backend.database import get_db
from backend.models import User, UserRole, PasswordReset, EmailVerification
from backend.services.auth import (
    hash_password, verify_password, create_access_token,
    generate_reset_token, get_current_user, RESET_TOKEN_EXPIRE_HOURS,
)
from backend.services.email_sender import send_verification_email, send_reset_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

VERIFY_TOKEN_EXPIRE_HOURS = 24


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str | None
    role: str
    is_active: bool
    is_verified: bool
    max_relays: int
    relay_expiry_days: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    user: UserOut


# --- Register ---

@router.post("/register")
async def register(data: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Register a new user account. Sends verification email."""
    existing = db.query(User).filter(
        func.lower(User.email) == data.email.lower()
    ).first()
    if existing:
        raise HTTPException(400, "Email already registered")

    if len(data.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    user = User(
        email=data.email.lower().strip(),
        password_hash=hash_password(data.password),
        name=data.name,
        role=UserRole.USER,
        is_active=True,
        is_verified=False,
        max_relays=1,
    )
    db.add(user)
    db.flush()

    # Create verification token
    token = generate_reset_token()
    verification = EmailVerification(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS),
    )
    db.add(verification)
    db.commit()

    # Send verification email in background
    background_tasks.add_task(send_verification_email, user.email, token)

    return {"message": "Registration successful. Check your email to verify your account."}


# --- Verify email ---

@router.get("/verify")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    """Verify email address using token from email."""
    verification = db.query(EmailVerification).filter(
        EmailVerification.token == token,
        EmailVerification.used == False,
        EmailVerification.expires_at > datetime.utcnow(),
    ).first()

    if not verification:
        raise HTTPException(400, "Invalid or expired verification link")

    user = db.query(User).filter(User.id == verification.user_id).first()
    if not user:
        raise HTTPException(400, "User not found")

    user.is_verified = True
    verification.used = True
    db.commit()

    return {"message": "Email verified. You can now log in."}


# --- Resend verification ---

@router.post("/resend-verification")
async def resend_verification(data: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Resend verification email."""
    user = db.query(User).filter(
        func.lower(User.email) == data.email.lower()
    ).first()

    if user and not user.is_verified:
        # Invalidate old tokens
        db.query(EmailVerification).filter(
            EmailVerification.user_id == user.id,
            EmailVerification.used == False,
        ).update({"used": True})

        token = generate_reset_token()
        verification = EmailVerification(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS),
        )
        db.add(verification)
        db.commit()

        background_tasks.add_task(send_verification_email, user.email, token)

    # Always return same message (no email enumeration)
    return {"message": "If the email exists and is unverified, a new link was sent."}


# --- Login ---

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(
        func.lower(User.email) == data.email.lower()
    ).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    if not user.is_active:
        raise HTTPException(403, "Account deactivated")

    if not user.is_verified:
        raise HTTPException(403, "Email not verified. Check your inbox or request a new link.")

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token(user.id, user.role.value)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )

    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


# --- Logout ---

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


# --- Current user ---

@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


# --- Forgot password ---

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Request password reset."""
    user = db.query(User).filter(
        func.lower(User.email) == data.email.lower()
    ).first()

    if user:
        db.query(PasswordReset).filter(
            PasswordReset.user_id == user.id,
            PasswordReset.used == False,
        ).update({"used": True})

        token = generate_reset_token()
        reset = PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS),
        )
        db.add(reset)
        db.commit()

        background_tasks.add_task(send_reset_email, user.email, token)

    return {"message": "If the email exists, a reset link was sent."}


# --- Reset password ---

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset = db.query(PasswordReset).filter(
        PasswordReset.token == data.token,
        PasswordReset.used == False,
        PasswordReset.expires_at > datetime.utcnow(),
    ).first()

    if not reset:
        raise HTTPException(400, "Invalid or expired reset token")

    if len(data.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    user = db.query(User).filter(User.id == reset.user_id).first()
    if not user:
        raise HTTPException(400, "User not found")

    user.password_hash = hash_password(data.password)
    reset.used = True
    db.commit()

    return {"message": "Password reset successfully"}


# --- Change password ---

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")

    if len(data.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    user.password_hash = hash_password(data.new_password)
    db.commit()

    return {"message": "Password changed"}
