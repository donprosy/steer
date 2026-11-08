# Stage 3 Completion Report — Authentication and User Management

## Status

**Stage 3 implementation and local verification passed.** The account lifecycle is functional when SMTP is configured. The workspace itself still contains demonstration business data and is not connected to business-management APIs.

Production launch is **not** ready until real SMTP, a strong persistent secret, HTTPS, shared rate-limit storage, production PostgreSQL, and deployment infrastructure are configured and verified.

## Completed

- Implemented registration with name, email, password confirmation, and required business name. Email addresses are validated and normalized; password hashes use Argon2id. New accounts receive an owner membership in the same transaction as email OTP delivery; failed delivery rolls the entire registration back.
- Replaced verification and reset links with cryptographically random six-digit OTPs. Codes are HMAC-hashed at rest, scoped by user and purpose, expire in 10 minutes, stop accepting guesses after five incorrect attempts, and are single-use. Resends use a 60-second per-account cooldown and invalidate older codes of the same purpose.
- Successful email verification immediately creates the authenticated server-side session and redirects the frontend to the dashboard. Password recovery requires an OTP and matching password confirmation; successful reset revokes prior sessions and returns to login.
- Added opaque, random authentication cookies backed by revocable server-side sessions. Only SHA-256 token digests are stored. Sessions expire after 12 hours or 30 days when “Remember me” is selected.
- Implemented login, current-user lookup, logout, protected `/app/*` routes, and persistent-session restoration after page reload.
- Added CSRF protection for API mutations, same-origin API helpers, endpoint rate limits, secure cookie attributes, JSON error responses, and security headers.
- Added backend membership/role checks that deny users without an active membership in the requested business.
- Added additive Flask-Migrate/Alembic migrations for the authentication schema and OTP attempt tracking. The current local database is at the OTP migration head; no tables or records were dropped.
- Connected the existing authentication screens to the backend without redesigning Stage 2. Added email-verification and password-reset routes. The dashboard still labels its sample figures as demonstration data.
- Updated API, database, architecture, security, roadmap, and setup documentation.

## Architecture

- **Frontend:** React pages use `frontend/src/services/authApi.js` for same-origin JSON requests and `frontend/src/context/AuthContext.jsx` for session state. The API client fetches a CSRF token and sends it in `X-CSRFToken` for mutations.
- **Backend:** Flask app factory, versioned `/api/v1/auth/*` routes, services for account/session operations, SMTP email, and Argon2id password handling.
- **Authentication:** Server-side sessions with opaque `HttpOnly`, `SameSite=Lax` cookies; `Secure` and a `__Host-` cookie name in production. No local-storage bearer credentials.
- **Database:** `users`, `businesses`, `business_memberships`, `auth_sessions`, and `auth_tokens`; SQLite locally, PostgreSQL planned for production. Schema changes use Alembic migrations.
- **Authorization:** Business access is resolved from the authenticated user’s active membership and role; a business ID alone does not grant access.

## Stage 3 files added

### Backend

- `backend/app/extensions.py`
- `backend/app/models/__init__.py`
- `backend/app/models/auth_session.py`
- `backend/app/models/auth_token.py`
- `backend/app/models/business.py`
- `backend/app/models/business_membership.py`
- `backend/app/models/user.py`
- `backend/app/routes/auth.py`
- `backend/app/security.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/email_service.py`
- `backend/app/services/password_service.py`
- `backend/migrations/alembic.ini`
- `backend/migrations/env.py`
- `backend/migrations/README`
- `backend/migrations/script.py.mako`
- `backend/migrations/versions/a6e4fb937d8b_add_authentication_and_business_.py`
- `backend/migrations/versions/c883d3d683ce_add_otp_attempt_tracking.py`
- `backend/requirements-dev.txt`
- `backend/tests/conftest.py`
- `backend/tests/test_auth.py`

### Frontend

- `frontend/src/context/AuthContext.jsx`
- `frontend/src/pages/AccountActionPage.jsx`
- `frontend/src/services/authApi.js`

## Stage 3 files updated

