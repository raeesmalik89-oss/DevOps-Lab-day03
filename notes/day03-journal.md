# Day 3 Journal — systemd, Services, Units and journalctl

## Learned

- systemd is the Linux service and process manager.
- systemd manages services as units.
- `.service`, `.timer`, `.socket`, `.mount` and `.target` are common unit types.
- Custom administrator units belong under `/etc/systemd/system/`.
- `systemctl status` is the first troubleshooting command.
- `journalctl -u <service>` shows service logs.
- `start` runs a service now.
- `enable` configures a service to start at boot.
- `daemon-reload` is required after changing a unit file.
- `Restart=on-failure` restarts a failed application.
- `RestartSec` provides restart backoff.
- `TimeoutStopSec` controls graceful shutdown time.
- `KillSignal=SIGTERM` supports graceful termination.
- `User=appuser` follows least privilege.
- Drop-in overrides allow selected settings to be changed without editing the base unit.
- systemd resource limits use cgroups.
- `ProtectSystem=strict` restricts writes to protected system paths.
- `ReadWritePaths` allows required writable locations.

## Broke

- Broken ExecStart path
- Missing systemd user
- Restart loop
- Restart=no behavior
- Memory limit experiment
- Missing daemon-reload
- Protected /etc write
- Start-limit protection

## Fixed by

- Checking `systemctl status`
- Checking `journalctl -u myapp`
- Correcting ExecStart
- Restoring User=appuser
- Running systemctl daemon-reload
- Using systemctl reset-failed
- Restoring the correct restart policy
- Using a systemd drop-in override
- Using systemd security hardening correctly

## Evidence from My Lab

### Service running

myapp.service successfully ran:

    /usr/bin/python3 /srv/myapp/app.py

### Health endpoint

    /health

returned:

    status = healthy
    version = 1.1.0

### Restart test

The /crash endpoint caused:

    status=1/FAILURE

and systemd restarted the service when:

    Restart=on-failure

### Restart=no test

The service remained failed after /crash when:

    Restart=no

### Bad user test

Using:

    User=nonexistentuser

produced:

    status=217/USER

### Start-limit test

Repeated failures produced:

    Start request repeated too quickly

### ProtectSystem test

Attempting to write to /etc produced:

    [Errno 30] Read-only file system

## Memory Drill Note

MemoryMax=10M was successfully applied.

The application reached approximately the configured limit, but this WSL environment did not produce confirmed OOM/OOM-kill evidence. Therefore I did not claim an OOM event without evidence.

The configuration was restored to:

    MemoryMax=256M

through the systemd drop-in override.

## Still Unclear

- PID 1 behavior inside containers
- Differences between systemd and container orchestration
- Advanced systemd dependency relationships
- Resource-control troubleshooting

## Production Mental Model

Filesystem
    ↓
Process
    ↓
Service
    ↓
systemd
    ↓
journalctl
    ↓
Troubleshooting
