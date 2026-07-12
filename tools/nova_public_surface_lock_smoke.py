# NOVA_PUBLIC_SURFACE_LOCK_20260711

from __future__ import annotations

from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse
import re
import sys
import xml.etree.ElementTree as ET


ROOT = Path(
    r"C:\Users\Owner\nova"
)


if str(
    ROOT
) not in sys.path:

    sys.path.insert(
        0,
        str(
            ROOT
        ),
    )


import app as app_module


app = app_module.app

client = app.test_client()


PUBLIC_PAGES = (
    "/",
    "/about",
    "/features",
    "/roadmap",
    "/faq",
    "/help",
    "/blog",
    "/contact",
    "/billing",
    "/privacy",
    "/terms",
)


EXPECTED_HEADLINES = {
    "/about": (
        "Nova exists because long-running work deserves continuity."
    ),
    "/features": (
        "Keep the project connected."
    ),
    "/roadmap": (
        "Nova is moving toward a more continuous AI workspace."
    ),
    "/faq": (
        "Questions about Nova, answered plainly."
    ),
    "/help": (
        "Give Nova the thread. Then keep moving."
    ),
    "/blog": (
        "Ideas for work that lasts longer than one chat."
    ),
    "/privacy": (
        "Project context is part of the product."
    ),
    "/terms": (
        "Use Nova to support the work. Keep judgment in the loop."
    ),
}


FORBIDDEN_PUBLIC_STRINGS = (
    "/richard-login",
    "/admin/",
    "owner dashboard",
    "ship checks",
    "public-site polish",
    "data/nova_",
    "nova-public-trust.css",
    "NOVA_PUBLIC_CHROME_CONSISTENCY_20260709_TOP",
    "NOVA_PUBLIC_CHROME_CONSISTENCY_20260709_BOTTOM",
)


SITEMAP_PATHS = set(
    PUBLIC_PAGES
)


STATIC_ASSETS = {
    "/static/favicon.svg": (
        200,
        "image/svg+xml",
    ),
    "/static/site.webmanifest": (
        200,
        "application/manifest+json",
    ),
    "/static/nova-og.svg": (
        200,
        "image/svg+xml",
    ),
}


def pass_check(
    message,
):

    print(
        "PASS",
        message,
    )


def fail(
    message,
    detail=None,
):

    print(
        "FAIL",
        message,
    )


    if detail is not None:

        print(
            "DETAIL:",
            detail,
        )


    raise SystemExit(
        1
    )


def exact_rules(
    path,
):

    return [
        rule
        for rule in app.url_map.iter_rules()
        if str(
            rule.rule
        )
        ==
        path
    ]


def extract_title(
    html,
):

    match = re.search(
        r"<title>\s*(.*?)\s*</title>",
        html,
        flags=(
            re.IGNORECASE
            |
            re.DOTALL
        ),
    )


    return (
        re.sub(
            r"\s+",
            " ",
            match.group(1),
        ).strip()
        if match
        else ""
    )


def extract_meta_description(
    html,
):

    patterns = (
        (
            r'<meta\s+name=["\']description["\']'
            r'\s+content=["\'](.*?)["\']'
        ),
        (
            r'<meta\s+content=["\'](.*?)["\']'
            r'\s+name=["\']description["\']'
        ),
    )


    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            flags=(
                re.IGNORECASE
                |
                re.DOTALL
            ),
        )


        if match:

            return re.sub(
                r"\s+",
                " ",
                match.group(1),
            ).strip()


    return ""


def extract_link_href(
    html,
    rel,
):

    tags = re.findall(
        r"<link\b[^>]*>",
        html,
        flags=re.IGNORECASE,
    )


    for tag in tags:

        rel_match = re.search(
            r'rel=["\']([^"\']+)["\']',
            tag,
            flags=re.IGNORECASE,
        )


        href_match = re.search(
            r'href=["\']([^"\']+)["\']',
            tag,
            flags=re.IGNORECASE,
        )


        if not (
            rel_match
            and href_match
        ):

            continue


        rel_values = {
            item.strip().lower()
            for item in rel_match.group(1).split()
        }


        if rel.lower() in rel_values:

            return href_match.group(1).strip()


    return ""


