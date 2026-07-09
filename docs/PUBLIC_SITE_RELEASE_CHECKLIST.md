# Nova Public Site Release Checklist

This checklist covers the public Nova funnel only.

It intentionally avoids mobile files, Stripe enforcement, email backend wiring, and billing logic.

## Public funnel

Core public routes:

- /nova-home-preview
- /about
- /features
- /roadmap
- /faq
- /nova-status
- /billing
- /blog
- /contact
- /early-access
- /privacy
- /terms

Workspace route:

- /richard-login

Utility routes:

- /sitemap.xml
- /robots.txt

Error routes:

- Public missing pages should render the Nova 404 page.
- Missing /api/ routes should return JSON 404.

## Public assets

Brand assets:

- C:\Users\Owner\nova\static\favicon.svg
- C:\Users\Owner\nova\static\site.webmanifest
- C:\Users\Owner\nova\static\nova-og.svg

Smoke test:

- C:\Users\Owner\nova\tools\nova_public_smoke.py

Run:

    cd C:\Users\Owner\nova
    python "C:\Users\Owner\nova\tools\nova_public_smoke.py"

Expected final line:

    PUBLIC SMOKE PASSED

## Safe commit rule

Never use:

    git add -A

For public-site polish, stage only the exact public files changed.

Before committing, always check:

    git diff --cached --stat
    git diff --cached --name-only | Select-String -Pattern "mobile"

The mobile check should show nothing.

## Current public polish commits

Latest public polish sequence:

- Add public SEO routes
- Add Nova privacy and terms pages
- Wire legal links into public pages
- Add public Nova 404 page
- Add Nova favicon and web manifest
- Add Nova social preview metadata
- Add public site smoke test

## Still separate

These are intentionally separate from public-site polish:

- Mobile session cleanup
- Mobile attachment preview cleanup
- Mobile chat UI cleanup
- Mobile working backups
- Billing enforcement
- Stripe checkout
- Email/contact form backend
