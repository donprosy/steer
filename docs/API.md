# REST API Plan

Implemented and planned endpoints use the `/api/v1` prefix and JSON request/response bodies unless a future file-upload flow is explicitly documented. Stage 3 implements health and authentication/account endpoints. Stage 4 implements business profiles, customers, products/inventory, sales/payments/refunds, expenses, dashboard summaries, reports, and CSV exports. Authentication, validation, business-scope authorization, pagination, and consistent error responses are required for every endpoint.

## Conventions

- Resource collections use plural nouns; IDs identify one resource.
- Use `GET` to read, `POST` to create/actions, `PATCH` for partial updates, and `DELETE` only where lifecycle policy permits.
- Use ISO 8601 timestamps and explicit currency codes. Monetary decimal values should be serialized as decimal strings to avoid floating-point ambiguity.
- Collection routes should define pagination and filtering; responses should not return unbounded datasets.
- Mutations must be idempotent where retries are expected, especially payment/webhook operations.
- Authentication and business authorization are backend responsibilities.

## Health

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/health` | Minimal process health check; implemented. Does not expose environment settings or verify database readiness. |

The existing `service` response identifier (`don-prosy-business-manager`) is retained for API compatibility; it is a technical identifier, not the public product name.

## Implemented endpoint groups

## Business profiles (Stage 4)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/businesses/{business_id}` | Read profile data for an active business member. |
| `PATCH` | `/api/v1/businesses/{business_id}` | Update name and contact details; owner-only. Currency is fixed to NGN. |

## Customer management (Stage 4)

All customer endpoints require a valid authenticated session and CSRF token for mutations. The business ID is only a resource lookup key: the server verifies an active membership before serving any customer resource. Inaccessible businesses and customers return the same `404` response to avoid confirming their existence.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/businesses/{business_id}/customers?page=1&per_page=25&q=` | Search and list customers for the authorized business. |
| `POST` | `/api/v1/businesses/{business_id}/customers` | Create a customer. Requires `full_name` and `phone`; `email`, `address`, and `notes` are optional. |
| `GET` | `/api/v1/businesses/{business_id}/customers/{customer_id}` | Retrieve a customer profile. |
| `PATCH` | `/api/v1/businesses/{business_id}/customers/{customer_id}` | Update explicitly supported customer fields. |
| `DELETE` | `/api/v1/businesses/{business_id}/customers/{customer_id}` | Delete a customer; restricted to owners and managers. |

List responses contain `customers` and `pagination` (`page`, `per_page`, `total`, `pages`). List rows include financial summaries but omit purchase history to keep collection responses bounded; the customer detail endpoint includes purchase history. Customer mutations return a serialized `customer` object. Validation errors use the API's standard `{ "error": { "code": "...", "message": "..." } }` response shape. Purchase history and balances are derived from sales and payment records.

## Authentication

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/auth/csrf` | Return a CSRF token for same-origin requests. Send it as `X-CSRFToken` on every `POST`, `PUT`, `PATCH`, and `DELETE`. |
| `POST /api/v1/auth/register` | Validate name, email, password, confirmation, and business name; atomically create an unverified account, owner membership, and verification OTP only if Resend delivery succeeds. Returns `202`; duplicate email returns `409`. Configure `RESEND_API_KEY` and a verified sender address. |
| `POST /api/v1/auth/login` | Verify credentials and email status, send a login OTP, and return a pending `challenge_id`; accepts optional `remember_me`. Does not create a session. |
| `POST /api/v1/auth/otp/send` | Alias for the password-check step at `/login`; accepts email, password, and optional `remember_me`, and sends a login OTP. |
| `POST /api/v1/auth/otp/resend` | Resend a login OTP using its `challenge_id`; enforces the per-account 60-second cooldown and generic responses for invalid challenges. |
| `POST /api/v1/auth/otp/verify` | Verify a login `challenge_id` and 6-digit code; issues the server-side session and opaque `HttpOnly` cookie only on success. |
| `POST /api/v1/auth/logout` | Revoke the current server-side session and clear its cookie. |
| `GET /api/v1/auth/me` | Return the current identity and active business memberships; requires authentication. |
| `POST /api/v1/auth/verification-requests` | Send a 6-digit verification OTP through Resend without disclosing whether an account is eligible. Enforces per-IP rate limits and a per-account 60-second cooldown. |
| `POST /api/v1/auth/email-verifications` | Verify a matching email and 6-digit verification OTP; expires after 10 minutes, allows up to five incorrect attempts, and creates the signed-in session on success. |
| `POST /api/v1/auth/password-reset-requests` | Start privacy-preserving recovery by emailing a 6-digit reset OTP through Resend; enforces a 60-second cooldown. |
| `POST /api/v1/auth/password-resets` | Validate email and reset OTP, require matching new-password confirmation, and revoke all existing sessions. |

