#!/bin/bash
set -e

# scenario_hard.sh
# Simulate filled disk by generating a large dummy log file and break postgres

# Create a 500MB dummy file to simulate disk pressure (reduced from 2GB for faster testing)
dd if=/dev/zero of=/var/log/nginx/access.log bs=1M count=500

# Stop PostgreSQL and corrupt its port config
service postgresql stop
sed -i 's/port = 5432/port = 0000/g' /etc/postgresql/14/main/postgresql.conf 2>/dev/null || true

echo "Alert: High disk usage observed, database connection refused, and web server latency high."
