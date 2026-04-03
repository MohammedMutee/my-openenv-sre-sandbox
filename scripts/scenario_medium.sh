#!/bin/bash
# scenario_medium.sh
# Corrupt the nginx configuration to simulate a bad deployment

echo "server { listen 80; location / { syntax_error_here; } }" > /etc/nginx/sites-available/default
service nginx reload 2>/dev/null || service nginx restart 2>/dev/null

echo "Alert: Nginx fails to start due to configuration error"
