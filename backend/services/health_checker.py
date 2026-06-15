"""Periodically check health of configured providers via SMTP AUTH login."""
import asyncio
import ssl
import time
import aiosmtplib
from datetime import datetime
from sqlalchemy import update
from backend.database import SessionLocal
from backend.models import Provider, HealthCheck, ProviderStatus
from backend.services.crypto import decrypt_password


def _make_tls_context():
    """Create TLS context that accepts self-signed / invalid certs."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def check_provider(provider: Provider) -> tuple[bool, int | None, str | None]:
    """Test SMTP connection + AUTH login to a provider.
    Returns (healthy, response_time_ms, error).
    """
    start = time.monotonic()
    try:
        use_tls = provider.tls_mode == "ssl"
        start_tls = provider.tls_mode == "starttls"
        tls_context = _make_tls_context() if (use_tls or start_tls) else None

        smtp = aiosmtplib.SMTP(
            hostname=provider.smtp_host,
            port=provider.smtp_port,
            use_tls=use_tls,
            start_tls=start_tls,
            tls_context=tls_context,
            timeout=15,
        )
        await smtp.connect()

        # Real AUTH login — not just EHLO
        if provider.username and provider.password_encrypted:
            try:
                password = decrypt_password(provider.password_encrypted)
            except Exception:
                password = provider.password_encrypted
            await smtp.login(provider.username, password)

        await smtp.quit()

        elapsed = int((time.monotonic() - start) * 1000)
        return True, elapsed, None

    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        return False, elapsed, str(e)


async def run_health_checks():
    """Check all active providers."""
    db = SessionLocal()
    try:
        providers = db.query(Provider).filter(
            Provider.status != ProviderStatus.DISABLED
        ).all()

        for provider in providers:
            healthy, response_time, error = await check_provider(provider)

            # Log health check
            check = HealthCheck(
                provider_id=provider.id,
                is_healthy=healthy,
                response_time_ms=response_time,
                error_message=error,
                checked_at=datetime.utcnow(),
            )
            db.add(check)

            # Update provider status
            new_status = ProviderStatus.ACTIVE if healthy else ProviderStatus.ERROR
            db.execute(
                update(Provider)
                .where(Provider.id == provider.id)
                .values(
                    status=new_status,
                    last_health_check=datetime.utcnow(),
                    last_error=error,
                )
            )

        db.commit()
    finally:
        db.close()


async def main():
    """Run health checks in a loop every 5 minutes."""
    await asyncio.sleep(15)  # wait for DB init
    while True:
        try:
            await run_health_checks()
        except Exception as e:
            print(f"Health check error: {e}")
        await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(main())