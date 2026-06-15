#!/usr/bin/env python3
"""
SimpleRelay pipe transport — stealth outbound email via SOCKS5 proxy.

Called by Postfix pipe daemon for each outbound email:
  stdin  = raw email message
  argv   = sender recipient

Mimics a normal email client:
  - EHLO with [proxy_ip] (not relay domain)
  - Strips internal Received headers
  - Ensures Message-ID uses sender domain
  - Routes through SOCKS5 proxy per provider config

Exit codes (Postfix pipe protocol):
  0  = delivered
  75 = temp failure → Postfix will retry
  69 = permanent failure → Postfix will bounce
"""

import sys
import os
import re
import uuid
import socket
import ipaddress
import smtplib
import ssl
import logging
import email
import email.encoders
from email.utils import parseaddr, formatdate
from urllib.parse import urlparse

# ── Setup path so we can import backend modules ──
sys.path.insert(0, "/app")

from backend.config import settings
from backend.services.crypto import decrypt_password

import psycopg2
import psycopg2.extras

# ── Logging to syslog / stderr (Postfix captures stderr) ──
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="pipe_transport: %(message)s",
)
log = logging.getLogger(__name__)

# ── SOCKS5 support (same approach as CampaignPilot pool_tasks.py) ──
try:
    import socks
    HAS_SOCKS = True
except ImportError:
    HAS_SOCKS = False

EX_OK = 0
EX_TEMPFAIL = 75
EX_UNAVAILABLE = 69


# ══════════════════════════════════════════════════════════
# DATABASE — lightweight queries, no ORM overhead
# ══════════════════════════════════════════════════════════

def get_db_conn():
    """Direct psycopg2 connection for speed (no SQLAlchemy ORM)."""
    return psycopg2.connect(
        settings.database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def lookup_provider(conn, sender_email):
    """Find active provider by sender email address."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.id, p.email, p.smtp_host, p.smtp_port, p.tls_mode,
                   p.username, p.password_encrypted, p.provider_type, p.proxy_id,
                   p.user_id, p.daily_limit, p.daily_sent
            FROM providers p
            WHERE p.email = %s
              AND p.status::text IN ('active', 'ACTIVE')
              AND p.is_locked = false
            LIMIT 1
        """, (sender_email,))
        return cur.fetchone()


def lookup_proxies(conn, proxy_id=None, provider_type=None):
    """Find all matching proxies, ordered by priority.
    Returns list — caller tries them in order (failover).

    Priority: direct ID (validated) → specific domain → catch-all fallback.
    Within each tier, ordered by current_assignments ASC (load balance).

    Known providers (gmail, outlook …) NEVER get catch-all proxies,
    even if one was incorrectly assigned via proxy_id.
    """
    _KNOWN_PROVIDERS = {"gmail", "outlook", "yahoo", "seznam", "mailcz",
                        "icloud", "amazon_ses", "sendgrid"}
    is_known = provider_type in _KNOWN_PROVIDERS

    proxies = []
    seen_ids = set()

    with conn.cursor() as cur:
        # 1. Direct assignment on provider — validate against provider_type
        if proxy_id:
            cur.execute("""
                SELECT id, host, port, username, password_encrypted, protocol,
                       provider_types
                FROM proxies
                WHERE id = %s AND is_active = true
            """, (proxy_id,))
            row = cur.fetchone()
            if row:
                row_types = row.get("provider_types")  # list or None
                is_catchall = row_types is None or row_types == "null"

                if is_catchall and is_known:
                    # Catch-all wrongly assigned to a known provider — skip
                    log.warning(
                        f"Skipping catch-all proxy id={proxy_id} for "
                        f"known provider type '{provider_type}'"
                    )
                else:
                    proxies.append(row)
                    seen_ids.add(row["id"])

        # 2. Specific domain match
        if provider_type:
            cur.execute("""
                SELECT id, host, port, username, password_encrypted, protocol
                FROM proxies
                WHERE is_active = true
                  AND provider_types::jsonb @> %s::jsonb
                ORDER BY current_assignments ASC
            """, (f'["{provider_type}"]',))
            for row in cur.fetchall():
                if row["id"] not in seen_ids:
                    proxies.append(row)
                    seen_ids.add(row["id"])

        # 3. Catch-all fallback — ONLY for custom/unknown provider types.
        if not is_known:
            cur.execute("""
                SELECT id, host, port, username, password_encrypted, protocol
                FROM proxies
                WHERE is_active = true AND (provider_types IS NULL OR provider_types::text = 'null')
                ORDER BY current_assignments ASC
            """)
            for row in cur.fetchall():
                if row["id"] not in seen_ids:
                    proxies.append(row)
                    seen_ids.add(row["id"])

    return proxies


