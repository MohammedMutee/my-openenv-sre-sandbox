#!/bin/bash
set -e

# scenario_resource.sh
# Simulate resource exhaustion — fill /tmp and spawn CPU consumers

# Fill /tmp with many small files
for i in $(seq 1 5000); do
    dd if=/dev/urandom of=/tmp/junk_${i} bs=1K count=10 2>/dev/null
done

# Spawn background CPU consumers
for i in $(seq 1 4); do
    yes > /dev/null 2>&1 &
done

echo "Alert: Server extremely slow. /tmp is nearly full and rogue processes consuming CPU."