- Backend: `backend/.env.example`, `backend/app/__init__.py`, `backend/app/models/auth_token.py`, `backend/app/models/business_membership.py`, `backend/app/routes/__init__.py`, `backend/app/routes/auth.py`, `backend/app/services/auth_service.py`, `backend/app/services/email_service.py`, `backend/requirements.txt`, `backend/run.py`, `backend/tests/conftest.py`, and `backend/tests/test_auth.py`.
- Frontend: `frontend/src/App.jsx`, `frontend/src/layouts/AppShell.jsx`, `frontend/src/pages/AuthPage.jsx`, and `frontend/src/styles/global.css`.
- Documentation: `README.md`, `STAGE_ROADMAP.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, and `docs/SECURITY.md`.

## Verification

- `python -m pytest -q` from `backend` using the project virtual environment — **17 passed**. Coverage includes OTP generation/delivery, hashed storage, expiry, attempt ceilings, resend cooldown and rotation, purpose separation, registration rollback on email failure, duplicate/invalid registration, login and unverified-account rejection, logout/session expiry, password reset/session revocation, CSRF, rate limits, and business membership/role denial.
- `npm run build` from `frontend` — **passed** with Vite after the final frontend updates.
- `flask --app run db check` from `backend` using the project virtual environment — **passed**, no model/migration differences detected.
- `flask --app run db current` — revision `c883d3d683ce (head)`.
- Health endpoint — `GET /api/v1/health` returned healthy JSON.
- Browser smoke check — login and registration pages rendered; registration displayed the explicit SMTP-not-configured response instead of reporting success. Final OTP browser flow was validated with the controlled test email backend at the API/service test level; real external SMTP was not available.
- Git-ignore checks — `.env`, the local SQLite database, `.venv`, and `node_modules` are ignored. No credentials were created or read.
- Repository scope — changes were made inside the STEER project only; Don Prosy AI was not accessed or modified.

## Run locally

From `backend` in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
```

Edit the ignored `backend/.env`: set a unique `SECRET_KEY`, configure SMTP values (STARTTLS on port 587 is the documented setup), and leave `APP_ENV=development` for local work. Generate a development secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then run:

```powershell
flask --app run db upgrade
python run.py
```

In another terminal, from `frontend`:

```powershell
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). Check the backend with:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/v1/health
```

Registration, verification, and password recovery require a functioning SMTP configuration. Without it, email-dependent operations return an explicit `503`; no fake email or payment integration is included.

## Manual authentication test

1. Configure a unique `SECRET_KEY` and working SMTP settings in the ignored `backend/.env`, then apply migrations and start Flask and Vite using the commands above.
2. Register with a new email, full name, password and confirmation, and business name. Confirm the verification message arrives and enter its six-digit code before it expires.
3. Confirm verification redirects to the dashboard. Refresh the page and verify the session remains active; visiting login or registration while authenticated should return to the dashboard.
4. Log out and confirm the login page appears. Log in with the new credentials, then test an incorrect password and an unverified account to confirm access is denied and the verification-resend option appears only for an unverified account.
5. Use “Forgot password”, request a reset code, and submit it with matching new-password fields. Confirm return to login, log in with the new password, and verify any previously active session is rejected.
6. Try an incorrect OTP repeatedly and request a resend; confirm the attempt limit and 60-second cooldown are enforced. Automated tests cover expiry, code reuse, and rate-limit boundaries without requiring timed manual waits.
7. In browser developer tools, confirm the authentication cookie is `HttpOnly` and `SameSite=Lax`; confirm it is `Secure` in production. Do not copy or share cookie values.

## Errors and unfinished work

- Early backend tests exposed missing SMTP settings in the test fixture and an app-context fixture that persisted request-local authentication cache state. The fixtures were corrected; the final suite passes.
- A listener already using port `5000` returned the health response but `404` for the newly added authentication routes during browser smoke testing. The current backend was verified on port `5010` through a temporary Vite proxy on `5174`. The existing listener was stopped during cleanup; if it was an intentionally running service, restart it. The temporary validation servers were also stopped afterward.
- Real external SMTP delivery was not exercised; no credentials were supplied. Production SMTP must use TLS. Automated tests use an injected in-memory test mail sender only.
- Local migration checks emitted the expected warning because the example `SECRET_KEY` is still unset or a placeholder; configure a unique key in the ignored `backend/.env` before relying on sessions across restarts.
- PostgreSQL, shared Redis rate-limit storage, production HTTPS/cookie behavior, and production WSGI deployment were not exercised. `run.py` refuses to start the Flask development server in production.
- Customer, product, inventory, sales, expense, reports, subscriptions, Paystack payments, AI services, and administration remain future-stage work. The dashboard data is still sample data.