def _increment_daily_sent(conn, provider_id):
    """Atomically increment daily_sent counter for provider."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE providers SET daily_sent = daily_sent + 1 WHERE id = %s",
                (provider_id,),
            )
        conn.commit()
    except Exception as e:
        log.warning(f"Failed to increment daily_sent: {e}")


def _get_global_daily_limit(conn, provider_type):
    """Get global daily limit for this provider type from provider_type_limits table."""
    if not provider_type:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT daily_limit FROM provider_type_limits WHERE provider_type = %s",
                (provider_type,),
            )
            row = cur.fetchone()
            return row["daily_limit"] if row else None
    except Exception as e:
        log.warning(f"Failed to get global limit for {provider_type}: {e}")
        return None


def check_client_authorized(conn, client_ip, provider):
    """Check if client IP is authorized to send via this provider.

    IP must be explicitly assigned to this provider in allowed_clients.
    No global/wildcard — every IP-provider pair must be explicitly configured.

    Returns True if authorized, False otherwise.
    """
    try:
        client_addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    provider_id = provider.get("id")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT ip_address, ip_cidr
            FROM allowed_clients
            WHERE client_type = 'ip'
              AND is_active = true
              AND provider_id = %s
        """, (provider_id,))

        for row in cur.fetchall():
            cidr = row.get("ip_cidr") or row.get("ip_address")
            if not cidr:
                continue
            try:
                if client_addr in ipaddress.ip_network(cidr.strip(), strict=False):
                    return True
            except ValueError:
                continue

    return False


