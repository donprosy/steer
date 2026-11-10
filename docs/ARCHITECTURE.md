# Architecture — STEER

## Principles

- Keep frontend and backend independently understandable and deployable.
- Keep business rules on the server; a browser is never an authority for access or plan limits.
- Start with a modular Flask application and a relational data model rather than microservices.
- Scope every business-owned query and mutation to an authorised business context.
- Add external integrations behind services/adapters so provider changes do not spread through domain code.
- Prefer observable, testable behavior and explicit errors over silent fallback behavior.

## High-level flow

```text
Browser (React + Vite)
       | JSON over HTTPS; /api/v1 in development is proxied by Vite
       v
Flask REST API (versioned routes)
       | authentication, validation, permissions, domain services
       v
SQLAlchemy data layer
       |
       v
PostgreSQL (production) / SQLite (local development)

Flask services -- future adapter boundary --> AI provider
Flask services -- future adapter boundary --> Paystack
```

Production hosting should route the frontend and API through HTTPS, ideally under one site origin, or configure a narrowly allowlisted CORS policy if origins must differ.

## Repository boundaries

- `frontend/`: React pages, reusable components, layouts, hooks, API clients, assets, and styles.
- `backend/app/routes/`: HTTP parsing, request validation, response serialization, and route-level authorization, including tenant-scoped customer endpoints.
- `backend/app/services/`: authentication and customer operations, business rules, and external provider adapters.
- `backend/app/models/`: SQLAlchemy identity, business membership, session, token, and initial customer entities; remaining domain entities are added incrementally.
- `backend/migrations/`: Alembic/Flask-Migrate schema history.
- `backend/run.py`: local development entry point; application creation is isolated in `create_app`.
- `docs/`: requirements, API, security, and data design.

## Frontend/backend communication

The frontend calls versioned JSON endpoints under `/api/v1`. The Vite dev server proxies `/api` to Flask, avoiding a separate browser CORS configuration during local development. API calls should be centralized in `frontend/src/services/`, use explicit error handling, and avoid storing long-lived credentials in browser storage.

Production must terminate TLS, apply appropriate cache rules, and return consistent JSON errors. The health endpoint is a minimal process check, not a readiness check for future dependencies.

## API organisation

Use a `/api/v1` prefix and group endpoints by domain. Route modules remain thin: validate input, establish identity and business context, call a service, and serialize a response. Use consistent pagination, filtering, timestamps, currency representation, and error formats. Breaking API changes require a versioning strategy.

## Database architecture

Use SQLAlchemy with PostgreSQL as the production relational database and SQLite for local development and tests that do not depend on PostgreSQL-specific behavior. Stage 3 adds the identity, business, membership, session, and one-time-token schema through Flask-Migrate/Alembic. Stage 4 adds the initial customer table through a forward-only migration. Every tenant-owned entity must carry a business relationship, and service queries must include the authorised business scope. Never rely on automatic production table creation.

The Stage 1 entity design is documented in [DATABASE.md](DATABASE.md). No domain tables are implemented yet.

## Authentication and authorization

Stage 3 implements verified identities, Argon2id password hashing, password-plus-OTP login, revocable server-side sessions, one-time verification/reset tokens, CSRF protection, and server-enforced membership-role checks. Authentication OTPs are sent through the Resend service adapter; only keyed hashes of OTPs are stored. Authentication uses a random opaque `HttpOnly` cookie; only its SHA-256 digest is stored. The React client obtains a CSRF token from the API and sends it in `X-CSRFToken` on mutations. Production cookies are `Secure`, `SameSite=Lax`, and use the `__Host-` prefix. A business context must be resolved from the authenticated user's active membership, not trusted from a client-supplied business ID alone. No bearer token or browser local-storage credential is used.

## Subscription architecture

Represent subscription state and plan entitlements in the backend. A central entitlement check should authorize plan-gated operations; frontend visibility is supplementary. Keep provider billing status distinct from internal access policy, record state changes, and reconcile asynchronous provider events. Grace periods, cancellation, renewal, refunds, and expiry behavior must be specified before billing launch.

## AI integration architecture

Add a backend AI service boundary in a later stage. The backend should assemble only the minimum authorised business context, enforce plan quotas before provider calls, track usage and provider outcomes, and avoid sending unnecessary personal data. AI output must be presented as assistance rather than guaranteed financial, tax, or legal advice. Store only conversation/history data required by an explicit retention policy. Voice is out of initial scope.

## Payment integration architecture

Integrate Paystack only through a backend payment service. Create payment intents/checkout sessions on the server, verify provider signatures and transaction status server-to-server, and make webhook handling idempotent. Never trust a browser success redirect as proof of payment. Keep secrets server-side, record auditable payment events, and avoid storing card details.

## Security and operations

See [SECURITY.md](SECURITY.md) for the security plan. Production also needs structured logs without secrets, monitored errors, encrypted backups, restore drills, dependency updates, and operational procedures for incidents and account support. Do not deploy the Stage 1 development server as a production server.
