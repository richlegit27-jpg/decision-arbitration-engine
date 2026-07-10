# Stale Public Home Archive ? 2026-07-10

Archived after the homepage polish audit confirmed that active `/` and `/nova-home-preview`
routes render `templates/nova_landing_home.html`.

Archived files:

- `templates/home.html`
  - Reason: stale default copy: "This is the main page of your app."
  - No exact active references found before move.

- `static/js/nova-home-final-polish.js`
  - Reason: no active references found.
  - The active homepage uses `static/js/nova-landing-home.js`.

Not archived:

- `templates/landing.html`
  - Reason: `nova/backend/main.py` still references `landing.html`, so it is not safe to move during this pass.

Do not touch mobile files as part of this cleanup.