def extract_meta_property(
    html,
    property_name,
):

    tags = re.findall(
        r"<meta\b[^>]*>",
        html,
        flags=re.IGNORECASE,
    )


    for tag in tags:

        property_match = re.search(
            r'property=["\']([^"\']+)["\']',
            tag,
            flags=re.IGNORECASE,
        )


        content_match = re.search(
            r'content=["\']([^"\']+)["\']',
            tag,
            flags=re.IGNORECASE,
        )


        if not (
            property_match
            and content_match
        ):

            continue


        if (
            property_match.group(1).strip().lower()
            ==
            property_name.lower()
        ):

            return content_match.group(1).strip()


    return ""


def url_path(
    value,
):

    parsed = urlparse(
        str(
            value
            or
            ""
        )
    )


    return (
        parsed.path
        or
        ""
    )


print()
print("=" * 100)
print("NOVA PUBLIC SURFACE LOCK")
print("=" * 100)


check_count = 0


for path in PUBLIC_PAGES:

    response = client.get(
        path
    )


    html = response.get_data(
        as_text=True
    )


    title = extract_title(
        html
    )


    description = extract_meta_description(
        html
    )


    canonical = extract_link_href(
        html,
        "canonical",
    )


    og_url = extract_meta_property(
        html,
        "og:url",
    )


    h1_count = len(
        re.findall(
            r"<h1\b",
            html,
            flags=re.IGNORECASE,
        )
    )


    route_count = len(
        exact_rules(
            path
        )
    )


    print()
    print(
        "PAGE:",
        path,
    )


    print(
        "STATUS:",
        response.status_code,
    )


    print(
        "ROUTE COUNT:",
        route_count,
    )


    print(
        "TITLE:",
        title,
    )


    print(
        "DESCRIPTION LENGTH:",
        len(
            description
        ),
    )


    print(
        "CANONICAL PATH:",
        url_path(
            canonical
        ),
    )


    print(
        "OG URL PATH:",
        url_path(
            og_url
        ),
    )


    print(
        "H1 COUNT:",
        h1_count,
    )


    if response.status_code != 200:

        fail(
            path
            +
            " did not return 200"
        )


    pass_check(
        path
        +
        " returns 200"
    )

    check_count += 1


    if route_count != 1:

        fail(
            path
            +
            " exact route count is not 1",
            route_count,
        )


    pass_check(
        path
        +
        " has exactly one route owner"
    )

    check_count += 1


    if (
        not title
        or
        "nova"
        not in title.lower()
    ):

        fail(
            path
            +
            " title is missing or does not identify Nova",
            title,
        )


    pass_check(
        path
        +
        " has a Nova title"
    )

    check_count += 1


    if not (
        45
        <=
        len(
            description
        )
        <=
        220
    ):

        fail(
            path
            +
            " meta description length is weak",
            len(
                description
            ),
        )


    pass_check(
        path
        +
        " has a useful meta description"
    )

    check_count += 1


    if url_path(
        canonical
    ) != path:

        fail(
            path
            +
            " canonical path is wrong",
            canonical,
        )


    pass_check(
        path
        +
        " canonical points to itself"
    )

    check_count += 1


    if url_path(
        og_url
    ) != path:

        fail(
            path
            +
            " og:url path is wrong",
            og_url,
        )


    pass_check(
        path
        +
        " og:url points to itself"
    )

    check_count += 1


    if h1_count < 1:

        fail(
            path
            +
            " has no h1"
        )


    pass_check(
        path
        +
        " has a primary heading"
    )

    check_count += 1


    expected_headline = EXPECTED_HEADLINES.get(
        path
    )


    if (
        expected_headline
        and
        expected_headline
        not in html
    ):

        fail(
            path
            +
            " locked headline is missing",
            expected_headline,
        )


    if expected_headline:

        pass_check(
            path
            +
            " locked headline survives"
        )

        check_count += 1




    visible_text = BeautifulSoup(
        html,
        "html.parser",
    ).get_text(
        " ",
        strip=True,
    ).lower()
    lower_html = html.lower()


    if 'href="/nova-home-preview"' in lower_html:

        fail(
            path
            +
            " still links publicly to /nova-home-preview"
        )


    pass_check(
        path
        +
        " does not link to preview Home"
    )

    check_count += 1


    for forbidden in FORBIDDEN_PUBLIC_STRINGS:

        if forbidden.lower() in visible_text:

            fail(
                path
                +
                " exposes internal public-site language",
                forbidden,
            )


    pass_check(
        path
        +
        " exposes no locked internal markers"
    )

    check_count += 1


