# STEER — AI-Powered Business Management Platform

**Take Control. Move Your Business Forward.**

STEER is an AI-powered business management platform designed to help business owners manage operations, monitor performance, and make smarter decisions. Stages 1–3 established the product foundation, responsive frontend, and verified account authentication. Stage 4 implements tenant-scoped business profiles, customers, products, stock movements, sales/payments/refunds, expenses, dashboard calculations, reports, and CSV exports. The Stage 4 report records what is implemented and what remains before formal pilot acceptance. The AI assistant is not connected; Stage 5 is the next planned stage.

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
    models/                 # Identity, membership, and business-management entities
    routes/                 # Health, auth, business profile, and operational APIs
    services/               # Auth, domain rules, financial calculations, and email
  migrations/               # Versioned Alembic database migrations
  instance/                 # Local SQLite database files (not committed)
  run.py                    # Flask development entry point
frontend/
  src/
    assets/                 # Locally managed visual assets
    components/              # Shared UI elements, icons, and charts
    hooks/
    layouts/                # Application shell
    pages/                   # Marketing, authentication, and live business workspaces
    services/               # Same-origin JSON API clients for auth and business data
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

Before running, edit the ignored `backend/.env` and replace the local placeholder `SECRET_KEY` with a random value. To deliver authentication OTPs through Gmail, set `AUTH_EMAIL_MODE=smtp`, `MAIL_SERVER=smtp.gmail.com`, `MAIL_PORT=587`, `MAIL_USE_TLS=1`, and set `MAIL_USERNAME`, `MAIL_PASSWORD`, and `MAIL_DEFAULT_SENDER` to your Gmail address, Google app password, and sender address. Gmail requires 2-Step Verification and an app password; do not use your normal Gmail password. Alternatively, use `AUTH_EMAIL_MODE=resend`, `RESEND_API_KEY`, and `MAIL_FROM` with a verified Resend sender. `AUTH_EMAIL_MODE=console` is for local development only and prints codes to the backend terminal. Do not commit credentials.

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

The public landing page is at `/`. Real account screens are available at `/login`, `/register`, and `/forgot-password`. Registration sends a six-digit verification OTP, then signs in and opens the dashboard after successful verification. Login checks the password, sends a separate six-digit OTP, and creates a session only after that code is verified. Password recovery uses its own OTP. `/app/*` routes require a verified account and sign-in. Business profile, customer, product, inventory, sales, expenses, dashboard, and report screens use authenticated business-scoped APIs. Business reports and CSV downloads are available from the Reports screen. Currency is currently NGN and is not user-configurable. The AI assistant is clearly marked as a Stage 5 preview and does not send business data to an AI provider. See [STAGE_4_REPORT.md](STAGE_4_REPORT.md) for implementation status, financial definitions, verification evidence, and remaining acceptance checks.
The Stage 5 assistant uses deterministic backend business context and stores authorized conversations. Configure `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`, `AI_API_FORMAT`, `AI_CHAT_PATH`, `AI_AUTH_SCHEME`, `AI_TIMEOUT_SECONDS`, and `AI_MAX_CONTEXT_MESSAGES` in the ignored backend `.env`. Real instructor-provider behavior remains unverified until provider documentation and credentials are supplied.

Authentication OTPs expire after ten minutes, are limited to five incorrect attempts, and can be resent after a 60-second cooldown. SMTP and Resend modes deliver OTPs by email; local console mode prints codes to the backend terminal. Failed registration email delivery rolls back the pending account and membership.

Pricing is intentionally shown as “Coming soon.” Payment processing and AI responses are not connected. See [STAGE_2_REPORT.md](STAGE_2_REPORT.md) for completed interface details and verification results.

## Configuration

Copy `backend/.env.example` to `backend/.env` for local settings. Never commit `.env` or production credentials. Production startup also requires a strong secret key, HTTPS `PUBLIC_APP_URL`, Resend API key and verified sender, and shared rate-limit storage (for example a managed Redis-compatible endpoint). The Flask development server is for local use only.

## Stage boundaries

Stage 3 implements account authentication and the identity/membership schema. Stage 4 implements the operational business-management core; its pilot, production database, and end-to-end switching acceptance gates still require completion. Consult [STAGE_4_REPORT.md](STAGE_4_REPORT.md) for exact status and the Stage 5 handoff. Architecture and interface details are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/API.md](docs/API.md), [docs/DATABASE.md](docs/DATABASE.md), [docs/SECURITY.md](docs/SECURITY.md), and [STAGE_ROADMAP.md](STAGE_ROADMAP.md).