def log_to_db(conn, sender, recipient, provider_name, status,
              error=None, proxy_name=None, user_id=None, provider_id=None):
    """Log delivery result to mail_log table."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO mail_log
                    (queue_id, sender, recipient, provider_name, status,
                     error_message, user_id, provider_id, proxy_ip, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                f"pipe-{uuid.uuid4().hex[:12]}",
                sender,
                recipient,
                provider_name or "unknown",
                status.upper(),
                error,
                user_id,
                provider_id,
                proxy_name,
            ))
        conn.commit()
    except Exception as e:
        log.warning(f"Failed to log to DB: {e}")


# ══════════════════════════════════════════════════════════
# PROXY CONTEXT — monkey-patch socket like CampaignPilot
# ══════════════════════════════════════════════════════════

def _resolve_ehlo_host(proxy_host, smtp_host):
    """Determine EHLO hostname as IP in brackets.

    With proxy:    resolve proxy hostname → [proxy_ip]
    Without proxy: use PUBLIC_IP from env → [public_ip]
    Fallback:      [127.0.0.1]
    """
    if proxy_host:
        try:
            proxy_ip = socket.gethostbyname(proxy_host)
            return f"[{proxy_ip}]"
        except Exception:
            return f"[{proxy_host}]"

    if settings.public_ip:
        return f"[{settings.public_ip}]"

    return "[127.0.0.1]"


def _apply_proxy(proxy_row):
    """Set up SOCKS5 proxy by monkey-patching socket.create_connection.
    Returns (original_func, proxy_host) for cleanup + EHLO.
    """
    if not proxy_row or not HAS_SOCKS:
        return None, None

    host = proxy_row["host"]
    port = proxy_row.get("port") or 1080
    username = proxy_row.get("username")
    password = proxy_row.get("password_encrypted")

    # Proxy password is stored encrypted (same Fernet as provider passwords)
    if password:
        try:
            password = decrypt_password(password)
        except Exception:
            pass  # might be plaintext in older entries

    original = socket.create_connection

    def proxied(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        s = socks.socksocket()
        s.set_proxy(
            socks.SOCKS5, host, port,
            rdns=True,
            username=username,
            password=password,
        )
        if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            s.settimeout(timeout)
        s.connect(address)
        return s

    socket.create_connection = proxied
    return original, host


def _restore_socket(original):
    """Restore original socket.create_connection."""
    if original:
        socket.create_connection = original


# ══════════════════════════════════════════════════════════
# MESSAGE CLEANUP — strip relay traces, fix Message-ID
# ══════════════════════════════════════════════════════════


def clean_message(raw_bytes, sender_email):
    """Strip relay traces, enforce From = envelope sender, emulate eM Client.
    Returns cleaned raw bytes ready for SMTP.

    Security: From header is ALWAYS set to sender_email (envelope sender).
    This prevents abuse where someone uses provider A to send as provider B.

    Mimics eM Client 10.4.0.0 headers:
    - Header order: From, To, Subject, Date, Message-Id, Reply-To,
      User-Agent, MIME-Version, Content-Type, CTE, X-Last-TLS-Session-Version
    - Message-Id: <em{uuid}@domain>
    - User-Agent: eMClient/10.4.0.0
    - Date: local timezone (not UTC)
    - X-Last-TLS-Session-Version: TLSv1.3
    """
    sender_domain = sender_email.split("@")[-1] if "@" in sender_email else "localhost"
    msg = email.message_from_bytes(raw_bytes)

    # ── Strip relay traces ──
    while "Received" in msg:
        del msg["Received"]
    if "Return-Path" in msg:
        del msg["Return-Path"]
    # Strip Gmail's rewrite header (leaks original From)
    if "X-Google-Original-From" in msg:
        del msg["X-Google-Original-From"]

    # ── Enforce From = envelope sender (security) ──
    if "From" in msg:
        del msg["From"]
    msg["From"] = sender_email

    # ── Strip relay traces ──
    while "Received" in msg:
        del msg["Received"]
    if "Return-Path" in msg:
        del msg["Return-Path"]

    # ── Convert 8bit text → quoted-printable (prevents DKIM body hash mismatch) ──
    for part in msg.walk():
        cte = (part.get("Content-Transfer-Encoding") or "").lower()
        if part.get_content_maintype() == "text" and cte == "8bit":
            raw = part.get_payload(decode=True)
            if raw:
                del part["Content-Transfer-Encoding"]
                part.set_payload(raw)
                email.encoders.encode_quopri(part)

    # ── eM Client headers ──

    # Message-Id → eM Client format: <em{uuid}@domain>
    if "Message-Id" in msg:
        del msg["Message-Id"]
    if "Message-ID" in msg:
        del msg["Message-ID"]
    msg["Message-Id"] = f"<em{uuid.uuid4()}@{sender_domain}>"

    # Date → local timezone (eM Client never sends UTC +0000)
    if "Date" in msg:
        del msg["Date"]
    msg["Date"] = formatdate(localtime=True)

    # User-Agent (replaces any X-Mailer)
    if "X-Mailer" in msg:
        del msg["X-Mailer"]
    if "User-Agent" in msg:
        del msg["User-Agent"]
    msg["User-Agent"] = "eMClient/10.4.0.0"

    # X-Last-TLS-Session-Version
    if "X-Last-TLS-Session-Version" not in msg:
        msg["X-Last-TLS-Session-Version"] = "TLSv1.3"

    # Reply-To (eM Client always includes it, matching From)
    if "Reply-To" in msg:
        del msg["Reply-To"]
    msg["Reply-To"] = sender_email

    # ── Reorder headers to match eM Client fingerprint ──
    _reorder_headers_emclient(msg)

    return msg.as_bytes()


# eM Client header order (lowercase keys for matching)
_EMCLIENT_HEADER_ORDER = [
    "from", "to", "subject", "date", "message-id", "reply-to",
    "user-agent", "mime-version", "content-type",
    "content-transfer-encoding", "x-last-tls-session-version",
]


def _reorder_headers_emclient(msg):
    """Reorder message headers to match eM Client fingerprint.
    Preserves original header values, only changes order.
    """
    headers = list(msg._headers)
    msg._headers.clear()

    added = set()
    for key in _EMCLIENT_HEADER_ORDER:
        for i, (name, value) in enumerate(headers):
            if name.lower() == key and i not in added:
                msg._headers.append((name, value))
                added.add(i)

    # Append any remaining headers not in the eM Client order
    for i, (name, value) in enumerate(headers):
        if i not in added:
            msg._headers.append((name, value))


# ══════════════════════════════════════════════════════════
# SMTP SEND — connect through proxy, EHLO as client
# ══════════════════════════════════════════════════════════

def send_via_provider(provider, proxy_row, raw_message, sender, recipient):
    """Send email through provider's SMTP, optionally via SOCKS5 proxy.
    Returns (success, error_message).
    """
    smtp_host = provider["smtp_host"]
    smtp_port = provider["smtp_port"]
    tls_mode = provider.get("tls_mode", "starttls")
    username = provider.get("username") or provider["email"]
    password_enc = provider.get("password_encrypted", "")

    try:
        password = decrypt_password(password_enc) if password_enc else ""
    except Exception:
        return False, "cannot decrypt provider password"

    # Set up proxy
    original_socket, proxy_host = _apply_proxy(proxy_row)

    try:
        # EHLO as [IP] — like a normal email client
        ehlo_host = _resolve_ehlo_host(proxy_host, smtp_host)

        if tls_mode == "ssl" or smtp_port == 465:
            smtp = smtplib.SMTP_SSL(
                smtp_host, smtp_port, timeout=30, local_hostname=ehlo_host,
            )
            smtp.ehlo(ehlo_host)
        else:
            smtp = smtplib.SMTP(
                smtp_host, smtp_port, timeout=30, local_hostname=ehlo_host,
            )
            smtp.ehlo(ehlo_host)
            if tls_mode == "starttls":
                smtp.starttls()
                smtp.ehlo(ehlo_host)

        smtp.login(username, password)
        smtp.sendmail(sender, [recipient], raw_message)
        smtp.quit()
        return True, None

    except smtplib.SMTPAuthenticationError as e:
        return False, f"auth_error: {str(e)[:200]}"
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"recipient_refused: {str(e)[:200]}"
    except smtplib.SMTPException as e:
        return False, f"smtp_error: {str(e)[:200]}"
    except (socket.timeout, ConnectionError, OSError) as e:
        return False, f"connection_error: {str(e)[:200]}"
    finally:
        _restore_socket(original_socket)


# ══════════════════════════════════════════════════════════
# MAIN — Postfix pipe entry point
# ══════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        log.error("Usage: pipe_transport.py <sender> <recipient> [client_address]")
        sys.exit(EX_TEMPFAIL)

    sender = sys.argv[1]
    recipient = sys.argv[2]
    client_address = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
    sender_domain = sender.split("@")[-1] if "@" in sender else "localhost"

    log.info(f"Processing: {sender} → {recipient} (client={client_address})")

    # Read raw email from stdin
    raw_message = sys.stdin.buffer.read()
    if not raw_message:
        log.error("Empty message on stdin")
        sys.exit(EX_TEMPFAIL)

    conn = None
    try:
        conn = get_db_conn()

        # Look up provider for this sender
        provider = lookup_provider(conn, sender)
        if not provider:
            log.error(f"No active provider for sender: {sender}")
            sys.exit(EX_UNAVAILABLE)

        # Per-provider IP authorization (skip for localhost — internal test endpoint)
        if client_address not in ("127.0.0.1", "::1"):
            if not check_client_authorized(conn, client_address, provider):
                log.error(f"REJECTED: {client_address} not authorized for provider {sender}")
                sys.exit(EX_UNAVAILABLE)
            log.info(f"Authorized: {client_address} → {sender}")

        # Look up all available proxies (failover list)
        proxies = lookup_proxies(
            conn,
            proxy_id=provider.get("proxy_id"),
            provider_type=provider.get("provider_type"),
        )

        # Clean message — eM Client emulation, strip relay traces
        cleaned = clean_message(raw_message, sender)

        # Daily limit check — global limit per provider type
        daily_limit = _get_global_daily_limit(conn, provider.get("provider_type"))
        daily_sent = provider.get("daily_sent") or 0
        if daily_limit is not None and daily_sent >= daily_limit:
            log.error(f"Daily limit reached: {sender} ({daily_sent}/{daily_limit})")
            log_to_db(conn, sender, recipient, provider["smtp_host"], "failed",
                       error=f"daily_limit_reached ({daily_sent}/{daily_limit})",
                       user_id=provider.get("user_id"),
                       provider_id=provider.get("id"))
            sys.exit(EX_UNAVAILABLE)

        # No proxies → send direct (single attempt)
        if not proxies:
            proxies = [None]

        # Try each proxy in order (failover)
        last_error = None
        for i, proxy in enumerate(proxies):
            proxy_info = f" via proxy {proxy['host']}:{proxy['port']}" if proxy else " (direct)"
            log.info(f"Attempt {i + 1}/{len(proxies)}: {provider['smtp_host']}:{provider['smtp_port']}{proxy_info}")

            success, error = send_via_provider(provider, proxy, cleaned, sender, recipient)

            if success:
                log.info(f"Delivered: {sender} → {recipient}{proxy_info}")
                # Increment daily_sent counter
                _increment_daily_sent(conn, provider["id"])
                log_to_db(conn, sender, recipient, provider["smtp_host"], "sent",
                           proxy_name=proxy["host"] if proxy else None,
                           user_id=provider.get("user_id"),
                           provider_id=provider.get("id"))
                sys.exit(EX_OK)

            last_error = error

            # Auth/recipient errors are permanent — don't try other proxies
            if error and ("auth_error" in error or "recipient_refused" in error):
                log.error(f"Permanent failure: {sender} → {recipient}: {error}")
                log_to_db(conn, sender, recipient, provider["smtp_host"], "failed",
                           error=error, user_id=provider.get("user_id"),
                           provider_id=provider.get("id"))
                sys.exit(EX_UNAVAILABLE)

            # Connection error — log and try next proxy
            log.warning(f"Proxy failed{proxy_info}: {error}")

        # All proxies exhausted
        log.error(f"All proxies failed: {sender} → {recipient}: {last_error}")
        log_to_db(conn, sender, recipient, provider["smtp_host"], "failed",
                   error=last_error, user_id=provider.get("user_id"),
                   provider_id=provider.get("id"))
        sys.exit(EX_TEMPFAIL)

    except Exception as e:
        log.error(f"Unexpected error: {e}")
        sys.exit(EX_TEMPFAIL)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()