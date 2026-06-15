"""Background task: lock expired provider relays."""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import and_
from backend.database import SessionLocal
from backend.models import Provider, ProviderStatus, User


def check_expirations():
    """Lock providers that have passed their expiration date."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find providers with expiry set that are past due
        expired = db.query(Provider).filter(
            Provider.expires_at != None,
            Provider.expires_at <= now,
            Provider.is_locked == False,
            Provider.status != ProviderStatus.LOCKED,
        ).all()

        for provider in expired:
            provider.is_locked = True
            provider.status = ProviderStatus.LOCKED
            provider.locked_reason = "Relay expired"

        # Also check users with relay_expiry_days — set expires_at on providers
        # that don't have one yet
        users_with_expiry = db.query(User).filter(
            User.relay_expiry_days != None,
            User.relay_expiry_days > 0,
        ).all()

        for user in users_with_expiry:
            unset = db.query(Provider).filter(
                Provider.user_id == user.id,
                Provider.expires_at == None,
                Provider.is_locked == False,
            ).all()

            for provider in unset:
                provider.expires_at = provider.created_at + timedelta(
                    days=user.relay_expiry_days
                )
                # Check if already expired
                if provider.expires_at <= now:
                    provider.is_locked = True
                    provider.status = ProviderStatus.LOCKED
                    provider.locked_reason = "Relay expired"

        if expired or any(u for u in users_with_expiry):
            db.commit()

    finally:
        db.close()


async def main():
    """Run expiration checks every 10 minutes."""
    await asyncio.sleep(10)  # wait for DB init
    while True:
        try:
            check_expirations()
        except Exception as e:
            print(f"Expiration check error: {e}")
        await asyncio.sleep(600)


if __name__ == "__main__":
    asyncio.run(main())