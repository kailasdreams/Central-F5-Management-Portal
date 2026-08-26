# F5 Central Management Portal

A standalone NOC-style portal for managing F5 BIG-IP devices across
`DC_SIFY`, `DR_BCP`, and `DC_CHAND` (or any sites you define).

**Stack:** FastAPI backend (JWT auth, encrypted credential vault, iControl
REST + SSH drivers, APScheduler) + Streamlit frontend, same pattern as your
SNOMS / FortiGate Policy Manager builds.

## Capabilities

| # | Capability | How it's implemented |
|---|------------|----------------------|
| 1 | Device management | Full CRUD inventory, per-device connection test, credentials encrypted at rest (Fernet) |
| 2 | GUI + CLI access | GUI: secure one-click launch link to native TMUI (F5's own frame-busting headers prevent iframe embedding — this is documented in-app). CLI: real interactive SSH terminal (xterm.js over WebSocket) **and** a structured tmsh command runner with quick-command buttons |
| 3 | Log summary | SSH-pulled `/var/log/{ltm,gtm,audit,secure,apm,asm}`, parsed and summarized by severity + process, filterable table |
| 4 | Backup (manual/auto) | UCS backup via iControl REST, downloaded and stored locally, optional SCP push to a remote backup server, cron-based auto-schedules (APScheduler) with retention pruning, full backup history + download |

All device changes, CLI sessions, GUI launches, backup runs, and logins are
written to an audit log (Settings → Audit Log, admin only).

## Quick Start (local, no Docker)

```bash
# 1. Generate secrets
python generate_keys.py
# copy the two printed lines into backend/.env (create it from backend/.env.example)

# 2. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export BACKEND_URL=http://localhost:8000
streamlit run streamlit_app.py
```

First login: **admin / admin123** — the app prints this once at first
startup. Change it immediately via Settings → User Management (create a new
admin user, then optionally disable/remove the seed admin — a password-change
endpoint can be added if you want in-place rotation instead).

## Quick Start (Docker Compose)

```bash
python generate_keys.py            # copy output into backend/.env
docker compose up --build -d
```

- Backend: http://localhost:8000/docs (OpenAPI/Swagger)
- Frontend: http://localhost:8501

## Notes on design decisions

- **GUI embedding**: F5 TMUI sends `X-Frame-Options`/CSP headers that block
  iframe embedding by design (security hardening on the device itself). The
  portal opens TMUI in a new tab instead of faking an embed — trying to strip
  those headers would mean modifying each device's httpd config, which isn't
  advisable to script as a side effect of a management portal.
- **CLI safety**: the structured command runner blocks a small set of
  obviously destructive shell tokens (`rm -rf`, fork bombs, etc.) but is not
  a full command allowlist — treat operator/admin accounts on this portal
  with the same care as direct SSH access, since the interactive terminal is
  a real shell.
- **Backup transport**: UCS files are pulled via iControl REST
  (`/mgmt/tm/sys/ucs` + `/mgmt/shared/file-transfer/ucs-downloads/`), not
  SCP, since that's the standard supported API path for UCS lifecycle. SCP
  is used only for the optional *remote push* leg to your own backup server.
- **RBAC**: `admin` (full control incl. user mgmt & device delete),
  `operator` (day-to-day: devices, CLI, backups, logs), `viewer` (read-only).

## Extending

- Add GTM/GSLB-specific views (wide-IPs, pool status) — you already have the
  iControl REST client (`app/services/f5_client.py`) to build on.
- Add Slack/email alerting on backup failure by hooking into
  `backup_service.run_backup()`.
- If you later want true SSO-style GUI embedding, that requires F5 APM SSO
  configuration on each device — happy to help wire that up as a follow-on.
