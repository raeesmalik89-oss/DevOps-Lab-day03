
# DevOps Lab — Day 3
## systemd, Services, Units & journalctl

Hands-on Linux service management and production troubleshooting using systemd.

## Objectives

- Understand systemd and PID 1
- Create and manage systemd services
- Configure restart and graceful shutdown behavior
- Use systemctl and journalctl
- Manage dependencies and environment files
- Apply security hardening
- Configure CPU and memory limits with cgroups
- Use drop-in overrides
- Troubleshoot service failures

## Project Structure

```text
day03/
├── README.md
├── .gitignore
├── app/
│   └── app.py
├── code/
│   └── myapp.service
├── config/
│   └── app.env.example
└── notes/
    └── day03-journal.md
```

## Service

Service: `myapp.service`

Application: `/srv/myapp/app.py`

Configuration: `/etc/myapp/app.env`

Port: `8080`

User: `appuser`

Version: `1.1.0`

## Key Configuration

```ini
User=appuser
Group=appuser
ExecStart=/usr/bin/python3 /srv/myapp/app.py

Restart=on-failure
RestartSec=5s

TimeoutStopSec=30s
KillSignal=SIGTERM

ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/srv/myapp/logs

MemoryMax=512M
CPUQuota=50%

StartLimitBurst=5
StartLimitIntervalSec=60
```

## Drop-in Override

The service was safely overridden using:

`/etc/systemd/system/myapp.service.d/override.conf`

```ini
[Service]
MemoryMax=256M
```

Verify the effective value:

```bash
systemctl show myapp -p MemoryMax
```

## Important Commands

```bash
systemctl status myapp
systemctl start myapp
systemctl stop myapp
systemctl restart myapp
systemctl enable myapp
systemctl disable myapp
systemctl daemon-reload
systemctl show myapp
systemctl cat myapp
systemctl edit myapp

journalctl -u myapp
journalctl -u myapp -n 30 --no-pager
journalctl -u myapp -f
```

## Application Tests

```bash
curl -s localhost:8080/health | jq
curl -s localhost:8080/ | jq
curl localhost:8080/crash
```

Expected health response:

```json
{
  "status": "healthy",
  "version": "1.1.0"
}
```

## Practical Exercises Completed

- Systemd service creation and management
- Automatic restart with `Restart=on-failure`
- Graceful shutdown using SIGTERM
- `start` vs `enable`
- `daemon-reload` behavior
- Drop-in overrides
- Broken `ExecStart` troubleshooting
- Invalid service user troubleshooting
- `Restart=no` behavior
- Start-limit protection
- Memory-limit investigation
- `ProtectSystem=strict` filesystem protection

## Troubleshooting Workflow

```text
systemctl status myapp
        ↓
journalctl -u myapp
        ↓
identify the failure
        ↓
fix application/configuration
        ↓
daemon-reload
        ↓
restart
        ↓
verify
        ↓
test /health
```

## Key Lessons

- `start` = run now
- `enable` = start at boot
- `After=` = ordering
- `Requires=` = dependency
- `Restart=on-failure` = restart after failure
- `RestartSec=` = restart delay
- `TimeoutStopSec=` = graceful shutdown timeout
- `KillSignal=SIGTERM` = graceful termination
- `daemon-reload` = reload changed unit configuration
- `journalctl -u` = service logs
- Drop-ins = service overrides
- `User=` = least privilege
- `MemoryMax=` = memory limit
- `CPUQuota=` = CPU limit
- `ProtectSystem=strict` = filesystem protection
- `StartLimit*` = crash-loop protection

## Security

The service runs as the non-root user `appuser`.

Sensitive runtime configuration is kept outside the Git repository.

Only the example configuration is committed:

```text
config/app.env.example
```

Real environment files and secrets are excluded through `.gitignore`.

## Result

Day 3 demonstrates practical systemd service management, monitoring,
restart policies, graceful shutdown, security hardening, resource control,
drop-in overrides, journald logging, and production-style troubleshooting.
