# STEER — AI-Powered Business Management Platform

**Take Control. Move Your Business Forward.**

STEER is an AI-powered business management platform designed to help business owners manage operations, monitor performance, and make smarter decisions. Stages 1 and 2 established the product foundation and responsive frontend. Stage 3 adds real email-verified account authentication, revocable sessions, password recovery, and a business-membership authorization foundation. Stage 4 is in progress: customer management uses tenant-scoped backend records; other workspace data remains demonstration content until its module is implemented. The AI assistant is not connected.

This project is independent of Don Prosy AI. No code or files have been copied from that product.

## Technology

- Frontend: React, Vite, JavaScript, and CSS
- Backend: Python, Flask, and a versioned REST API
- Data layer: SQLAlchemy; SQLite for local development and PostgreSQL planned for production
- Configuration: environment variables loaded locally from an untracked `.env` file

## Project layout

```text
backend/
  app/
    models/                 # Identity, membership, session, token, and customer entities
    routes/                 # Health, authentication, and business customer API routes
    services/               # Auth, customer validation/operations, and email services
  migrations/               # Versioned Alembic database migrations
  instance/                 # Local SQLite database files (not committed)
  run.py                    # Flask development entry point
frontend/
  src/
    assets/                 # Locally managed visual assets
    components/              # Shared UI elements, icons, and charts
    hooks/
    layouts/                # Application shell
    pages/                   # Marketing, authentication, and workspace views
    services/               # Same-origin JSON API clients, including customer management
    context/                # Authenticated user state
    styles/                  # Design tokens and responsive styles
docs/
  API.md
  ARCHITECTURE.md
  DATABASE.md
  PRODUCT_REQUIREMENTS.md
  SECURITY.md
STAGE_ROADMAP.md
STAGE_1_REPORT.md
STAGE_2_REPORT.md
STAGE_3_REPORT.md
```

## Run locally

Prerequisites: a supported Python 3 installation, Node.js (LTS recommended), and npm.

### Backend

From `backend`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
flask --app run db upgrade
python run.py
```

Before running, edit the ignored `backend/.env`: replace the local placeholder `SECRET_KEY` with a random value, set `RESEND_API_KEY`, and set `MAIL_FROM` to a sender address verified with Resend. Do not commit credentials. SMTP settings are optional and only used for non-OTP account notifications.

Generate a local secret in PowerShell with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The API listens on `http://127.0.0.1:5000`. Verify health with:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/v1/health
```

The response should contain `status: healthy`. The health route does not access or modify business data.

### Frontend

In a second terminal, from `frontend`:

```powershell
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). The Vite development server proxies `/api` requests to Flask.

## Account and workspace

The public landing page is at `/`. Real account screens are available at `/login`, `/register`, and `/forgot-password`. Registration sends a six-digit verification OTP, then signs in and opens the dashboard after successful verification. Login checks the password, sends a separate six-digit OTP, and creates a session only after that code is verified. Password recovery uses its own OTP. `/app/*` routes require a verified account and sign-in. The overview and business modules other than customers still display labelled sample data. See [STAGE_4_REPORT.md](STAGE_4_REPORT.md) for incremental implementation status and instructor migration handoff.

Authentication OTPs expire after ten minutes, are limited to five incorrect attempts, and can be resent after a 60-second cooldown. OTPs are sent through Resend; failed registration email delivery rolls back the pending account and membership.

Pricing is intentionally shown as “Coming soon.” Payment processing and AI responses are not connected. See [STAGE_2_REPORT.md](STAGE_2_REPORT.md) for completed interface details and verification results.

## Configuration

Copy `backend/.env.example` to `backend/.env` for local settings. Never commit `.env` or production credentials. Production startup also requires a strong secret key, HTTPS `PUBLIC_APP_URL`, Resend API key and verified sender, and shared rate-limit storage (for example a managed Redis-compatible endpoint). The Flask development server is for local use only.

## Stage boundaries

Stage 3 implements account authentication and the identity/membership schema. Stage 4 is incremental; consult [STAGE_4_REPORT.md](STAGE_4_REPORT.md) for implemented scope, outstanding modules, verification evidence, and production database handoff requirements. Architecture and interface details are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/API.md](docs/API.md), [docs/DATABASE.md](docs/DATABASE.md), [docs/SECURITY.md](docs/SECURITY.md), and [STAGE_ROADMAP.md](STAGE_ROADMAP.md).
