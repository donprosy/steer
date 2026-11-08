# REST API Plan

Implemented and planned endpoints use the `/api/v1` prefix and JSON request/response bodies unless a future file-upload flow is explicitly documented. Stage 3 implements health and authentication/account endpoints; business-management endpoints remain planned. Authentication, validation, business-scope authorization, pagination, and consistent error responses are required before other endpoint groups are exposed.

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

## Planned endpoint groups

### Authentication

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

### Businesses

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses` | List businesses the current user may access. |
| `POST /api/v1/businesses` | Create a business and initial owner membership. |
| `GET /api/v1/businesses/{business_id}` | Read an authorised business profile. |
| `PATCH /api/v1/businesses/{business_id}` | Update permitted business settings. |

### Customers

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/customers` | Paginated, scoped customer search/list. |
| `POST /api/v1/businesses/{business_id}/customers` | Create a customer. |
| `GET /api/v1/businesses/{business_id}/customers/{customer_id}` | Read one customer and authorised summary. |
| `PATCH /api/v1/businesses/{business_id}/customers/{customer_id}` | Update customer details. |
| `DELETE /api/v1/businesses/{business_id}/customers/{customer_id}` | Archive or delete according to retention rules. |

### Products

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/products` | List/search products and services. |
| `POST /api/v1/businesses/{business_id}/products` | Create a catalogue item. |
| `GET /api/v1/businesses/{business_id}/products/{product_id}` | Read one scoped item. |
| `PATCH /api/v1/businesses/{business_id}/products/{product_id}` | Update catalogue details without rewriting historical sale snapshots. |
| `DELETE /api/v1/businesses/{business_id}/products/{product_id}` | Archive an item subject to sales/history constraints. |

### Inventory

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/inventory` | Read current stock and low-stock indicators. |
| `POST /api/v1/businesses/{business_id}/inventory/movements` | Record an authorised stock receipt, sale, or adjustment with an audit trail. |
| `GET /api/v1/businesses/{business_id}/inventory/movements` | Paginated movement history and filters. |

### Sales

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/sales` | List sales by date/status/customer. |
| `POST /api/v1/businesses/{business_id}/sales` | Record a sale and validated line items; apply inventory policy transactionally. |
| `GET /api/v1/businesses/{business_id}/sales/{sale_id}` | Read sale details within business scope. |
| `POST /api/v1/businesses/{business_id}/sales/{sale_id}/void` | Void a sale under an explicit auditable policy. |

### Expenses

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/expenses` | Paginated, filtered expense list. |
| `POST /api/v1/businesses/{business_id}/expenses` | Record a validated expense. |
| `GET /api/v1/businesses/{business_id}/expenses/{expense_id}` | Read one scoped expense. |
| `PATCH /api/v1/businesses/{business_id}/expenses/{expense_id}` | Correct permitted fields with audit requirements. |

### Reports

| Method and path | Responsibility |
|---|---|
| `GET /api/v1/businesses/{business_id}/reports/overview` | Period summary for sales, expenses, estimated profit, and inventory. |
| `GET /api/v1/businesses/{business_id}/reports/sales` | Sales trends and breakdowns. |
| `GET /api/v1/businesses/{business_id}/reports/expenses` | Expense totals and categories. |
| `GET /api/v1/businesses/{business_id}/reports/inventory` | Stock valuation/alerts only after calculation rules are defined. |

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
