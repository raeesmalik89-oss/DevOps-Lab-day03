# DevOps Lab — Day 3: systemd Services, Units & journalctl

![Linux](https://img.shields.io/badge/Linux-systemd-FCC624?logo=linux&logoColor=black)
![Python](https://img.shields.io/badge/Python-3-3776AB?logo=python&logoColor=white)
![Tools](https://img.shields.io/badge/tools-systemctl%20%7C%20journalctl-4EAA25?logo=gnubash&logoColor=white)

This lab runs a Python HTTP service the way production Linux hosts do: as a hardened, resource-limited **systemd
unit**. The unit starts at boot, restarts on failure, shuts down gracefully and logs to the journal. The lab then
breaks the service on purpose, eight different ways, and fixes each failure using only `systemctl status` and
`journalctl`.

Part of a hands-on DevOps Linux series:
[Day 1 — Filesystem & permissions](https://github.com/raeesmalik89-oss/DevOps-Lab-day01) ·
[Day 2 — Processes & signals](https://github.com/raeesmalik89-oss/DevOps-Lab-day02) ·
**Day 3 — systemd** ·
[Day 4 — Disk, memory & CPU](https://github.com/raeesmalik89-oss/DevOps-Lab-day04)

---

## Table of contents

- [What this lab demonstrates](#what-this-lab-demonstrates)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Deploy the service](#deploy-the-service)
- [Verify it works](#verify-it-works)
- [The unit file explained](#the-unit-file-explained)
- [Changing settings safely: drop-in overrides](#changing-settings-safely-drop-in-overrides)
- [Failure drills](#failure-drills)
- [Troubleshooting runbook](#troubleshooting-runbook)
- [Command reference](#command-reference)
- [Security notes](#security-notes)
- [Lab environment and limitations](#lab-environment-and-limitations)
- [Key takeaways](#key-takeaways)

---

## What this lab demonstrates

| Area | What was done |
|------|---------------|
| Service lifecycle | Created `myapp.service`; practised `start` vs `enable`, `stop`, `restart` and `daemon-reload` |
| Resilience | Automatic restart with `Restart=on-failure` and a 5 s delay; crash-loop protection with start limits |
| Graceful shutdown | The app handles `SIGTERM`; systemd waits up to 30 s before force-killing it |
| Least privilege | Runs as the unprivileged `appuser`, with `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict` and `ProtectHome` |
| Resource control | cgroup limits: `MemoryMax=512M` and `CPUQuota=50%` in the unit, tightened to 256M with a drop-in |
| Configuration | Settings read from `/etc/myapp/app.env`; only an example file is committed |
| Observability | stdout/stderr go to the journal under the identifier `myapp` |
| Troubleshooting | Eight induced failures diagnosed and fixed (see [Failure drills](#failure-drills)) |

## Architecture

```text
                 boot / systemctl start
                          │
                          ▼
┌──────────────────────── systemd (PID 1) ────────────────────────┐
│  myapp.service                                                  │
│    User=appuser · EnvironmentFile=/etc/myapp/app.env            │
│    cgroup: MemoryMax · CPUQuota     sandbox: ProtectSystem ...  │
│                                                                 │
│    ExecStart ─► /usr/bin/python3 /srv/myapp/app.py  (:8080)     │
│                    │  GET /health  GET /  GET /crash            │
│                    │                                            │
│    stdout/stderr ──┴──► journald ──► journalctl -u myapp        │
│    exit ≠ 0 ─────────► Restart=on-failure (after 5 s)           │
└─────────────────────────────────────────────────────────────────┘
```

The application ([`app/app.py`](app/app.py)) is a small Python HTTP server with no external dependencies:

| Endpoint | Response | Purpose |
|----------|----------|---------|
| `GET /health` | `{"status": "healthy", "version": "1.1.0"}` | Health check |
| `GET /` | `{"message": "hello from systemd", "version": "1.1.0"}` | Default route |
| `GET /crash` | The process exits with status 1 | Simulates a crash to test restart policies |

It reads `PORT` and `APP_VERSION` from the environment and exits cleanly on `SIGTERM` or `SIGINT`.

## Repository structure

```text
DevOps-Lab-day03/
├── app/
│   └── app.py                # Python HTTP service (health, root and crash endpoints)
├── code/
│   └── myapp.service         # systemd unit file
├── config/
│   └── app.env.example       # Example runtime configuration (the real file stays on the host)
├── notes/
│   └── day03-journal.md      # Lab journal: what I learned, broke and fixed, with evidence
├── .gitignore                # Excludes real env files, logs and Python caches
└── README.md
```

## Deploy the service

Requires a Linux host with systemd and Python 3. Run from the repository root.

```bash
# 1. Service account with no login shell
sudo useradd --system --no-create-home --shell /usr/sbin/nologin appuser

# 2. Application files, plus the one directory the sandbox lets it write to
sudo mkdir -p /srv/myapp/logs
sudo cp app/app.py /srv/myapp/app.py
sudo chown -R appuser:appuser /srv/myapp

# 3. Runtime configuration (kept outside the repository)
sudo mkdir -p /etc/myapp
sudo cp config/app.env.example /etc/myapp/app.env
sudo chmod 640 /etc/myapp/app.env

# 4. Install and start the unit
sudo cp code/myapp.service /etc/systemd/system/myapp.service
sudo systemctl daemon-reload
sudo systemctl enable --now myapp
```

> The `ReadWritePaths=/srv/myapp/logs` directory must exist before the service starts. If it is missing,
> systemd cannot set up the sandbox and the unit fails.

## Verify it works

```bash
systemctl status myapp --no-pager         # active (running), main PID, cgroup
curl -s localhost:8080/health | jq        # {"status": "healthy", "version": "1.1.0"}
journalctl -u myapp -n 20 --no-pager      # "starting on port 8080, version 1.1.0"
```

Test the restart policy:

```bash
curl -s localhost:8080/crash              # the process exits with status 1
journalctl -u myapp -f                    # failure logged, restart about 5 s later
```

## The unit file explained

[`code/myapp.service`](code/myapp.service)

| Section | Setting | Why |
|---------|---------|-----|
| `[Unit]` | `After=network-online.target`, `Wants=network-online.target` | Start once the network is up |
| `[Unit]` | `StartLimitBurst=5`, `StartLimitIntervalSec=60` | More than 5 starts within 60 s stops the crash loop |
| `[Service]` | `Type=simple` | The started process is the service |
| `[Service]` | `User=appuser`, `Group=appuser` | Least privilege: never run as root |
| `[Service]` | `WorkingDirectory=/srv/myapp`, `EnvironmentFile=/etc/myapp/app.env` | Code and configuration kept apart |
| `[Service]` | `Restart=on-failure`, `RestartSec=5s` | Restart after a crash, with a delay |
| `[Service]` | `KillSignal=SIGTERM`, `TimeoutStopSec=30s` | Graceful stop first; `SIGKILL` only after 30 s |
| `[Service]` | `StandardOutput=journal`, `SyslogIdentifier=myapp` | Logs go to journald with a clear tag |
| `[Service]` | `NoNewPrivileges=true`, `PrivateTmp=true` | No privilege escalation; a private `/tmp` |
| `[Service]` | `ProtectSystem=strict`, `ProtectHome=true`, `ReadWritePaths=/srv/myapp/logs` | Read-only OS and no home directories, except the one log path |
| `[Service]` | `MemoryMax=512M`, `CPUQuota=50%` | cgroup limits so one service cannot starve the host |
| `[Install]` | `WantedBy=multi-user.target` | `enable` makes it start at boot |

## Changing settings safely: drop-in overrides

The base unit is never edited in place. Changes go into a drop-in file, which survives updates to the original:

```bash
sudo systemctl edit myapp
```

```ini
# /etc/systemd/system/myapp.service.d/override.conf
[Service]
MemoryMax=256M
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart myapp
systemctl show myapp -p MemoryMax         # MemoryMax=268435456 (256M)
systemctl cat myapp                       # the base unit followed by the override
```

## Failure drills

Each failure was caused on purpose, diagnosed from `systemctl status` and `journalctl -u myapp`, then fixed.
The evidence is recorded in [`notes/day03-journal.md`](notes/day03-journal.md).

| # | Failure introduced | What systemd reported | Fix |
|---|--------------------|-----------------------|-----|
| 1 | Wrong path in `ExecStart` | The unit failed to start; the cause was shown in `journalctl` | Corrected `ExecStart`, then `daemon-reload` and restart |
| 2 | `User=nonexistentuser` | `status=217/USER` | Restored `User=appuser` |
| 3 | `/crash` with `Restart=on-failure` | `status=1/FAILURE`, then an automatic restart | Expected behaviour: policy verified |
| 4 | `/crash` with `Restart=no` | The service stayed `failed` | Restored `Restart=on-failure` |
| 5 | Repeated crashes | `Start request repeated too quickly` | `systemctl reset-failed myapp`, then fixed the cause |
| 6 | Unit edited without a reload | The old configuration stayed active | `systemctl daemon-reload` |
| 7 | Write to `/etc` under `ProtectSystem=strict` | `[Errno 30] Read-only file system` | Write only to `ReadWritePaths` |
| 8 | `MemoryMax=10M` | Memory held near the limit (see [limitations](#lab-environment-and-limitations)) | Restored to 256M with the drop-in |

## Troubleshooting runbook

```text
1. systemctl status myapp --no-pager        which state, which exit code, when
2. journalctl -u myapp -n 50 --no-pager     what the app and systemd logged
3. systemctl cat myapp                      which unit and drop-ins are active
4. fix the application or the unit
5. systemctl daemon-reload                  if a unit file changed
6. systemctl reset-failed myapp             if the start limit was hit
7. systemctl restart myapp
8. curl -s localhost:8080/health            confirm it is healthy
```

Exit codes seen in this lab: `1/FAILURE` (the app exited with an error) and `217/USER` (the configured user
does not exist).

## Command reference

| Task | Command |
|------|---------|
| Start / stop / restart | `systemctl start\|stop\|restart myapp` |
| Start at boot, and now | `systemctl enable --now myapp` |
| Status | `systemctl status myapp` |
| Reload unit files | `systemctl daemon-reload` |
| Show the effective unit | `systemctl cat myapp` |
| Show one property | `systemctl show myapp -p MemoryMax` |
| Create a drop-in | `systemctl edit myapp` |
| Clear the failed state | `systemctl reset-failed myapp` |
| Recent logs | `journalctl -u myapp -n 30 --no-pager` |
| Follow logs | `journalctl -u myapp -f` |

## Security notes

- The service runs as a dedicated system account, never as root.
- The filesystem sandbox leaves exactly one writable path: `/srv/myapp/logs`.
- Real configuration lives in `/etc/myapp/app.env` on the host. Only `config/app.env.example` is committed, and
  `.gitignore` excludes `app.env`, `.env` and log files.

## Lab environment and limitations

- Run on Linux with systemd under WSL.
- **Memory drill:** `MemoryMax=10M` was applied and the process stayed near the limit, but this WSL environment
  produced no confirmed OOM kill, so none is claimed. On a standard Linux host, exceeding the limit typically
  ends in an OOM kill that the journal records.
- The `Documentation=` URL in the unit is a placeholder for a real runbook link.

## Key takeaways

- `start` runs a service now; `enable` makes it start at boot. Production services need both.
- `After=` only controls order; `Requires=` and `Wants=` declare dependencies.
- Every unit-file change needs `systemctl daemon-reload`.
- `Restart=on-failure`, a restart delay and start limits give self-healing without endless crash loops.
- Graceful shutdown needs both sides: systemd sends `SIGTERM`, and the application must handle it.
- Drop-ins change behaviour without touching the original unit.
- A dedicated `User=`, sandboxing and cgroup limits cost little and contain the damage from a bug or a compromise.
- `systemctl status` and `journalctl -u` answer most service incidents.

---

**Author:** [Muhammad Raees](https://github.com/raeesmalik89-oss) — AIOps / DevOps Engineer
