from __future__ import annotations

from app import app


def main() -> int:
    with app.test_client() as client:
        contact = client.post(
            "/api/contact",
            json={
                "name": "Smoke Test",
                "email": "smoke@example.com",
                "interest": "product_question",
                "message": "Dry run contact smoke test.",
                "dry_run": True,
            },
        )

        early = client.post(
            "/api/early-access",
            json={
                "name": "Smoke Test",
                "email": "early@example.com",
                "interest": "early_access",
                "message": "Dry run early access smoke test.",
                "dry_run": True,
            },
        )

        invalid = client.post(
            "/api/contact",
            json={
                "email": "not-an-email",
                "message": "Invalid email smoke test.",
                "dry_run": True,
            },
        )

        leads = client.get("/api/leads")

        checks = [
            ("POST /api/contact", contact.status_code, contact.get_json(silent=True)),
            ("POST /api/early-access", early.status_code, early.get_json(silent=True)),
            ("POST /api/contact invalid email", invalid.status_code, invalid.get_json(silent=True)),
            ("GET /api/leads unauthorized", leads.status_code, leads.get_json(silent=True)),
        ]

        failures: list[str] = []

        for label, status, payload in checks:
            print(label, status, payload)

        if contact.status_code != 200 or not (contact.get_json(silent=True) or {}).get("ok"):
            failures.append("contact dry run failed")

        if early.status_code != 200 or not (early.get_json(silent=True) or {}).get("ok"):
            failures.append("early access dry run failed")

        if invalid.status_code != 400:
            failures.append("invalid email did not return 400")

        if leads.status_code != 403:
            failures.append("unauthorized leads endpoint did not return 403")

        if failures:
            print("")
            print("LEAD CAPTURE SMOKE FAILED")
            for failure in failures:
                print(" -", failure)
            return 1

        print("")
        print("LEAD CAPTURE SMOKE PASSED")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
