FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install Postfix + supervisor + DNS tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    postfix \
    libsasl2-modules \
    sasl2-bin \
    supervisor \
    rsyslog \
    dnsutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for frontend build
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Frontend build
COPY frontend/package.json frontend/package-lock.json* /app/frontend/
RUN cd /app/frontend && npm install

COPY frontend/ /app/frontend/
RUN cd /app/frontend && npm run build

# Backend
COPY backend/ /app/backend/

# Postfix base config
COPY postfix/master.cf /etc/postfix/master.cf
COPY postfix/main.cf /etc/postfix/main.cf
COPY postfix/sasl_passwd /etc/postfix/sasl_passwd
COPY postfix/sender_relay /etc/postfix/sender_relay

# Scripts
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/postfix-start.sh /app/scripts/entrypoint.sh \
    && chmod +x /app/backend/services/pipe_transport.py

# Supervisor config
COPY scripts/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create data directory and fix Postfix permissions
RUN mkdir -p /data/oauth /data/logs /var/log \
    && chmod 600 /etc/postfix/sasl_passwd \
    && touch /var/log/mail.log

EXPOSE 2525 8080

CMD ["/app/scripts/entrypoint.sh"]