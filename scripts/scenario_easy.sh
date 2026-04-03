#!/bin/bash
# scenario_easy.sh
# Intentionally stop nginx to simulate a simple service failure

service nginx stop
echo "Alert: Nginx is unresponsive on port 80"