Email verification and password reset OTP endpoints accept `{"email":"person@example.com","code":"012345"}`. Login OTP endpoints accept `{"email":"person@example.com","password":"...","remember_me":false}` to send a code, `{"challenge_id":"..."}` to resend, and `{"challenge_id":"...","code":"012345"}` to verify. Registration also accepts `confirm_password`; password reset accepts `password` and `confirm_password`. OTP values are generated with a cryptographic random generator, stored as a keyed HMAC digest, scoped to user and purpose, and never returned in API responses. They expire after 10 minutes, are single-use, and stop accepting guesses after five incorrect attempts. New codes invalidate previous codes of the same purpose. Resend endpoints return a generic response during cooldown and for ineligible accounts to reduce account enumeration.

Auth cookies are same-origin, `HttpOnly`, and `SameSite=Lax`; production also sets `Secure` and uses the `__Host-dpbm_auth` cookie name. Authentication credentials are never stored in browser local storage.

Mutating endpoints are CSRF-protected. The frontend fetches `/api/v1/auth/csrf` and sends the returned token in the `X-CSRFToken` header. The API client refreshes that token once after an expired-token response. Rate limits are applied to registration, login, verification, and recovery endpoints; production requires shared rate-limit storage.

### Implemented authentication error shape

```json
{"error":{"code":"validation_error","message":"Enter a valid email address."}}
```

Unverified accounts cannot sign in. Successful login OTP verification creates an authenticated session. Email-dependent OTP operations return `503` when Resend is not configured or delivery fails. Set `RESEND_API_KEY` and `MAIL_FROM` to a sender address verified with Resend. Non-OTP account notifications continue to use optional SMTP settings.

## Product and inventory management (Stage 4)

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/products` | List/search products and services with pagination, low-stock filtering and sorting (`newest`, `name`, `price_low`, `price_high`, `stock_low`). |
| `POST /api/v1/businesses/{business_id}/products` | Create a catalogue item. |
| `GET /api/v1/businesses/{business_id}/products/{product_id}` | Read one scoped item. |
| `PATCH /api/v1/businesses/{business_id}/products/{product_id}` | Update catalogue details without rewriting historical sale snapshots. |
| `POST /api/v1/businesses/{business_id}/products/{product_id}/archive` | Archive an item without deleting sales history. |

Inventory adjustments use `POST /api/v1/businesses/{business_id}/products/{product_id}/stock-adjustment`; product detail includes recent movements. Sale, opening-stock, and adjustment operations write stock movements.

## Sales and payments (Stage 4)

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/sales?q=&page=1&per_page=25&range=this_month&status=all` | Search by reference/notes, filter by status and supported period, and paginate sales. Status values are `all`, `pending`, `partially_paid`, `paid`, `cancelled`, and `refunded`. Date ranges may be `today`, `this_week`, `this_month`, `this_year`, or `custom` with `start_date` and `end_date`. |
| `POST /api/v1/businesses/{business_id}/sales` | Record validated multi-line sales; decrement inventory transactionally. |
| `GET /api/v1/businesses/{business_id}/sales/{sale_id}` | Read sale details within business scope. |
| `PATCH /api/v1/businesses/{business_id}/sales/{sale_id}` | Owner/manager-only metadata edit for customer, notes and sale date. Cancelled/refunded sales are locked. Line-item and total edits remain unsupported. |
| `POST /api/v1/businesses/{business_id}/sales/{sale_id}/payments` | Record a bounded incoming payment. |
| `POST /api/v1/businesses/{business_id}/sales/{sale_id}/refunds` | Record a bounded refund; a full refund restores physical product stock. |
| `POST /api/v1/businesses/{business_id}/sales/{sale_id}/cancel` | Cancel sales with no net collected funds. |

