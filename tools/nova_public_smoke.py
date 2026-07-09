from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable

from app import app


@dataclass(frozen=True)
class Check:
    path: str
    expected_status: int
    expected_type: str
    markers: tuple[str, ...] = ()


def body_text(response) -> str:
    return response.get_data(as_text=True)


def has_json_404(text: str) -> bool:
    return '"ok": false' in text and '"error": "Not found"' in text


def main() -> int:
    checks = [
        Check(
            "/nova-home-preview",
            200,
            "text/html",
            (
                "/static/favicon.svg",
                "/static/site.webmanifest",
                "og:title",
                "twitter:card",
                "/static/nova-og.svg",
                'href="/contact"',
                'href="/privacy"',
                'href="/terms"',
            ),
        ),
        Check(
            "/contact",
            200,
            "text/html",
            (
                "/static/favicon.svg",
                "/static/site.webmanifest",
                "og:title",
                "twitter:card",
                "/static/nova-og.svg",
                'href="/privacy"',
                'href="/terms"',
            ),
        ),
        Check(
            "/privacy",
            200,
            "text/html",
            (
                "Privacy — Nova",
                "/static/favicon.svg",
                "/static/site.webmanifest",
                "og:title",
                "twitter:card",
                "/static/nova-og.svg",
                'href="/terms"',
            ),
        ),
        Check(
            "/terms",
            200,
            "text/html",
            (
                "Terms — Nova",
                "/static/favicon.svg",
                "/static/site.webmanifest",
                "og:title",
                "twitter:card",
                "/static/nova-og.svg",
                'href="/privacy"',
            ),
        ),
        Check(
            "/billing",
            200,
            "text/html",
            (
                "/static/favicon.svg",
                "/static/site.webmanifest",
                "og:title",
                "twitter:card",
                "/static/nova-og.svg",
                'href="/privacy"',
                'href="/terms"',
            ),
        ),
        Check(
            "/blog",
            200,
            "text/html",
            (
                "/static/favicon.svg",
                "/static/site.webmanifest",
                "og:title",
                "twitter:card",
                "/static/nova-og.svg",
                'href="/privacy"',
                'href="/terms"',
            ),
        ),
        Check(
            "/faq",
            200,
            "text/html",
            (
                "/static/favicon.svg",
                "/static/site.webmanifest",
                "og:title",
                "twitter:card",
                "/static/nova-og.svg",
                'href="/privacy"',
                'href="/terms"',
            ),
        ),
        Check(
            "/roadmap",
            200,
            "text/html",
            (
                "/static/favicon.svg",
                "/static/site.webmanifest",
                "og:title",
                "twitter:card",
                "/static/nova-og.svg",
                'href="/privacy"',
                'href="/terms"',
            ),
        ),
        Check(
            "/sitemap.xml",
            200,
            "application/xml",
            (
                "/nova-home-preview",
                "/contact",
                "/privacy",
                "/terms",
            ),
        ),
        Check(
            "/robots.txt",
            200,
            "text/plain",
            (
                "User-agent: *",
                "Sitemap:",
                "/sitemap.xml",
            ),
        ),
        Check(
            "/static/favicon.svg",
            200,
            "image/svg+xml",
            (
                "<svg",
                "Nova",
            ),
        ),
        Check(
            "/static/site.webmanifest",
            200,
            "application/manifest+json",
            (
                '"name": "Nova"',
                '"/static/favicon.svg"',
            ),
        ),
        Check(
            "/static/nova-og.svg",
            200,
            "image/svg+xml",
            (
                "<svg",
                "AI project command center",
            ),
        ),
        Check(
            "/this-page-does-not-exist",
            404,
            "text/html",
            (
                "This route drifted out of orbit",
                "/static/favicon.svg",
                "/static/site.webmanifest",
                "og:title",
                "twitter:card",
                "/static/nova-og.svg",
            ),
        ),
        Check(
            "/api/this-route-does-not-exist",
            404,
            "application/json",
            (
                '"ok": false',
                '"error": "Not found"',
            ),
        ),
    ]

    failures: list[str] = []

    with app.test_client() as client:
        for check in checks:
            response = client.get(check.path)
            text = body_text(response)
            content_type = response.content_type or ""

            print(
                f"{check.path} -> "
                f"{response.status_code} | "
                f"{content_type}"
            )

            if response.status_code != check.expected_status:
                failures.append(
                    f"{check.path}: expected status {check.expected_status}, got {response.status_code}"
                )

            if check.expected_type not in content_type:
                failures.append(
                    f"{check.path}: expected content type containing {check.expected_type!r}, got {content_type!r}"
                )

            for marker in check.markers:
                if marker not in text:
                    failures.append(
                        f"{check.path}: missing marker {marker!r}"
                    )

    if failures:
        print("")
        print("PUBLIC SMOKE FAILED")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("")
    print("PUBLIC SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
