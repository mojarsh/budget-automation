#!/usr/bin/bash
set -euo pipefail

# URL for ntfy push notifications
NTFY_URL="http://192.168.1.200:8446/homelab-alerts"
# Path configuration
BASE_DIR="${BUDGET_BASE_DIR:-$HOME/automation/budgeting}"
CREDS_DIR="${BUDGET_CREDS_DIR:-$BASE_DIR/creds}"
# Using /run/user/$(id -u) ensures this is a RAM-only location
TEMP_RAM="/run/user/$(id -u)/budget_tmp"

# Initialise temp RAM, vanishes on reboot
mkdir -p "$TEMP_RAM"
if ! mountpoint -q "$TEMP_RAM"; then
    sudo mount -t tmpfs -o size=1M tmpfs "$TEMP_RAM"
fi

# Decrypt secrets into temp RAM
sudo systemd-creds decrypt "$CREDS_DIR/budget-env.cred" > "$TEMP_RAM/.env"
sudo systemd-creds decrypt "$CREDS_DIR/google-json.cred" > "$TEMP_RAM/google_creds.json"

IMAGE="ghcr.io/mojarsh/budget-automation:latest"
sudo docker pull "$IMAGE"

# Run pipeline and notify on outcome
if CREDS_DIR="$TEMP_RAM" \
   GOOGLE_CREDS_PATH="$TEMP_RAM/google_creds.json" \
   BASE_DIR="$BASE_DIR" \
   sudo -E docker compose run --rm budget_automation; then
    curl -s \
        -H "Title: Budget automation complete" \
        -H "Priority: default" \
        -H "Tags: white_check_mark" \
        -d "Pipeline completed successfully" \
        "$NTFY_URL"
else
    curl -s \
        -H "Title: Budget automation failed" \
        -H "Priority: high" \
        -H "Tags: warning" \
        -d "Pipeline exited with an error — check journalctl for details" \
        "$NTFY_URL"
fi

sudo rm -rf "$TEMP_RAM"/*
sudo umount "$TEMP_RAM"
rmdir "$TEMP_RAM"