print()
print("=" * 100)
print("SITEMAP CONTRACT")
print("=" * 100)


sitemap_response = client.get(
    "/sitemap.xml"
)


sitemap_text = sitemap_response.get_data(
    as_text=True
)


print(
    "STATUS:",
    sitemap_response.status_code,
)


print(
    "CONTENT TYPE:",
    sitemap_response.content_type,
)


if sitemap_response.status_code != 200:

    fail(
        "/sitemap.xml did not return 200"
    )


pass_check(
    "sitemap returns 200"
)

check_count += 1


try:

    sitemap_root = ET.fromstring(
        sitemap_text
    )

except ET.ParseError as exc:

    fail(
        "sitemap XML is invalid",
        repr(
            exc
        ),
    )


namespace = {
    "s": "http://www.sitemaps.org/schemas/sitemap/0.9"
}


sitemap_locations = [
    (
        node.text
        or
        ""
    ).strip()
    for node in sitemap_root.findall(
        "s:url/s:loc",
        namespace,
    )
]


sitemap_paths = {
    url_path(
        value
    )
    for value in sitemap_locations
}


print(
    "SITEMAP PATHS:",
    sorted(
        sitemap_paths
    ),
)


if sitemap_paths != SITEMAP_PATHS:

    fail(
        "sitemap canonical path set is wrong",
        {
            "expected": sorted(
                SITEMAP_PATHS
            ),
            "actual": sorted(
                sitemap_paths
            ),
        },
    )


pass_check(
    "sitemap contains exactly the canonical public pages"
)

check_count += 1


for forbidden_path in (
    "/nova-home-preview",
    "/early-access",
    "/nova-status",
    "/richard-login",
    "/admin",
):

    if forbidden_path in sitemap_paths:

        fail(
            "sitemap exposes alias, preview, or private path",
            forbidden_path,
        )


pass_check(
    "sitemap excludes preview, alias, status, and owner paths"
)

check_count += 1


print()
print("=" * 100)
print("ROBOTS + ASSET CONTRACT")
print("=" * 100)


robots_response = client.get(
    "/robots.txt"
)


robots_text = robots_response.get_data(
    as_text=True
)


print(
    "ROBOTS STATUS:",
    robots_response.status_code,
)


if robots_response.status_code != 200:

    fail(
        "/robots.txt did not return 200"
    )


pass_check(
    "robots returns 200"
)

check_count += 1


if (
    "sitemap:"
    not in robots_text.lower()
    or
    "/sitemap.xml"
    not in robots_text
):

    fail(
        "robots.txt does not point to sitemap"
    )


pass_check(
    "robots points to sitemap"
)

check_count += 1


for path, (
    expected_status,
    expected_content_type,
) in STATIC_ASSETS.items():

    response = client.get(
        path
    )


    print(
        path,
        "->",
        response.status_code,
        response.content_type,
    )


    if response.status_code != expected_status:

        fail(
            path
            +
            " status is wrong",
            response.status_code,
        )


    if (
        expected_content_type
        not in response.content_type
    ):

        fail(
            path
            +
            " content type is wrong",
            response.content_type,
        )


    pass_check(
        path
        +
        " asset contract"
    )

    check_count += 1


