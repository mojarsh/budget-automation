#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# budget-automation host setup script
# Run once on a new server from the project root after cloning the repository.
# Usage: bash infra/setup.sh
# =============================================================================

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
info()    { echo "[INFO]  $*"; }
success() { echo "[OK]    $*"; }
error()   { echo "[ERROR] $*" >&2; exit 1; }
confirm() {
    read -rp "$* [y/N] " response
    [[ "$response" =~ ^[Yy]$ ]] || error "Aborted."
}

# -----------------------------------------------------------------------------
# Verify script is run from the project root
# -----------------------------------------------------------------------------
[[ -f "infra/run_budgeting.sh" ]] || error "Run this script from the project root: bash infra/setup.sh"

# -----------------------------------------------------------------------------
# Collect user input
# -----------------------------------------------------------------------------
echo
echo "============================================="
echo " budget-automation host setup"
echo "============================================="
echo

read -rp "Service username: " SERVICE_USER
SERVICE_UID=$(id -u "$SERVICE_USER" 2>/dev/null) || error "User '$SERVICE_USER' not found."
SERVICE_HOME=$(eval echo "~$SERVICE_USER")
PROJECT_ROOT="$(pwd)"
TEMP_RAM="/run/user/${SERVICE_UID}/budget_tmp"

echo
info "Service user:  $SERVICE_USER (uid=$SERVICE_UID)"
info "Project root:  $PROJECT_ROOT"
info "Temp RAM path: $TEMP_RAM"
echo
confirm "Proceed with setup?"

# -----------------------------------------------------------------------------
# 1. Shell script permissions
# -----------------------------------------------------------------------------
info "Setting run script permissions..."
chmod +x infra/run_budgeting.sh
success "infra/run_budgeting.sh is executable"

# -----------------------------------------------------------------------------
# 2. Group
# -----------------------------------------------------------------------------
info "Creating budget-automation group..."
if getent group budget-automation > /dev/null 2>&1; then
    info "Group budget-automation already exists, skipping"
else
    sudo groupadd budget-automation
    success "Created group budget-automation"
fi

info "Adding $SERVICE_USER to budget-automation group..."
sudo usermod -aG budget-automation "$SERVICE_USER"
success "$SERVICE_USER added to budget-automation"

# -----------------------------------------------------------------------------
# 3. Sudoers
# -----------------------------------------------------------------------------
info "Installing sudoers file..."
sudo cp infra/sudoers/budget-automation /etc/sudoers.d/budget-automation
sudo chmod 0440 /etc/sudoers.d/budget-automation
sudo visudo -c -f /etc/sudoers.d/budget-automation || error "Sudoers file failed validation"
success "Sudoers file installed and validated"

# -----------------------------------------------------------------------------
# 4. Runtime directory (tmpfiles)
# -----------------------------------------------------------------------------
info "Creating tmpfiles rule for runtime directory..."
sudo tee /etc/tmpfiles.d/budget-automation.conf > /dev/null << EOF
d /run/user/${SERVICE_UID}/budget_tmp 0700 ${SERVICE_USER} ${SERVICE_USER} -
EOF
sudo systemd-tmpfiles --create /etc/tmpfiles.d/budget-automation.conf
success "Runtime directory rule created"

# -----------------------------------------------------------------------------
# 5. Loginctl linger (keeps /run/user/UID alive without an active session)
# -----------------------------------------------------------------------------
info "Enabling loginctl linger for $SERVICE_USER..."
sudo loginctl enable-linger "$SERVICE_USER"
success "Linger enabled for $SERVICE_USER"

# -----------------------------------------------------------------------------
# 6. Systemd service and timer
# -----------------------------------------------------------------------------
info "Installing systemd unit files..."
sudo cp infra/systemd/budget-automation.service /etc/systemd/system/
sudo cp infra/systemd/budget-automation.timer /etc/systemd/system/
success "Unit files installed"

info "Creating systemd drop-in override..."
sudo mkdir -p /etc/systemd/system/budget-automation.service.d/
sudo tee /etc/systemd/system/budget-automation.service.d/override.conf > /dev/null << EOF
[Service]
User=${SERVICE_USER}
WorkingDirectory=${PROJECT_ROOT}
ExecStart=
ExecStart=${PROJECT_ROOT}/infra/run_budgeting.sh
EOF
success "Drop-in override created"

info "Reloading systemd and enabling timer..."
sudo systemctl daemon-reload
sudo systemctl enable --now budget-automation.timer
success "Timer enabled"

# Verify ExecStart resolves correctly
EXEC_COUNT=$(systemctl show budget-automation.service | grep -c "^ExecStart=")
[[ "$EXEC_COUNT" -eq 1 ]] || error "Multiple ExecStart entries detected — check the drop-in override"
success "ExecStart resolves correctly"

# -----------------------------------------------------------------------------
# 7. Credentials
# -----------------------------------------------------------------------------
echo
info "Credential setup must be done manually — see infra/README.md step 6."
info "Required files: secrets.env and google_creds.json"
info "Encrypt with:"
echo "  CREDS_DIR=\"\$HOME/automation/budgeting/creds\""
echo "  mkdir -p \"\$CREDS_DIR\""
echo "  sudo systemd-creds encrypt secrets.env \"\$CREDS_DIR/budget-env.cred\""
echo "  sudo systemd-creds encrypt google_creds.json \"\$CREDS_DIR/google-json.cred\""
echo "  shred -u secrets.env google_creds.json"

# -----------------------------------------------------------------------------
# 8. Docker image
# -----------------------------------------------------------------------------
info "Pulling latest Docker image..."
sudo /usr/bin/docker pull ghcr.io/mojarsh/budget-automation:latest
success "Docker image pulled"


# -----------------------------------------------------------------------------
# 9. Docker compose config verification
# -----------------------------------------------------------------------------
info "Validating docker compose configuration..."
DUMMY_CREDS="/tmp/budget_validate_$$"
mkdir -p "$DUMMY_CREDS"
touch "$DUMMY_CREDS/.env" "$DUMMY_CREDS/google_creds.json"

CREDS_DIR="$DUMMY_CREDS" \
GOOGLE_CREDS_PATH="$DUMMY_CREDS/google_creds.json" \
BASE_DIR="$SERVICE_HOME/automation/budgeting" \
  docker compose config > /dev/null || { rm -rf "$DUMMY_CREDS"; error "docker compose config validation failed"; }

rm -rf "$DUMMY_CREDS"
success "Docker compose configuration is valid"
# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo
echo "============================================="
echo " Setup complete"
echo "============================================="
echo
echo "Next steps:"
echo "  1. Encrypt credentials (see above)"
echo "  2. Verify the service runs manually:"
echo "     sudo systemctl start budget-automation.service"
echo "     journalctl -u budget-automation.service --no-pager"
echo "  3. Verify the timer is scheduled:"
echo "     systemctl status budget-automation.timer"
echo

