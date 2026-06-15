#!/bin/bash
set -e

# Start syslog (Postfix needs it for mail.log)
rsyslogd 2>/dev/null || true

# Wait for database
sleep 2

# Generate Postfix config from database
python -m backend.services.postfix_config --init 2>/dev/null || echo "Config init skipped (DB not ready yet)"

# Fix permissions
chown -R root:root /etc/postfix/
chmod 600 /etc/postfix/sasl_passwd 2>/dev/null || true
postmap /etc/postfix/sasl_passwd 2>/dev/null || true
postmap /etc/postfix/sender_relay 2>/dev/null || true

# Start Postfix in foreground
postfix start-fg
