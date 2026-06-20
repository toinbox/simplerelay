"""Postfix SMTP policy server — real-time IP+sender authorization from DB.

Postfix queries this server at RCPT TO time via:
  check_policy_service inet:127.0.0.1:9199

At that point both client_address AND sender are known, so we can
enforce per-provider IP restrictions at the SMTP level (reject before
accepting the message).

Protocol: Postfix SMTPD policy (attribute=value pairs, blank line terminated)
  Request attributes: client_address, sender, recipient, ...
  Response: action=permit | action=reject <reason>

No Postfix reload needed when IPs change in the admin UI.
"""
import socketserver
import ipaddress
import logging
import sys
import time

sys.path.insert(0, "/app")

from backend.database import SessionLocal
from backend.models import AllowedClient, Provider

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="access_server: %(message)s",
)
log = logging.getLogger(__name__)

# Simple cache to reduce DB queries
_cache = {"data": [], "domain_rules": [], "expires": 0}
CACHE_TTL = 30  # seconds


def _load_access_rules():
    """Load allowed client rules from DB with cache."""
    now = time.time()
    if now < _cache["expires"]:
        return _cache["data"], _cache["domain_rules"]

    db = SessionLocal()
    try:
        # Exact email rules (existing)
        rows = db.query(
            AllowedClient.ip_cidr,
            AllowedClient.ip_address,
            Provider.email.label("provider_email"),
        ).join(
            Provider, AllowedClient.provider_id == Provider.id
        ).filter(
            AllowedClient.client_type == "ip",
            AllowedClient.is_active == True,
            AllowedClient.provider_id != None,
            Provider.domain_routing == False,
        ).all()

        rules = []
        for r in rows:
            cidr = r.ip_cidr or r.ip_address
            if not cidr:
                continue
            try:
                network = ipaddress.ip_network(cidr.strip(), strict=False)
                rules.append((network, r.provider_email.lower()))
            except ValueError:
                log.warning(f"Invalid CIDR in DB: {cidr}")

        # Domain routing rules
        domain_rows = db.query(
            AllowedClient.ip_cidr,
            AllowedClient.ip_address,
            Provider.email.label("provider_email"),
        ).join(
            Provider, AllowedClient.provider_id == Provider.id
        ).filter(
            AllowedClient.client_type == "ip",
            AllowedClient.is_active == True,
            AllowedClient.provider_id != None,
            Provider.domain_routing == True,
        ).all()

        domain_rules = []
        for r in domain_rows:
            cidr = r.ip_cidr or r.ip_address
            if not cidr:
                continue
            try:
                network = ipaddress.ip_network(cidr.strip(), strict=False)
                domain = r.provider_email.lower().split("@")[-1]
                domain_rules.append((network, domain))
            except ValueError:
                log.warning(f"Invalid CIDR in DB: {cidr}")

        _cache["data"] = rules
        _cache["domain_rules"] = domain_rules
        _cache["expires"] = now + CACHE_TTL
        return rules, domain_rules
    except Exception as e:
        log.error(f"DB error loading rules: {e}")
        return _cache["data"], _cache["domain_rules"]
    finally:
        db.close()


def check_access(client_ip_str, sender):
    """Check if client_ip is authorized to send as sender.
    Returns (allowed: bool, reason: str).
    """
    if not client_ip_str or not sender:
        return False, "missing client_address or sender"

    # Always allow localhost (internal test endpoint / bounces)
    if client_ip_str in ("127.0.0.1", "::1"):
        return True, "localhost"

    try:
        client_ip = ipaddress.ip_address(client_ip_str)
    except ValueError:
        return False, f"invalid IP: {client_ip_str}"

    sender_lower = sender.lower()
    sender_domain = sender_lower.split("@")[-1] if "@" in sender_lower else ""
    rules, domain_rules = _load_access_rules()

    # Check if this IP+sender pair is explicitly allowed (exact email match)
    for network, provider_email in rules:
        if client_ip in network and sender_lower == provider_email:
            return True, f"matched {network} → {provider_email}"

    # Check domain routing rules
    for network, domain in domain_rules:
        if client_ip in network and sender_domain == domain:
            return True, f"domain_routing {network} → *@{domain}"

    # Check if IP exists at all (for better error message)
    ip_known = any(client_ip in net for net, _ in rules)
    if not ip_known:
        ip_known = any(client_ip in net for net, _ in domain_rules)
    if ip_known:
        return False, f"IP {client_ip_str} not authorized for sender {sender}"
    else:
        return False, f"IP {client_ip_str} not in whitelist"


class PolicyHandler(socketserver.StreamRequestHandler):
    """Handle Postfix SMTPD policy protocol."""

    def handle(self):
        while True:
            attrs = {}
            while True:
                line = self.rfile.readline()
                if not line:
                    return  # connection closed
                line = line.decode().strip()
                if not line:
                    break  # end of request (blank line)
                if "=" in line:
                    key, _, value = line.partition("=")
                    attrs[key] = value

            if not attrs:
                return

            client_ip = attrs.get("client_address", "")
            sender = attrs.get("sender", "")

            allowed, reason = check_access(client_ip, sender)

            if allowed:
                action = "permit"
                log.info(f"PERMIT {client_ip} → {sender} ({reason})")
            else:
                action = f"reject Access denied: {reason}"
                log.info(f"REJECT {client_ip} → {sender} ({reason})")

            self.wfile.write(f"action={action}\n\n".encode())
            self.wfile.flush()


def main():
    host, port = "127.0.0.1", 9199
    server = socketserver.ThreadingTCPServer((host, port), PolicyHandler)
    server.daemon_threads = True
    log.info(f"Policy server listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()