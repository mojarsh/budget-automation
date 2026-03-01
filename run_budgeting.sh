#!/usr/bin/bash
set -e

# Path configuration
BASE_DIR="/home/USER/automation/budgeting"
CREDS_DIR="$BASE_DIR/creds"
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

# Main Docker command
sudo docker run --rm -d \
  --name budget_automation \
  --env-file "$TEMP_RAM/.env" \
  -v "$TEMP_RAM/google_creds.json:/app/google_creds.json:ro" \
  -v "$BASE_DIR/logs/budget_automation.log:/app/budget_automation.log" \
  -v "$BASE_DIR/transactions.db:/app/transactions.db" \
  budget_automation:latest

# Wait for container to start, then wipe temp RAM
sleep 2
sudo rm -rf "$TEMP_RAM"/*
sudo umount "$TEMP_RAM"
rmdir "$TEMP_RAM"
