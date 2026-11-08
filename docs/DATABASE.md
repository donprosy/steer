# Database Design Plan

PostgreSQL is the planned production database; SQLAlchemy is the persistence layer. SQLite is used for local development and authentication tests. Stage 3 implements the account, business-membership, session, and one-time-token tables listed below; customer and business-operations tables remain planned. Names and fields are provisional and must be refined with validated product workflows.

## Core entities

| Entity | Purpose | Important relationships / constraints |
|---|---|---|
| `users` | Sign-in identity and profile | **Implemented.** Unique normalized email; Argon2id password hash; active and email-verification state. |
| `businesses` | Tenant/workspace and business profile | **Minimal schema implemented** for registration; one owner at creation; multi-business membership is supported by the relationship. |
| `business_memberships` | User-to-business membership and role | **Implemented.** Join table; unique `(business_id, user_id)`; role and membership state. |
| `auth_sessions` | Revocable browser sessions | **Implemented.** Stores only a SHA-256 digest of a random cookie token, expiry, last-seen and revocation timestamps, and remember-me state. |
| `auth_tokens` | Email verification and password-reset OTPs | **Implemented.** Stores only a keyed HMAC digest of a random 6-digit code, purpose, expiry, incorrect-attempt count, and use timestamp. |
| `customers` | Customer/contact records | Belongs to one business; optional relationship to a user is not required. |
| `products` | Product/service catalogue | Belongs to one business; SKU uniqueness should be scoped to business if used. |
| `inventory_items` | Current stock or stock configuration | Belongs to a product/business; quantity and reorder threshold; enforce non-negative rules where appropriate. |
| `inventory_movements` | Auditable stock changes | Belongs to a business and product; records signed quantity, reason, timestamp, and actor; supports reconciliation of current stock. |
| `sales` | Sale header, date, status, totals | Belongs to a business; optionally references a customer; status and totals must be validated on the server. |
| `sale_items` | Product/service lines for each sale | Belongs to a sale and product; stores quantity and price snapshot so historical sales remain stable when catalogue prices change. |
| `expenses` | Business costs | Belongs to a business; includes amount, currency, category, date, and optional note/receipt metadata. |
| `plans` | Product plan definitions and entitlements | Defines internal plan key and limits; provider-specific IDs stored separately/configurably. |
| `subscriptions` | Business subscription lifecycle | Belongs to a business and plan; stores status, billing interval, provider reference, period boundaries, and cancellation/expiry state. |
| `payments` | Payment transactions and reconciliation | Belongs to a subscription/business; provider transaction reference, amount/currency, status, and verified timestamps; unique provider reference. |
| `ai_usage_records` | AI quota and cost accounting | Belongs to a business and initiating user when available; tracks feature, request/result status, units, and provider metadata without secrets or unnecessary prompt content. |
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
- Use primary keys that are not guessable identifiers where practical, plus database foreign keys.
- Every tenant-owned row must have a business scope or an unambiguous path to one.
- Queries and updates must constrain by the authenticated, authorised business; never rely on the client to provide a trusted tenant ID.
- Consider composite uniqueness/foreign-key constraints containing `business_id` to prevent cross-business relationships at the database layer.
- Validate amounts, currencies, quantities, enum/status transitions, and date ranges at the service boundary and reinforce invariants in the database.
- Define deletion, retention, export, and anonymization policies before launch; financial history may require retention even after account closure.
- Use migrations for all schema changes. Production data must not be reset or recreated by application startup.

## Financial and reporting notes

Store monetary values as fixed-precision decimal/numeric amounts, not binary floating point. Persist currency explicitly. Define whether revenue is gross/net, how refunds/voids are handled, and whether profit means gross profit or revenue less recorded expenses before presenting figures. Reports should derive from auditable source records, and any denormalized aggregates need a documented reconciliation strategy.

## Deferred design questions

- Supported currencies, tax treatment, and country-specific records.
- Whether sale checkout, invoices, refunds, or partial payments are in scope.
- Inventory costing and adjustment/negative-stock policy.
- Data retention and deletion obligations for AI prompts and transaction records.
- Whether memberships, invitations, and multiple businesses ship in the first public release.
- How account deletion, verification-email retries, and support-assisted recovery will be presented to users.
