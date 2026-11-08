# Security Plan

Security is a design constraint for every stage. Stage 3 implements the identity/session controls described below; production operations, business-resource authorization, and later payment/AI controls remain subject to the listed follow-up requirements.

## Identity and passwords

- **Implemented:** Hash passwords with Argon2id using a unique salt per password. Rehash on successful authentication when Argon2 parameters change.
- Never store or log plaintext passwords, reset tokens, or authentication credentials.
- **Implemented:** Generic login, verification-request, and password-recovery responses reduce account enumeration. Email verification is required before login.
- **Implemented:** Rate-limit login, registration, verification, and recovery requests. Local development uses process-local limits; production configuration rejects in-memory rate-limit storage.
- **Implemented:** Verification and recovery codes are cryptographically random six-digit OTPs. A keyed HMAC digest is stored with user/purpose scope, 10-minute expiry, five-attempt ceiling, and single-use state. A 60-second per-account resend cooldown and IP rate limits restrict abuse; issuing another code invalidates previous unused codes of that purpose.

## Secure authentication

**Implemented:** Opaque random session cookies backed by server-side session records containing only a SHA-256 token digest. Cookies are `HttpOnly`, `SameSite=Lax`, path `/`; production uses `Secure` and the `__Host-` prefix. Login creates a new session, standard sessions expire after 12 hours, remember-me sessions after 30 days, and logout/password reset revoke sessions. CSRF tokens protect mutations. The browser does not store bearer credentials or put authentication tokens in URLs.

Enforce TLS in production. Never use Flask's development server in production. Set a strong secret key from an environment/secret manager and fail safely if production configuration is missing.

## Authorization and business data isolation

- **Implemented foundation:** `require_auth` and `require_business_role` enforce active identity, membership, business status, and allowed role on protected routes. The initial registration creates an owner membership. Future business-resource routes must use these checks and scope every query by the authorized business.
- Resolve active business membership from authenticated server-side identity; a business ID in a URL/body is only a lookup key, never proof of permission.
- Scope every tenant-owned read, update, delete, export, report, AI context query, and background task to the authorised business.
- Use deny-by-default permissions and check both membership status and required role.
- Add tests that attempt cross-business ID substitution for every resource family.
- Apply database foreign keys and, where useful, composite constraints to prevent relationships across businesses.
- Audit privileged changes and administrator access; minimize support access and require an explicit operational reason.

## Input validation and web protections

- Validate type, length, format, ranges, and allowed state transitions at API boundaries.
- Use SQLAlchemy parameterized operations; never construct SQL from user strings.
- Escape output and avoid unsafe HTML rendering; use framework defaults and a restrictive Content Security Policy when deployed.
- **Implemented:** Flask-WTF CSRF defenses protect cookie-authenticated mutations; JSON failures use a stable error response.
- Configure strict CORS allowlists only when cross-origin clients are needed.
- Prevent mass assignment by mapping allowed fields explicitly.
- Apply safe upload limits and content validation if uploads are introduced.
- Use security headers, HTTPS, secure cookie flags, and appropriate cache controls for private responses.
- **Implemented for auth:** Apply endpoint rate limits; production requires a shared store configured with `RATELIMIT_STORAGE_URI`. Add abuse monitoring and appropriate limits for reports, AI, and payment/webhook paths when those features are implemented.
- Protect against SSRF, open redirects, path traversal, and unsafe deserialization if later features introduce those input surfaces.

## Secrets and configuration

- **Implemented:** Load sensitive values from environment variables or a managed secret store, never from committed source or frontend build variables. Production startup rejects missing/weak secret keys, in-memory rate limits, incomplete SMTP configuration, SMTP without TLS, and a non-HTTPS public URL. `run.py` refuses to start the Flask development server in production.
- `.env` is ignored by Git; `.env.example` contains placeholders only.
- Rotate credentials when exposed and document production rotation procedures.
- Separate development, test, and production credentials and databases.
- Never return configuration, stack traces, tokens, or secrets in health responses or error messages.

## Payments

- Keep Paystack secret keys on the backend only; do not collect or store raw card details.
- Verify webhook signatures using the provider's documented method and compare verified transaction status/amount/currency against the expected server-side record.
- Treat provider notifications as untrusted until verified; make handlers idempotent and protect against replay/duplicate delivery.
- Do not activate a subscription because a browser redirects to a success page.
- Record sufficient audit and reconciliation data without retaining unnecessary payment-sensitive information.

## AI privacy and usage

- Apply business authorization before retrieving context or sending a request to an AI provider.
- Minimize personal and transactional data sent externally; document provider retention and processing terms before launch.
- Enforce plan quotas and abuse limits server-side before provider calls.
- Avoid logging full prompts/responses or credentials by default; define explicit retention, deletion, and access policies.
- Clearly communicate uncertainty and do not represent outputs as professional financial, legal, or tax advice.

## Operations and verification

- Pin/lock deployed dependencies and scan/update them on a regular schedule.
- Use least-privilege database and service credentials, encrypted transport, encrypted backups, and tested restoration.
- Centralize logs/alerts with secret and personal-data redaction.
- Maintain incident response, access review, and data breach procedures.
- **Implemented tests:** Authentication validation, CSRF, verification and reset token use/expiry, session cookie and revocation behavior, and business-membership isolation.
- Add production authorization, rate-limit, and payment-verification tests before each relevant launch stage. Use shared production session/database infrastructure and review deployment headers/TLS before launch.
