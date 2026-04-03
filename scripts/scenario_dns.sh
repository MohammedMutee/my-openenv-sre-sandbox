#!/bin/bash
set -e

# scenario_dns.sh
# Break DNS resolution by corrupting resolv.conf

# Backup and destroy DNS config
cp /etc/resolv.conf /etc/resolv.conf.bak
echo "# DNS has been sabotaged" > /etc/resolv.conf

echo "Alert: DNS resolution is completely broken. No hostnames can be resolved."
