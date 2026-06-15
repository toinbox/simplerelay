"""Background task: periodic cleanup and daily resets.

Runs every hour, performs:
- Reset daily_sent counters at midnight (UTC)
- Delete mail_log entries older than 24 hours
- Truncate /var/log/mail.log when over 50MB
- Flush Postfix deferred queue
"""
import time
import os
import subprocess
import logging
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/app")

from backend.database import SessionLocal
from backend.models import MailLog, Provider

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="log_cleanup: %(message)s",
)
log = logging.getLogger(__name__)

INTERVAL = 3600              # check every hour
LOG_RETENTION_HOURS = 24     # keep mail_log for 24 hours
MAIL_LOG_MAX_BYTES = 50_000_000
MAIL_LOG_PATH = "/var/log/mail.log"

_last_reset_date = None


def reset_daily_counters():
    """Reset daily_sent to 0 on all providers — once per day at midnight."""
    global _last_reset_date
    today = datetime.utcnow().date()

    if _last_reset_date == today:
        return  # already reset today

    db = SessionLocal()
    try:
        updated = db.query(Provider).filter(
            Provider.daily_sent > 0
        ).update({"daily_sent": 0})
        db.commit()
        _last_reset_date = today
        if updated:
            log.info(f"Reset daily_sent on {updated} providers")
    except Exception as e:
        log.error(f"Daily reset error: {e}")
        db.rollback()
    finally:
        db.close()


def cleanup_mail_log_db():
    """Delete mail_log entries older than retention period."""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=LOG_RETENTION_HOURS)
        deleted = db.query(MailLog).filter(MailLog.created_at < cutoff).delete()
        db.commit()
        if deleted:
            log.info(f"Pruned {deleted} mail_log entries older than {LOG_RETENTION_HOURS}h")
    except Exception as e:
        log.error(f"DB cleanup error: {e}")
        db.rollback()
    finally:
        db.close()


def cleanup_mail_log_file():
    """Truncate /var/log/mail.log if over size limit."""
    try:
        if os.path.exists(MAIL_LOG_PATH):
            size = os.path.getsize(MAIL_LOG_PATH)
            if size > MAIL_LOG_MAX_BYTES:
                with open(MAIL_LOG_PATH, "w") as f:
                    f.write("")
                log.info(f"Truncated {MAIL_LOG_PATH} (was {size // 1_000_000}MB)")
    except Exception as e:
        log.error(f"Mail log file cleanup error: {e}")


def cleanup_postfix_queue():
    """Flush old deferred mail from Postfix queue."""
    try:
        result = subprocess.run(
            ["postsuper", "-d", "ALL", "deferred"],
            capture_output=True, text=True, timeout=30,
        )
        if result.stdout.strip():
            log.info(f"Postfix deferred queue flushed: {result.stdout.strip()}")
    except Exception as e:
        log.error(f"Postfix queue cleanup error: {e}")


def main():
    log.info(f"Started (interval={INTERVAL}s, log_retention={LOG_RETENTION_HOURS}h)")
    while True:
        reset_daily_counters()
        cleanup_mail_log_db()
        cleanup_mail_log_file()
        cleanup_postfix_queue()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
