# Nova Launch Ready Checkpoint — Staged Payments

Date: 2026-07-10

Tag:
nova-launch-ready-staged-payments-20260710

Commit:
aec736e Clarify launch checklist ready state

Branch:
post-frontend-polish-phase

## What is ready

- Public pages pass smoke checks.
- Admin dashboard passes owner/admin checks.
- Leads page and filtered CSV export pass checks.
- Sitemap and robots assets pass checks.
- `/nova-home-preview` is included in the sitemap.
- Billing page is live as an account/status dashboard.
- Billing readiness API is live.
- Billing plans API is live.
- Admin billing readiness page is live.
- Launch checklist has Ready / Planned / Blocked visibility.
- Model gateway has billing/credit enforcement wiring.
- Chat service direct model calls are routed through the gateway.
- Usage enforcement readiness reports true for gateway and chat paths.

## Payment safety state

Nova is not enabled to take real payments yet.

Expected live-safe state:

- `mode`: `staged_planned`
- `safe_to_take_payment`: `false`
- checkout route: `live=false`, `processed=false`
- portal route: `live=false`, `processed=false`
- Stripe webhook route: `live=false`, `processed=false`

## Known blockers before real paid launch

- `NOVA_PAYMENTS_LIVE` must be intentionally enabled.
- `STRIPE_SECRET_KEY` must be configured.
- `STRIPE_WEBHOOK_SECRET` must be configured.
- Paid Stripe price IDs must be configured.
- Real checkout, portal, invoice, webhook verification, and paid upgrade flows must be tested before accepting payment.

## Validation performed

- Local public release check passed.
- Local admin release check passed.
- Local full release check passed.
- Railway live release check passed.
- Live staged payments safety assertion passed.
- Live checklist deployment confirmed after Railway caught up.
- Git working tree was clean before tagging.

## Do not accidentally change

- Do not enable live payments without completing Stripe config and webhook verification.
- Do not remove staged payment safety guards.
- Do not bypass model gateway usage enforcement.
- Do not commit accidental mobile files during public/admin polish.
