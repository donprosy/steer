# Database Design Plan

PostgreSQL is the planned production database; SQLAlchemy is the persistence layer. SQLite is used for local development and authentication tests. Stage 3 implements the account, business-membership, session, and one-time-token tables listed below. Stage 4 adds domain tables incrementally through forward-only migrations; names and fields should be refined with validated product workflows.

## Core entities

| Entity | Purpose | Important relationships / constraints |
|---|---|---|
| `users` | Sign-in identity and profile | **Implemented.** Unique normalized email; Argon2id password hash; active and email-verification state. |
| `businesses` | Tenant/workspace and business profile | **Implemented.** Name, industry, contact email, phone, address, and fixed `NGN` currency; multi-business membership is supported by the relationship. |
| `business_memberships` | User-to-business membership and role | **Implemented.** Join table; unique `(business_id, user_id)`; role and membership state. |
| `auth_sessions` | Revocable browser sessions | **Implemented.** Stores only a SHA-256 digest of a random cookie token, expiry, last-seen and revocation timestamps, and remember-me state. |
| `auth_tokens` | Login, email-verification, and password-reset OTPs | **Implemented.** Stores only a keyed HMAC digest of a random 6-digit code, purpose, expiry, incorrect-attempt count, use timestamp, and the login challenge's remember-me choice. |
| `customers` | Customer/contact records | **Implemented.** Business-scoped profiles, searchable/paginated lists, and sale/payment-derived purchase and receivable summaries. |
| `products` | Product/service catalogue | **Implemented.** Business-scoped catalogue and archive state; SKU uniqueness is not yet enforced. |
| `inventory_movements` | Auditable stock changes | **Implemented.** Signed quantity, resulting balance, reason, timestamp, and optional actor; product opening stock and sales/adjustments are recorded. |
| `sales` | Sale header, date, status, totals | **Implemented.** Business-scoped, optionally customer-linked, with server-validated sale and payment/refund/cancellation workflows. |
| `sale_items` | Product/service lines for each sale | **Implemented.** Quantity, description, unit-price, and unit-cost snapshots preserve historical sale details. |
| `expenses` | Business costs | **Implemented.** Business-scoped category, amount, payment method, date, and optional notes. |
| `plans` | Product plan definitions and entitlements | Defines internal plan key and limits; provider-specific IDs stored separately/configurably. |
| `subscriptions` | Business subscription lifecycle | Belongs to a business and plan; stores status, billing interval, provider reference, period boundaries, and cancellation/expiry state. |
| `payments` | Payment transactions and reconciliation | Belongs to a subscription/business; provider transaction reference, amount/currency, status, and verified timestamps; unique provider reference. |
| `ai_usage_records` | AI quota and cost accounting | Belongs to a business and initiating user when available; tracks feature, request/result status, units, and provider metadata without secrets or unnecessary prompt content. |
| `ai_conversations` | Tenant-owned AI chat sessions | User and business ownership, title and timestamps; removed with the owning business or user. |
| `ai_messages` | Conversation message history | User/assistant role, content, request idempotency key and provider metadata; cascades with its conversation. |
| `audit_events` | Sensitive administrative and ownership changes | Actor, business scope where applicable, action, target identifier, timestamp, and carefully redacted metadata. |

## Relationship outline

```text
users *---* businesses via business_memberships (registration creates the initial owner membership)
users 1---* auth_sessions
users 1---* auth_tokens
businesses 1---* customers
businesses 1---* products 1---0..1 inventory_items
products 1---* inventory_movements
businesses 1---* sales 1---* sale_items *---1 products
businesses 1---* expenses
businesses 1---* subscriptions *---1 plans
subscriptions 1---* payments
businesses 1---* ai_usage_records
users 1---* ai_usage_records (optional actor)
```

## Data integrity and tenancy

- Stage 3's initial schema is defined in `backend/app/models/` and created with the versioned migration in `backend/migrations/versions/`. Apply it with `flask --app run db upgrade`; do not use `create_all()` against deployed data.
- Stage 4 migration revisions must follow the current Alembic head and must be reviewed/applied through the existing development and deployment process. This work does not run schema upgrades against production; the instructor handoff and review gate are in `STAGE_4_REPORT.md`.
- Use primary keys that are not guessable identifiers where practical, plus database foreign keys.
- Every tenant-owned row must have a business scope or an unambiguous path to one.
- Queries and updates must constrain by the authenticated, authorised business; never rely on the client to provide a trusted tenant ID.
- Consider composite uniqueness/foreign-key constraints containing `business_id` to prevent cross-business relationships at the database layer.
- Validate amounts, currencies, quantities, enum/status transitions, and date ranges at the service boundary and reinforce invariants in the database.
- Define deletion, retention, export, and anonymization policies before launch; financial history may require retention even after account closure.
- Use migrations for all schema changes. Production data must not be reset or recreated by application startup.

## Financial and reporting notes

Store monetary values as fixed-precision decimal/numeric amounts, not binary floating point. Current business profiles use NGN only; multi-currency and tax handling are deferred until launch markets are confirmed. Dashboard definitions: gross sales exclude cancelled sales; net sales subtract received refunds; net cash collected subtracts refunds from received payments; receivables equal gross sale value less received incoming payments (refunds are reported separately and do not turn a paid sale into a customer debt); gross profit is net sales less cost of goods sold; net profit is gross profit less recorded operating expenses. A full refund returns all physical line-item stock and removes that sale's COGS; partial cash refunds do not infer returned quantities, so physical returns must be recorded as an inventory adjustment. Reports derive from source records.

## Deferred design questions

- Supported currencies, tax treatment, and country-specific records.
- Whether sale checkout, invoices, refunds, or partial payments are in scope.
- Inventory costing and adjustment/negative-stock policy.
- Data retention and deletion obligations for AI prompts and transaction records.
- Whether memberships, invitations, and multiple businesses ship in the first public release.
- How account deletion, verification-email retries, and support-assisted recovery will be presented to users.
