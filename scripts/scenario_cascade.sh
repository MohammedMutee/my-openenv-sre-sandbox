#!/bin/bash
set -e

# scenario_cascade.sh
# Multi-failure cascade: nginx upstream, postgres auth, and log flooding

# 1. Break nginx upstream — point to nonexistent backend
cat > /etc/nginx/sites-available/default << 'EOF'
upstream backend {
    server 127.0.0.1:9999;
}
server {
    listen 80;
    location / {
        proxy_pass http://backend;
    }
}
EOF
service nginx reload 2>/dev/null || service nginx restart 2>/dev/null || true

# 2. Break PostgreSQL — reject all connections via pg_hba.conf
PG_HBA=$(find /etc/postgresql -name pg_hba.conf 2>/dev/null | head -1)
if [ -n "$PG_HBA" ]; then
    cp "$PG_HBA" "${PG_HBA}.bak"
    echo "local all all reject" > "$PG_HBA"
    echo "host all all 0.0.0.0/0 reject" >> "$PG_HBA"
    service postgresql reload 2>/dev/null || true
fi

# 3. Start a cron-like log flooder
while true; do echo "CRON SPAM $(date)" >> /var/log/syslog 2>/dev/null; sleep 0.1; done &

echo "Alert: CRITICAL — Nginx upstream unreachable, PostgreSQL rejecting connections, logs flooding."
