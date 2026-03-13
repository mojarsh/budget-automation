# infra

Host-level configuration for the budget automation pipeline. No usernames or hardcoded paths are present in the versioned files — all user-specific configuration is applied on the host via the steps below.

## Installation

### 1. Shell script permissions
```bash
chmod +x infra/run_budgeting.sh
```

### 2. Group
```bash
sudo groupadd budget-automation
sudo usermod -aG budget-automation YOUR_USERNAME
```

### 3. Sudoers
Git does not preserve file permissions — `0440` must be set manually:
```bash
sudo cp infra/sudoers/budget-automation /etc/sudoers.d/
sudo chmod 0440 /etc/sudoers.d/budget-automation
sudo visudo -c -f /etc/sudoers.d/budget-automation
```

### 4. Systemd
The versioned service file contains no username or paths. A drop-in override supplies these on the host. The empty `ExecStart=` line is required — systemd appends rather than replaces `ExecStart` across files, so the base value must be explicitly cleared first:
```bash
sudo cp infra/systemd/budget-automation.service /etc/systemd/system/
sudo cp infra/systemd/budget-automation.timer /etc/systemd/system/

sudo mkdir -p /etc/systemd/system/budget-automation.service.d/
sudo tee /etc/systemd/system/budget-automation.service.d/override.conf << OVERRIDE
[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/automation/budget-automation
ExecStart=
ExecStart=/home/YOUR_USERNAME/automation/budget-automation/infra/run_budgeting.sh
OVERRIDE

sudo systemctl daemon-reload
sudo systemctl enable --now budget-automation.timer
```

Verify the resolved configuration — confirm only one `ExecStart` entry is present pointing at the correct path:
```bash
systemctl show budget-automation.service | grep -E "ExecStart|User|WorkingDirectory"
```

### 5. Credentials
See `.env.example` in the project root for required fields. Encrypt and securely delete the plaintext files:
```bash
CREDS_DIR="$HOME/automation/budgeting/creds"
mkdir -p "$CREDS_DIR"

sudo systemd-creds encrypt secrets.env "$CREDS_DIR/budget-env.cred"
sudo systemd-creds encrypt google_creds.json "$CREDS_DIR/google-json.cred"
shred -u secrets.env google_creds.json
```

Verify decryption works correctly:
```bash
sudo systemd-creds decrypt "$CREDS_DIR/budget-env.cred" - | head -3
```

> **Note:** Encrypted `.cred` files are cryptographically bound to the machine they were created on. When migrating to a new server, credentials must be re-encrypted — the old `.cred` files cannot be transferred.

### 6. Docker image
```bash
docker pull ghcr.io/mojarsh/budget-automation:latest
```

---

## Verifying the installation
```bash
sudo systemctl start budget-automation.service
journalctl -u budget-automation.service --no-pager
```

---

## Monitoring
```bash
systemctl status budget-automation.timer        # next scheduled run
journalctl -u budget-automation.service         # logs from last run
journalctl -u budget-automation.service -f      # follow logs in real time
```

The timer runs at 00:00, 06:00, 12:00, and 18:00 UTC. `Persistent=true` means if the machine was off at a scheduled time, the job runs immediately on next boot.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `203/EXEC` | `ExecStart` resolves to wrong path or two entries present | Ensure override contains empty `ExecStart=` before the real value. Run `systemctl show budget-automation.service \| grep ExecStart` to inspect |
| `no configuration file provided` | `WorkingDirectory` missing or incorrect | Confirm override `WorkingDirectory` points to the project root |
| `permission denied` on Docker socket | User not in `docker` group or sudoers misconfigured | Check `groups YOUR_USERNAME` and `sudo visudo -c -f /etc/sudoers.d/budget-automation` |
| `env file not found` | Filename mismatch between script and `docker-compose.yml` | Ensure both reference the same filename for the decrypted credential |
| Credentials fail to decrypt | `.cred` files are machine-specific | Re-encrypt on the new machine |
