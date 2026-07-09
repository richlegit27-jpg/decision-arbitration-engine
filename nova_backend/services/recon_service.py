from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests


HREF_RE = re.compile(r'href=["\'](.*?)["\']', re.IGNORECASE)
SRC_RE = re.compile(r'src=["\'](.*?)["\']', re.IGNORECASE)
PARAM_RE = re.compile(r"[?&]([a-zA-Z0-9_\-]+)=")
JS_ENDPOINT_RE = re.compile(r'["\'](/api/[^"\']+)["\']')
FORM_RE = re.compile(r"<form\b[^>]*>(.*?)</form>", re.IGNORECASE | re.DOTALL)
FORM_ACTION_RE = re.compile(r'action=["\'](.*?)["\']', re.IGNORECASE)
FORM_METHOD_RE = re.compile(r'method=["\'](.*?)["\']', re.IGNORECASE)
INPUT_NAME_RE = re.compile(r'<input\b[^>]*name=["\'](.*?)["\']', re.IGNORECASE)


class ReconService:
    def __init__(self, timeout: int = 10, user_agent: str | None = None):
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

    # -----------------------
    # HTTP
    # -----------------------

    def _headers(self) -> dict:
        return {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
        }

    def normalize_url(self, url: str) -> str:
        value = str(url or "").strip()
        if not value:
            return ""
        if not value.startswith(("http://", "https://")):
            value = "https://" + value
        return value

    def fetch(self, url: str) -> str:
        target = self.normalize_url(url)
        if not target:
            return ""

        try:
            return requests.get(
                target,
                timeout=self.timeout,
                headers=self._headers(),
                allow_redirects=True,
            ).text
        except requests.exceptions.SSLError:
            try:
                return requests.get(
                    target,
                    timeout=self.timeout,
                    headers=self._headers(),
                    allow_redirects=True,
                    verify=False,
                ).text
            except Exception:
                return ""
        except Exception:
            return ""

    def fetch_text(self, url: str) -> str:
        return self.fetch(url)

    # -----------------------
    # EXTRACTION
    # -----------------------

    def extract_links(self, html: str, base_url: str) -> List[str]:
        links = set()
        base = self.normalize_url(base_url)

        for match in HREF_RE.findall(str(html or "")):
            if match:
                links.add(urljoin(base, match))

        for match in SRC_RE.findall(str(html or "")):
            if match:
                links.add(urljoin(base, match))

        return sorted(links)

    def extract_js_files(self, links: List[str]) -> List[str]:
        js_files = []
        for link in links:
            value = str(link or "").strip().lower()
            if ".js" in value:
                js_files.append(str(link).strip())
        return sorted(set(js_files))

    def extract_params(self, urls: List[str]) -> Dict[str, List[str]]:
        params: Dict[str, List[str]] = {}

        for url in urls:
            found = PARAM_RE.findall(str(url or ""))
            if found:
                params[str(url)] = sorted(set(found))

        return params

    def extract_js_endpoints(self, js_urls: List[str]) -> List[str]:
        endpoints = set()

        for js in js_urls:
            try:
                content = requests.get(
                    js,
                    timeout=self.timeout,
                    headers=self._headers(),
                    allow_redirects=True,
                ).text
                matches = JS_ENDPOINT_RE.findall(content)
                endpoints.update(matches)
            except requests.exceptions.SSLError:
                try:
                    content = requests.get(
                        js,
                        timeout=self.timeout,
                        headers=self._headers(),
                        allow_redirects=True,
                        verify=False,
                    ).text
                    matches = JS_ENDPOINT_RE.findall(content)
                    endpoints.update(matches)
                except Exception:
                    continue
            except Exception:
                continue

        return sorted(endpoints)

    def extract_forms(self, html: str, base_url: str) -> List[dict]:
        forms: List[dict] = []
        base = self.normalize_url(base_url)

        for block in FORM_RE.findall(str(html or "")):
            action_match = FORM_ACTION_RE.search(block)
            method_match = FORM_METHOD_RE.search(block)
            input_names = INPUT_NAME_RE.findall(block)

            action = action_match.group(1).strip() if action_match else ""
            method = method_match.group(1).strip().upper() if method_match else "GET"

            forms.append(
                {
                    "action": urljoin(base, action) if action else base,
                    "method": method,
                    "inputs": sorted(set([str(x).strip() for x in input_names if str(x).strip()])),
                }
            )

        return forms

    # -----------------------
    # ANALYSIS
    # -----------------------

    def analyze_params(self, param_map: Dict[str, List[str]]) -> List[dict]:
        findings: List[dict] = []

        for url, params in (param_map or {}).items():
            for p in params:
                risk = "low"
                notes: List[str] = []

                pname = str(p or "").lower()

                if "id" in pname:
                    risk = "medium"
                    notes.append("Possible IDOR / enumeration")

                if "q" == pname or "query" in pname or "search" in pname:
                    if risk != "high":
                        risk = "medium"
                    notes.append("Possible XSS / injection point")

                if "redirect" in pname or pname == "url" or "return" in pname or "next" in pname:
                    risk = "high"
                    notes.append("Possible open redirect")

                if "file" in pname or "path" in pname or "folder" in pname:
                    risk = "high"
                    notes.append("Possible LFI / path traversal")

                if "token" in pname or "auth" in pname or "key" in pname or "jwt" in pname:
                    risk = "high"
                    notes.append("Sensitive parameter")

                if "debug" in pname or "test" in pname:
                    if risk == "low":
                        risk = "medium"
                    notes.append("Interesting debug/test parameter")

                findings.append(
                    {
                        "type": "param",
                        "url": str(url or "").strip(),
                        "param": str(p or "").strip(),
                        "risk": risk,
                        "notes": notes,
                    }
                )

        return findings

    def analyze_endpoints(self, endpoints: List[str]) -> List[dict]:
        results: List[dict] = []

        for ep in endpoints:
            risk = "low"
            notes: List[str] = []

            ep_l = str(ep or "").lower()

            if "admin" in ep_l:
                risk = "high"
                notes.append("Admin endpoint")

            if "login" in ep_l or "auth" in ep_l or "signin" in ep_l:
                if risk != "high":
                    risk = "medium"
                notes.append("Auth surface")

            if "upload" in ep_l or "import" in ep_l:
                risk = "high"
                notes.append("Upload surface")

            if "debug" in ep_l or "internal" in ep_l:
                risk = "high"
                notes.append("Debug/internal surface")

            if "user" in ep_l or "profile" in ep_l or "account" in ep_l:
                if risk == "low":
                    risk = "medium"
                notes.append("User/account data surface")

            if "search" in ep_l or "filter" in ep_l:
                if risk == "low":
                    risk = "medium"
                notes.append("Possible input-heavy endpoint")

            results.append(
                {
                    "type": "endpoint",
                    "endpoint": str(ep or "").strip(),
                    "risk": risk,
                    "notes": notes,
                }
            )

        return results

    def analyze_forms(self, forms: List[dict]) -> List[dict]:
        findings: List[dict] = []

        for form in forms:
            action = str(form.get("action") or "").strip()
            method = str(form.get("method") or "GET").strip().upper()
            inputs = form.get("inputs") if isinstance(form.get("inputs"), list) else []

            risk = "low"
            notes: List[str] = []

            lowered_action = action.lower()
            lowered_inputs = [str(x).lower() for x in inputs]

            if method == "POST":
                risk = "medium"
                notes.append("State-changing form surface")

            if any("password" in x for x in lowered_inputs) or "login" in lowered_action:
                if risk != "high":
                    risk = "medium"
                notes.append("Authentication form")

            if any("file" in x for x in lowered_inputs) or "upload" in lowered_action:
                risk = "high"
                notes.append("File upload form")

            if any("redirect" in x or x == "url" for x in lowered_inputs):
                risk = "high"
                notes.append("Possible open redirect input")

            findings.append(
                {
                    "type": "form",
                    "action": action,
                    "method": method,
                    "inputs": inputs,
                    "risk": risk,
                    "notes": notes,
                }
            )

        return findings

    # -----------------------
    # SUMMARY
    # -----------------------

    def summarize_findings(
        self,
        links: List[str],
        js_files: List[str],
        params: Dict[str, List[str]],
        endpoints: List[str],
        forms: List[dict],
        findings: List[dict],
    ) -> dict:
        high = [f for f in findings if str(f.get("risk") or "").lower() == "high"]
        medium = [f for f in findings if str(f.get("risk") or "").lower() == "medium"]
        low = [f for f in findings if str(f.get("risk") or "").lower() == "low"]

        return {
            "counts": {
                "links": len(links),
                "js_files": len(js_files),
                "param_urls": len(params),
                "endpoints": len(endpoints),
                "forms": len(forms),
                "findings_total": len(findings),
                "high": len(high),
                "medium": len(medium),
                "low": len(low),
            },
            "top_findings": (high + medium + low)[:10],
        }

    def build_text_summary(self, summary: dict) -> str:
        counts = summary.get("counts") if isinstance(summary, dict) else {}
        top_findings = summary.get("top_findings") if isinstance(summary, dict) else []

        lines = [
            f'Links found: {counts.get("links", 0)}',
            f'JS files found: {counts.get("js_files", 0)}',
            f'Parameter-bearing URLs: {counts.get("param_urls", 0)}',
            f'JS endpoints found: {counts.get("endpoints", 0)}',
            f'Forms found: {counts.get("forms", 0)}',
            f'Findings: {counts.get("findings_total", 0)} '
            f'(high: {counts.get("high", 0)}, medium: {counts.get("medium", 0)}, low: {counts.get("low", 0)})',
        ]

        for item in top_findings[:5]:
            risk = str(item.get("risk") or "low").upper()
            if item.get("type") == "param":
                lines.append(f'- [{risk}] Param "{item.get("param", "")}" at {item.get("url", "")}')
            elif item.get("type") == "endpoint":
                lines.append(f'- [{risk}] Endpoint {item.get("endpoint", "")}')
            elif item.get("type") == "form":
                lines.append(f'- [{risk}] Form {item.get("method", "GET")} {item.get("action", "")}')

        return "\n".join(lines).strip()

    # -----------------------
    # MAIN
    # -----------------------

    def analyze_target(self, url: str) -> dict:
        target = self.normalize_url(url)
        html = self.fetch(target)

        if not html:
            return {
                "ok": False,
                "url": target,
                "error": "Failed to fetch target",
                "links": [],
                "js_files": [],
                "params": {},
                "endpoints": [],
                "forms": [],
                "findings": [],
                "summary": {},
                "summary_text": "",
            }

        links = self.extract_links(html, target)
        js_files = self.extract_js_files(links)
        params = self.extract_params(links)
        endpoints = self.extract_js_endpoints(js_files)
        forms = self.extract_forms(html, target)

        findings: List[dict] = []
        findings.extend(self.analyze_params(params))
        findings.extend(self.analyze_endpoints(endpoints))
        findings.extend(self.analyze_forms(forms))

        summary = self.summarize_findings(
            links=links,
            js_files=js_files,
            params=params,
            endpoints=endpoints,
            forms=forms,
            findings=findings,
        )

        return {
            "ok": True,
            "url": target,
            "html_length": len(html),
            "links": links,
            "js_files": js_files,
            "params": params,
            "endpoints": endpoints,
            "forms": forms,
            "findings": findings,
            "summary": summary,
            "summary_text": self.build_text_summary(summary),
        }

    # -----------------------
    # ARTIFACT HELPER
    # -----------------------

    def build_artifact_payload(self, result: Dict[str, Any]) -> dict:
        target = str(result.get("url") or "").strip()
        summary_text = str(result.get("summary_text") or "").strip()

        top_findings = []
        summary = result.get("summary")
        if isinstance(summary, dict):
            raw_top = summary.get("top_findings")
            if isinstance(raw_top, list):
                for item in raw_top[:8]:
                    text = ""
                    risk = str(item.get("risk") or "low").upper()

                    if item.get("type") == "param":
                        text = f'[{risk}] Param "{item.get("param", "")}" at {item.get("url", "")}'
                    elif item.get("type") == "endpoint":
                        text = f'[{risk}] Endpoint {item.get("endpoint", "")}'
                    elif item.get("type") == "form":
                        text = f'[{risk}] Form {item.get("method", "GET")} {item.get("action", "")}'

                    if text:
                        top_findings.append(text)

        return {
            "kind": "recon_result",
            "title": f"Recon: {target}" if target else "Recon result",
            "body": summary_text,
            "source": "recon",
            "meta": {
                "url": target,
                "links": result.get("links", []),
                "js_files": result.get("js_files", []),
                "params": result.get("params", {}),
                "endpoints": result.get("endpoints", []),
                "forms": result.get("forms", []),
                "findings": result.get("findings", []),
                "summary": result.get("summary", {}),
            },
            "viewer": {
                "kind": "recon_result",
                "title": f"Recon: {target}" if target else "Recon result",
                "body": summary_text,
                "source_url": target,
                "image_url": "",
                "video_url": "",
                "audio_url": "",
                "analysis_text": summary_text,
                "bullets": top_findings,
            },
        }

