#!/bin/bash
set -e

# scenario_permissions.sh
# Break nginx by changing file permissions

# Make web root unreadable by nginx worker
chmod 000 /var/www/html 2>/dev/null || true

# Make nginx config unreadable
chmod 000 /etc/nginx/sites-available/default 2>/dev/null || true

# Restart nginx (it will start but serve 403)
service nginx restart 2>/dev/null || true

echo "Alert: Nginx is returning 403 Forbidden. Permissions appear incorrect."
