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

### 4. Runtime directory

The script mounts a RAM-only tmpfs at `/run/user/UID/budget_tmp` to hold decrypted credentials. This path is wiped on every reboot — a tmpfiles rule ensures it is recreated automatically on boot. Without this, the service will fail after any reboot.

Replace `YOUR_UID` with the numeric user ID of the service user (find it with `id -u YOUR_USERNAME`):

```bash
sudo tee /etc/tmpfiles.d/budget-automation.conf << EOF
d /run/user/YOUR_UID/budget_tmp 0700 YOUR_USERNAME YOUR_USERNAME -
EOF

sudo systemd-tmpfiles --create /etc/tmpfiles.d/budget-automation.conf
```

Verify the directory was created:

```bash
ls -la /run/user/YOUR_UID/budget_tmp
```

### 5. Systemd
The versioned service file contains no username or paths. A drop-in override supplies these on the host. The empty `ExecStart=` line is required — systemd appends rather than replaces `ExecStart` across files, so the base value must be explicitly cleared first:
```bash
sudo cp infra/systemd/budget-automation.service /etc/systemd/system/
sudo cp infra/systemd/budget-automation.timer /etc/systemd/system/

sudo mkdir -p /etc/systemd/system/budget-automation.service.d/
sudo tee /etc/systemd/system/budget-automation.service.d/override.conf << OVERRIDE
[Service]
User=YOUR_USERNAME
WorkingDirectory=/path/to/project/root
ExecStart=
ExecStart=/path/to/project/root/infra/run_budgeting.sh
Environment=BUDGET_BASE_DIR=/path/to/project/root
Environment=BUDGET_CREDS_DIR=/path/to/project/root/creds
OVERRIDE

sudo systemctl daemon-reload
sudo systemctl enable --now budget-automation.timer
```

Verify the resolved configuration — confirm only one `ExecStart` entry is present pointing at the correct path:
```bash
systemctl show budget-automation.service | grep -E "ExecStart|User|WorkingDirectory"
```

### 6. Credentials
See `.env.example` in the project root for required fields. Encrypt and securely delete the plaintext files:
```bash
CREDS_DIR="$(pwd)/creds"
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

### 7. Docker image
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

### 8. Database migration (new server only)

If migrating from an existing server, restore the database before
starting the full service. Start postgres with inline credentials
to avoid the credential decryption dependency:

    # Create a temporary placeholder .env so docker compose validates
    touch .env

    # Start only the postgres container
    POSTGRES_USER=youruser \
    POSTGRES_PASSWORD=yourpassword \
    POSTGRES_DB=tcpostgres \
    docker compose up -d db

    # Restore the dump
    docker exec -i postgres_db psql -U youruser tcpostgres \
      < /tmp/budget_db_YYYYMMDD.sql

    # Verify row counts
    docker exec postgres_db psql -U youruser tcpostgres \
      -c "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC"

    # Bring down and replace .env with encrypted credentials
    docker compose down
    shred -u .env

Note: encrypted .cred files must be re-created on the new machine
before running the full service.

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
| Service fails after reboot | `/run/user/UID/budget_tmp` wiped on reboot | Ensure tmpfiles rule exists and ran: `sudo systemd-tmpfiles --create /etc/tmpfiles.d/budget-automation.conf` |
