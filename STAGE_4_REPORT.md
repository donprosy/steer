# Stage 4 — Business Management System

## Status

The Stage 4 operational workflows are implemented and covered by backend tests and a production frontend build. This is an implementation and verification report, not a production launch sign-off. Pilot reconciliation, target-PostgreSQL validation, and browser-driven acceptance across multiple business workspaces remain launch gates.

## Delivered workflows

- Business profile details scoped to the selected authorized workspace.
- Customer contact records, search/pagination, financial summaries, and customer purchase history.
- Product and service catalogue, search/pagination, product archiving, and role-controlled edits.
- Inventory opening stock, searchable stock ledger, threshold/out-of-stock visibility, and reasoned adjustments. Sales and full refunds record their corresponding stock movements.
- Sales with customer/product lookup, multi-line items, estimated subtotal, initial payments, receipts, payment history, later payments, refunds, and cancellation rules.
- Expense entry, editing/deletion by authorized roles, search, pagination, and today/week/month/year/custom date filters.
- Business-scoped dashboard financials, customers/inventory counts, best-selling and low-stock products, and actual net-sales/expense trends.
- Sales, expense, inventory, customer, payment, receivables, product-performance, and profit-and-loss reports, with date filtering and CSV export.
- UI states and management views that clear tenant-specific selections when switching business workspaces. Demo-only notification and hardcoded charts were removed from the authenticated app.
- Dashboard now includes recent expenses and a combined recent sales/expense activity feed.
- Sales support status filtering and guarded metadata editing; product catalogue supports sorting and a detailed stock valuation/movement view.
- Reports support browser print/PDF output in addition to CSV; settings expose supported business, account and security controls.

## Financial definitions and boundaries

Calculations use decimal arithmetic. Cancelled sales are excluded from sales; refunds reduce net sales and net cash. Receivables are sale value less received incoming payments; refunds are reported separately and do not create customer debt. Gross profit is net sales less cost of goods sold, and net profit subtracts recorded operating expenses. COGS uses sale-time cost snapshots. Full refunds restore product stock; partial cash refunds do not infer physical returns, which must be recorded as an inventory adjustment.

The catalogue and receipts use NGN; multi-currency reporting, configurable tax, discounts, subscriptions/Paystack, and AI-provider functionality are not Stage 4 deliverables. The subtotal is an estimate based on entered line items; the backend remains authoritative for sale totals.

## Database

Migration `c51d47a9291f` adds business industry, contact email, phone, address, and fixed-currency fields. It follows `a4d23d7d11a5`. The local SQLite database was backed up and upgraded to `c51d47a9291f`; the backup is `backend\\instance\\don_prosy.db.20261116-195152.bak`. `flask db check` found no model/migration differences. Do not reset the local database. A PostgreSQL migration run is still required before production.

## Verification

- Backend: `backend\\.venv\\Scripts\\python.exe -m pytest -q` — **41 passed** (six existing test `datetime.utcnow()` deprecation warnings).
- Frontend: `npm run build` — **passed**.
- Editor diagnostics on the changed primary frontend pages and app shell — **no errors found**.
- `git diff --check` — **passed** (Git reports a benign LF/CRLF conversion warning).
- Migration status — local SQLite schema at `c51d47a9291f`; `flask db check` previously passed after upgrade.

## Remaining acceptance gates

1. Reconcile real pilot business workflows and period totals against source transactions, including refunds and receivables.
2. Verify migrations and key transaction/inventory behavior on the target PostgreSQL version.
3. Perform browser-driven acceptance for roles, protected routes, switching among multiple businesses, responsive layouts, and sale/receipt/expense workflows.
4. Complete accessibility, backup/restore, performance, deployment configuration, and operational readiness checks.

Stage 5 is prepared, not implemented. The future assistant should obtain minimal context through authorized business APIs and the financial-summary service. Provider selection, AI endpoints, conversations, quotas, usage accounting, data-retention policy, and privacy/safety evaluation remain Stage 5 work. No business data is currently sent to an AI provider.
