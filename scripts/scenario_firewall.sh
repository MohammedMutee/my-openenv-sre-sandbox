#!/bin/bash
set -e

# scenario_firewall.sh
# Block web traffic using iptables rules

iptables -A INPUT -p tcp --dport 80 -j DROP 2>/dev/null || true
iptables -A INPUT -p tcp --dport 443 -j DROP 2>/dev/null || true

echo "Alert: Web traffic on ports 80 and 443 is being dropped by firewall rules."