## Expenses (Stage 4)

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/expenses?q=&page=1&per_page=25&range=this_month` | Search by description/category and filter/paginate expenses. Date ranges may be `today`, `this_week`, `this_month`, `this_year`, or `custom` with `start_date` and `end_date`. |
| `POST /api/v1/businesses/{business_id}/expenses` | Record a validated expense. |
| `PATCH /api/v1/businesses/{business_id}/expenses/{expense_id}` | Correct permitted fields with audit requirements. |
| `DELETE /api/v1/businesses/{business_id}/expenses/{expense_id}` | Delete an expense; restricted to owners and managers. |

## Dashboard and reports (Stage 4)

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/dashboard?range=this_month` | Live financial summary, business/customer and inventory counts, recent sales, top products, stock alerts, and net-sales/expense trend. |
| `GET /api/v1/businesses/{business_id}/reports?type=sales&range=this_month` | Records for sales, expenses, inventory, customers, payments, receivables, product performance, or profit/loss. |
| `GET /api/v1/businesses/{business_id}/reports/export?type=sales&range=this_month` | CSV export for supported report categories. Text cells are escaped and formula-prefixed content neutralized. |

Dashboard and report ranges accept `today`, `this_week`, `this_month`, `this_year`, or `custom`. Custom ranges require ISO `start_date` and `end_date`; date-only end dates include the full day. Currency is currently NGN.

## Planned endpoint groups

### AI assistant

| Method and path | Responsibility |
|---|---|
| `POST /api/v1/businesses/{business_id}/assistant/conversations` | Start a text conversation under plan and usage limits. |
| `POST /api/v1/businesses/{business_id}/assistant/conversations/{conversation_id}/messages` | Submit a prompt and return an AI response using authorised context. |
| `GET /api/v1/businesses/{business_id}/assistant/usage` | Read current-period usage and applicable limit. |

Voice AI is not part of the initial release.

### Subscriptions

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/plans` | List public plan descriptions and non-sensitive entitlements. |
| `GET /api/v1/businesses/{business_id}/subscription` | Read current subscription state and renewal information. |
| `POST /api/v1/businesses/{business_id}/subscription/checkout` | Start a provider-backed checkout after server-side eligibility checks. |
| `POST /api/v1/businesses/{business_id}/subscription/cancel` | Request cancellation under disclosed policy. |

### Payments

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/payments` | List authorised payment records. |
| `GET /api/v1/businesses/{business_id}/payments/{payment_id}` | Read a payment's verified internal status. |
| `POST /api/v1/webhooks/paystack` | Receive, verify, deduplicate, and process provider events; not a browser-facing confirmation endpoint. |

### Administration

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/admin/users` | Restricted, audited user search for authorised platform administrators. |
| `GET /api/v1/admin/businesses` | Restricted business account monitoring. |
| `GET /api/v1/admin/subscriptions` | Subscription operations and exception review. |
| `GET /api/v1/admin/payments` | Payment reconciliation and monitoring. |
| `GET /api/v1/admin/ai-usage` | Platform-level AI usage/cost monitoring without unnecessary message content. |
| `GET /api/v1/admin/metrics` | Aggregated platform health and product statistics. |

## Error contract

Authentication endpoints use `{"error":{"code":"validation_error","message":"Request could not be processed"}}`. Other resource groups should follow this shape and define their status mappings before implementation. Production responses must not include stack traces, secrets, SQL, or sensitive tenant data.
