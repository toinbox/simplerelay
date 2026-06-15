#!/bin/bash
set -e

# Create runtime directories
mkdir -p /data/logs /data/oauth /var/log
touch /var/log/mail.log

# Wait for database
echo "Waiting for database..."
for i in $(seq 1 30); do
  python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ.get('RELAY_DATABASE_URL', 'postgresql://simplerelay:simplerelay@db:5432/simplerelay'))
conn.close()
print('Database ready')
" 2>/dev/null && break
  echo "  attempt $i..."
  sleep 1
done

# Create tables + seed admin BEFORE supervisord
echo "Initializing database..."
cd /app && python3 -c "
from backend.database import init_db
init_db()
print('Database initialized')
"

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf