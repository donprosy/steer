# Product Requirements — Don Prosy Business Manager

## Product summary

Don Prosy Business Manager is a web-based SaaS platform that gives small business owners one dependable place to organise customers, products, inventory, sales, expenses, and business performance. A future text-based AI assistant will help users interpret their own business information and produce practical summaries.

The first release should prioritise trustworthy core workflows, understandable financial summaries, and strong separation of each business's data. It should not attempt to be a full accounting or enterprise resource planning system.

## Target customers

- Owner-operated and small businesses that currently rely on notebooks, spreadsheets, or disconnected applications.
- Retailers and other inventory-based businesses that need a clearer picture of stock, sales, and cash performance.
- Service businesses that need to track customers, sales, expenses, and reports without managing stock.
- Small teams that need a shared view of business operations with owner-controlled access.

Initial launch geography and any jurisdiction-specific tax/accounting requirements are to be confirmed before those capabilities are designed.

## Problems addressed

- Business information is scattered and difficult to keep current.
- Owners cannot easily connect sales, costs, stock, and customer activity.
- Manual reporting is time-consuming and makes trends hard to spot.
- Owners need practical guidance but may not have ready access to business analysis.
- Growing businesses need a simple step up from spreadsheets without enterprise complexity.

## Product goals and non-goals

**Goals**

- Make routine business information easy to record and review.
- Provide clear, consistent revenue, expense, and profit views, with definitions users can understand.
- Make business-specific access isolation a core design constraint.
- Establish a sustainable paid product with transparent plan-based limits.
- Keep the initial system modular enough to grow without premature complexity.

**Non-goals for the initial release**

- Voice AI (planned only as a possible later upgrade).
- A replacement for regulated accounting, tax filing, payroll, or banking software.
- A fabricated or simulated payment integration.
- Advanced multi-region enterprise tenancy or custom reporting engines before validated demand.

## Main capabilities

1. **Business dashboard:** At-a-glance sales, expenses, estimated profit, stock alerts, and recent activity.
2. **Customer management:** Customer profiles, contact details, and links to sales history.
3. **Product and inventory management:** Product catalogue, stock movements, and low-stock visibility.
4. **Sales tracking:** Recorded sales and line items, with totals tied to the selected business.
5. **Expense tracking:** Categorised expenses with dates, amounts, and optional supporting notes.
6. **Reports and analytics:** Period-based operational summaries that clearly explain calculations.
7. **Text AI business assistant (future):** User-requested analysis and generated summaries using only authorised business context, with usage limits and clear AI caveats.
8. **Subscriptions and administration (future):** Plans, entitlements, billing status, and a restricted platform operations console.

## Roles

- **Business owner:** Creates or controls one or more business workspaces, invites team members in a later iteration, and manages subscription settings.
- **Business staff (future):** Performs only explicitly permitted work within assigned businesses.
- **Platform administrator:** Performs limited, audited platform support and account operations; not a routine business user.
- **Unauthenticated visitor:** Can access public marketing and account entry pages only.

Role names are conceptual at Stage 1. Exact permissions and business ownership transfer rules must be defined before authentication is implemented.

## Revenue model

Use recurring subscriptions with Starter, Growth, and Business plan tiers, offered monthly and annually. Plans may vary by business count, team access, reporting depth, and AI reply allowance. Feature limits must be visible and enforced by the backend, not only hidden in the interface.

Paystack is the intended payment provider, subject to country availability, supported currencies, fees, and legal requirements. No payment processing is implemented in Stage 1. Pricing, trial policy, refund policy, and tax treatment require product and jurisdiction validation.

## Success measures

- Activation: proportion of new owners who configure a business and complete a first useful workflow.
- Retention: active businesses and retained paid businesses over time.
- Data quality: completion and correction rates for key records.
- Value: regular use of dashboard and reports, and user-rated usefulness.
- Sustainability: conversion, plan mix, churn, support burden, and AI cost per active subscriber.
- Reliability and safety: availability, error rates, security events, and business data isolation tests.

## Future growth

Start with a focused single-business experience and a clear domain model. Validate the highest-value operational workflows with real users; then add team permissions, plan entitlements, AI analysis, and integrations based on evidence. Voice AI, additional payment methods, accounting integrations, and advanced analytics remain future options rather than launch commitments.

## Design direction

Use an elegant, premium SaaS visual language: calm neutral surfaces, deep green/teal brand accents, restrained warm highlights, excellent readable typography, consistent spacing, and clear hierarchy. Dashboard cards and charts should foreground useful comparisons and accessible labels rather than decoration. Motion should be subtle, purposeful, and respect reduced-motion preferences. Design mobile-first layouts for real operational use. Avoid generic admin-template appearance, crowded screens, and visual effects that compete with the data.

The Stage 1 frontend is only a responsive placeholder to verify the toolchain; it is not the final product UI or brand system.

