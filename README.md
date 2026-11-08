# Don Prosy Business Manager

Don Prosy Business Manager is a SaaS product for small business owners. Stages 1 and 2 established the product foundation and responsive frontend. Stage 3 adds real email-verified account authentication, revocable sessions, password recovery, and a business-membership authorization foundation. Workspace business data remains a clearly labelled frontend demonstration.

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
    models/                 # User, business, membership, session, and auth-token entities
    routes/                 # Health and authentication API routes
    services/               # Auth, password, and SMTP email services
  migrations/               # Versioned Alembic database migrations
  instance/                 # Local SQLite database files (not committed)
  run.py                    # Flask development entry point
frontend/
  src/
    assets/                 # Locally managed visual assets
    components/              # Shared UI elements, icons, and charts
    hooks/
    layouts/                # Application shell
    pages/                   # Marketing, authentication, and demo views
    services/               # Same-origin JSON API clients
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

Before running, edit the ignored `backend/.env`: replace the local placeholder `SECRET_KEY` with a random value, and configure an SMTP server (`MAIL_SERVER`, `MAIL_PORT`, `MAIL_FROM`, and any required credentials) for registration, verification, and password recovery. Use a provider-neutral SMTP account; do not commit credentials. The example uses STARTTLS on port 587.

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

The public landing page is at `/`. Real account screens are available at `/login`, `/register`, and `/forgot-password`. Registration sends a six-digit verification OTP, then signs in and opens the dashboard after successful verification. Password recovery uses a separate six-digit OTP. `/app/*` routes require a verified account and sign-in. The dashboard still displays labelled sample data and is not connected to business-management APIs.

Verification and reset OTPs expire after ten minutes, are limited to five incorrect attempts, and can be re-requested after a 60-second cooldown. Email operations require a working SMTP configuration; failed registration email delivery rolls back the pending account and membership.

Pricing is intentionally shown as “Coming soon.” Payment processing and AI responses are not connected. See [STAGE_2_REPORT.md](STAGE_2_REPORT.md) for completed interface details and verification results.

## Configuration

Copy `backend/.env.example` to `backend/.env` for local settings. Never commit `.env` or production credentials. Production startup also requires a strong secret key, HTTPS `PUBLIC_APP_URL`, SMTP configuration, and shared rate-limit storage (for example a managed Redis-compatible endpoint). The Flask development server is for local use only.

## Stage boundaries

Stage 3 implements account authentication and an initial identity/membership schema only. Persistent customers, products, sales, expenses, subscriptions, payment processing, AI integration, and admin tools remain for later stages. Architecture and interface details are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/API.md](docs/API.md), [docs/DATABASE.md](docs/DATABASE.md), [docs/SECURITY.md](docs/SECURITY.md), and [STAGE_ROADMAP.md](STAGE_ROADMAP.md).
