"""Parse Postfix mail log and store delivery events in database."""
import re
import time
import subprocess
from datetime import datetime
from backend.database import SessionLocal
from backend.models import MailLog, MailStatus


# Postfix log patterns
RE_QUEUE = re.compile(
    r"postfix/smtpd\[\d+\]: (\w+): client=.+\[(.+?)\]"
)
RE_FROM = re.compile(
    r"postfix/cleanup\[\d+\]: (\w+): message-id=.+from=<(.+?)>"
)
RE_QMGR = re.compile(
    r"postfix/qmgr\[\d+\]: (\w+): from=<(.+?)>,.+size=(\d+)"
)
RE_SENT = re.compile(
    r"postfix/smtp\[\d+\]: (\w+): to=<(.+?)>,.+relay=(.+?)\[.+status=(\w+)\s*\((.+?)\)"
)
RE_BOUNCE = re.compile(
    r"postfix/bounce\[\d+\]: (\w+): .+status=(\w+)"
)

# In-memory tracking of queue IDs
queue_state: dict[str, dict] = {}


def parse_line(line: str):
    """Parse a single Postfix log line and update state/database."""
    db = SessionLocal()
    try:
        # New message queued
        m = RE_QUEUE.search(line)
        if m:
            qid, client_ip = m.groups()
            queue_state[qid] = {"client_ip": client_ip}
            return

        # Sender extracted
        m = RE_QMGR.search(line)
        if m:
            qid, sender, _ = m.groups()
            if qid in queue_state:
                queue_state[qid]["sender"] = sender
            return

        # Delivery result
        m = RE_SENT.search(line)
        if m:
            qid, recipient, relay, status_word, detail = m.groups()
            state = queue_state.get(qid, {})

            if status_word == "sent":
                status = MailStatus.SENT
            elif status_word == "bounced":
                status = MailStatus.BOUNCED
            else:
                status = MailStatus.FAILED

            log_entry = MailLog(
                queue_id=qid,
                sender=state.get("sender", "unknown"),
                recipient=recipient,
                provider_name=relay.split("[")[0] if "[" in relay else relay,
                status=status,
                error_message=detail if status != MailStatus.SENT else None,
                client_ip=state.get("client_ip"),
                created_at=datetime.utcnow(),
            )
            db.add(log_entry)
            db.commit()

            # Clean up state
            queue_state.pop(qid, None)
            return

    finally:
        db.close()


def tail_maillog():
    """Tail Postfix mail log and parse lines."""
    log_path = "/var/log/mail.log"

    # Wait for log file to exist
    import os
    while not os.path.exists(log_path):
        time.sleep(1)

    proc = subprocess.Popen(
        ["tail", "-F", log_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    for line in proc.stdout:
        line = line.strip()
        if "postfix/" in line:
            try:
                parse_line(line)
            except Exception as e:
                print(f"Log parse error: {e}")


if __name__ == "__main__":
    tail_maillog()