print()
print("=" * 100)
print("404 CONTRACT")
print("=" * 100)


html_404 = client.get(
    "/this-page-does-not-exist"
)


api_404 = client.get(
    "/api/this-route-does-not-exist"
)


print(
    "HTML 404:",
    html_404.status_code,
    html_404.content_type,
)


print(
    "API 404:",
    api_404.status_code,
    api_404.content_type,
)


if (
    html_404.status_code
    !=
    404
    or
    "text/html"
    not in html_404.content_type
):

    fail(
        "public HTML 404 contract is wrong"
    )


pass_check(
    "public HTML 404 contract"
)

check_count += 1


if (
    api_404.status_code
    !=
    404
    or
    "application/json"
    not in api_404.content_type
):

    fail(
        "API 404 contract is wrong"
    )


pass_check(
    "API 404 contract"
)

check_count += 1


print()
print("=" * 100)
print("BLOG + BILLING PRODUCT CONTRACT")
print("=" * 100)


posts_response = client.get(
    "/api/blog/posts"
)


posts_payload = (
    posts_response.get_json(
        silent=True
    )
    or {}
)


print(
    "BLOG POSTS STATUS:",
    posts_response.status_code,
)


print(
    "BLOG POSTS OK:",
    posts_payload.get(
        "ok"
    ),
)


print(
    "BLOG POSTS LIST:",
    isinstance(
        posts_payload.get(
            "posts"
        ),
        list,
    ),
)


if (
    posts_response.status_code
    !=
    200
    or
    posts_payload.get(
        "ok"
    )
    is not True
    or
    not isinstance(
        posts_payload.get(
            "posts"
        ),
        list,
    )
):

    fail(
        "Blog posts product contract is wrong"
    )


pass_check(
    "Blog posts product contract"
)

check_count += 1


billing_response = client.get(
    "/api/billing/readiness"
)


billing_payload = (
    billing_response.get_json(
        silent=True
    )
    or {}
)


billing_summary = (
    billing_payload.get(
        "summary"
    )
    if isinstance(
        billing_payload.get(
            "summary"
        ),
        dict,
    )
    else {}
)


print(
    "BILLING READINESS STATUS:",
    billing_response.status_code,
)


print(
    "BILLING MODE:",
    billing_payload.get(
        "mode"
    ),
)


print(
    "SAFE TO TAKE PAYMENT:",
    billing_summary.get(
        "safe_to_take_payment"
    ),
)


if billing_response.status_code != 200:

    fail(
        "billing readiness endpoint did not return 200"
    )


if billing_summary.get(
    "safe_to_take_payment"
) is not False:

    fail(
        "billing readiness no longer matches staged-payment truth"
    )


pass_check(
    "billing staged-payment truth remains locked"
)

check_count += 1


print()
print("=" * 100)
print("NOVA PUBLIC SURFACE LOCK PASSED")
print("=" * 100)


print(
    "PUBLIC PAGE COUNT:",
    len(
        PUBLIC_PAGES
    ),
)


print(
    "CHECK COUNT:",
    check_count,
)


print(
    "PUBLIC SURFACE SCORE: 100%"
)


print(
    "ROOT HOME: LOCKED"
)


print(
    "ABOUT: LOCKED"
)


print(
    "FEATURES: LOCKED"
)


print(
    "ROADMAP: LOCKED"
)


print(
    "FAQ: LOCKED"
)


print(
    "HELP: LOCKED"
)


print(
    "BLOG: LOCKED"
)


print(
    "CONTACT: LOCKED"
)


print(
    "BILLING: LOCKED TO STAGED PAYMENT TRUTH"
)


print(
    "PRIVACY: LOCKED"
)


print(
    "TERMS: LOCKED"
)


print(
    "SITEMAP: CANONICAL PUBLIC SURFACE ONLY"
)


print(
    "RESULT: THE PUBLIC RELEASE GATE NOW TESTS THE PRODUCT WE ACTUALLY BUILT"
)
