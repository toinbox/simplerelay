from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import backend.models  # noqa: F401 — register all models with Base.metadata
    Base.metadata.create_all(bind=engine)
    _migrate_db()
    seed_admin()
    seed_provider_limits()


def _migrate_db():
    """Add columns that were added to models after initial table creation."""
    insp = inspect(engine)
    
    # proxies.provider_types (JSON, nullable)
    if "proxies" in insp.get_table_names():
        columns = [c["name"] for c in insp.get_columns("proxies")]
        if "provider_types" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE proxies ADD COLUMN provider_types JSON"))
            print("Migration: added proxies.provider_types")

    # allowed_clients.provider_id (INTEGER, nullable, FK to providers.id)
    if "allowed_clients" in insp.get_table_names():
        columns = [c["name"] for c in insp.get_columns("allowed_clients")]
        if "provider_id" not in columns:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE allowed_clients ADD COLUMN provider_id INTEGER REFERENCES providers(id) ON DELETE CASCADE"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_allowed_clients_provider_id ON allowed_clients (provider_id)"
                ))
            print("Migration: added allowed_clients.provider_id")

        if "smtp_password_plain" not in columns:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE allowed_clients ADD COLUMN smtp_password_plain VARCHAR(255)"
                ))
            print("Migration: added allowed_clients.smtp_password_plain")


def seed_admin():
    """Create default admin from .env if not exists."""
    from backend.config import settings
    from backend.models import User, UserRole
    from backend.services.auth import hash_password

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.admin_email).first()
        if not existing:
            admin = User(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                name="Admin",
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
                max_relays=100,
            )
            db.add(admin)
            db.commit()
            print(f"Admin account created: {settings.admin_email}")
        else:
            print(f"Admin account exists: {settings.admin_email}")
    finally:
        db.close()


def seed_provider_limits():
    """Seed provider_type_limits from presets (only inserts missing types)."""
    from backend.models import ProviderTypeLimit
    from backend.services.provider_presets import PROVIDER_PRESETS

    db = SessionLocal()
    try:
        for ptype, preset in PROVIDER_PRESETS.items():
            existing = db.query(ProviderTypeLimit).get(ptype)
            if not existing and preset.get("daily_limit") is not None:
                db.add(ProviderTypeLimit(
                    provider_type=ptype,
                    daily_limit=preset["daily_limit"],
                ))
        db.commit()
        print("Provider type limits seeded")
    finally:
        db.close()