# Development Roadmap

Each stage should be reviewed and accepted before moving into the next. Scope is intentionally staged so the team validates a secure, useful core before adding costly integrations. Stages 1 and 2 are complete; Stage 3 implements real authentication while leaving business workflows and production service provisioning for their planned stages.

## 1. Planning and project foundation — complete

- Confirm product vision, target users, MVP boundaries, roles, revenue direction, and initial design direction.
- Establish separate frontend and backend structure, developer configuration, local health check, and baseline documentation.
- Plan API groups, data entities, security, integrations, and delivery stages without implementing business workflows.
- Exit: foundation runs locally, documentation is reviewed, and unresolved market/compliance decisions are recorded.

## 2. Website design and frontend

- Validate user journeys and responsive information architecture with small business owners.
- Define brand tokens, typography, accessible components, navigation, marketing pages, and authenticated application shell.
- Implement polished dashboard and management screens against agreed API contracts, with loading, empty, error, and mobile states.
- Exit: design review, accessibility checks, responsive testing, and frontend acceptance.

## 3. User authentication and security

- Implement registration, sign-in/out, email verification, password recovery, sessions, and business membership/roles — complete for the initial account lifecycle.
- Add server-side authorization, business context resolution, input validation, and cross-business membership denial tests — complete as a reusable authorization foundation; domain-resource isolation tests are added with Stage 4 resources.
- Establish production configuration checks, migration workflow, security headers, CSRF policy, and auth abuse limits — implemented; production SMTP, strong secret, TLS, and shared rate-limit storage still require environment provisioning.
- Exit: automated tests verify account lifecycle, CSRF/session controls, and membership denial. Before launch, complete a security review and configure production services.

## 4. Business management system

- Implement business profiles, customers, products, stock movements, sales, expenses, and core dashboard/report calculations.
- Add transactional integrity, database migrations, search/pagination, import/export policy, and currency/financial definitions.
- Validate practical workflows with pilot businesses and reconcile reports against source records.
- Exit: core operations are reliable, usable, and financially consistent for the supported business types.

## 5. AI business assistant

- Select a provider only after cost, privacy, retention, and quality evaluation.
- Add text conversations and business analysis through a backend service boundary with permission-scoped context.
- Track usage, enforce quotas, disclose limitations, and test prompt/data privacy behavior.
- Voice AI remains explicitly out of initial scope and requires a separate product/security decision.
- Exit: quality, privacy, safety, usage accounting, and unit economics meet agreed thresholds.

## 6. Subscription and payment system

- Finalize Starter, Growth, and Business pricing/entitlements, billing periods, trial/cancellation/refund rules, and supported market.
- Integrate Paystack in backend services; verify callbacks/webhooks, reconcile payments, and enforce plan limits server-side.
- Test duplicate/late events, failed payments, renewal, expiry, cancellation, and recovery cases.
- Exit: end-to-end subscription lifecycle is verified without trusting client-side payment claims.

## 7. Admin dashboard

- Build a protected, audited operations interface with least-privilege roles.
- Add user/business support workflows, subscription/payment review, AI usage/cost monitoring, and aggregated platform metrics.
- Define administrator access reviews and support procedures.
- Exit: privileged access is tested, logged, and limited to operational needs.

## 8. Testing and security

- Expand automated unit, API integration, end-to-end, migration, tenant-isolation, and payment tests.
- Perform dependency, configuration, privacy, and application security reviews; resolve launch-blocking findings.
- Validate backup/restore, performance, accessibility, failure handling, and incident response.
- Exit: release criteria and operational runbooks are signed off.

## 9. Deployment and official launch

- Provision production infrastructure, managed PostgreSQL, TLS, secrets, logs, monitoring, backups, and deployment pipeline.
- Run controlled pilot, migrate verified data if any, publish support/privacy/terms materials, and confirm payment readiness.
- Launch gradually with rollback and incident procedures.
- Exit: production health, support, billing, and data protection controls are operating.

## 10. Growth and improvements

- Review customer feedback, adoption, retention, support, costs, and reliability measures.
- Prioritize product improvements based on validated needs and sustainable economics.
- Consider team collaboration, accounting integrations, additional markets/payment methods, advanced reports, and future voice capabilities only with separate validation.
- Continue security, compliance, accessibility, performance, and data governance improvements.

## Stage 3 implementation boundary

Account authentication is functional, but the workspace remains explicitly marked as demonstration data. Customer, inventory, sales, expense, reporting, subscription, payment, AI, and administration APIs are not implemented by Stage 3.
