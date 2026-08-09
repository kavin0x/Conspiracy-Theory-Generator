from __future__ import annotations

from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from agents import function_tool
from ddgs import DDGS

_REQUEST_HEADERS = {
    "User-Agent": (
        "ConspiracyTheoryGenerator/2.0 (+https://github.com/; research bot; "
        "link-verification only)"
    ),
    "Accept": "*/*",
}


def _truncate(text: str, limit: int = 220) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def strip_tracking_params(url: str) -> str:
    """Remove common tracking params (utm_*, utm=openai, fbclid, gclid, etc.)."""
    try:
        parsed = urlparse(url)
        filtered = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if not (
                k.lower().startswith("utm")
                or k.lower() in {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}
                or (k == "utm" and v == "openai")
            )
        ]
        if len(filtered) == len(parse_qsl(parsed.query, keep_blank_values=True)):
            return url
        return urlunparse(parsed._replace(query=urlencode(filtered, doseq=True)))
    except (ValueError, TypeError, AttributeError):
        return url


def verify_url(url: str, timeout_seconds: float = 6.0) -> bool:
    """Return True if the URL responds with an HTTP status < 400."""
    url = strip_tracking_params(url)
    if not url.startswith(("http://", "https://")):
        return False

    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=timeout_seconds,
            headers=_REQUEST_HEADERS,
        )
        if response.status_code < 400:
            return True
        if response.status_code in (403, 405, 501):
            response = requests.get(
                url,
                allow_redirects=True,
                timeout=timeout_seconds,
                headers=_REQUEST_HEADERS,
                stream=True,
            )
            try:
                return response.status_code < 400
            finally:
                response.close()
        return False
    except requests.RequestException:
        return False


def _search_raw(query: str, max_results: int) -> list[dict]:
    results = DDGS().text(query, max_results=max_results) or []
    return list(results)


@function_tool
def web_search(query: str, max_results: int = 5) -> List[str]:
    """Search the web and return concise title/snippet strings."""
    max_results = max(1, min(int(max_results), 10))
    snippets: list[str] = []
    try:
        for result in _search_raw(query, max_results):
            title = result.get("title", "")
            body = result.get("body", "")
            href = result.get("href") or result.get("url") or ""
            snippets.append(_truncate(f"{title}: {body} ({href})", 280))
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        raise RuntimeError(f"web_search failed: {exc}") from exc
    return snippets


@function_tool
def verify_url_tool(url: str, timeout_seconds: int = 6) -> bool:
    """Check whether a URL is reachable (HTTP status < 400)."""
    return verify_url(url, timeout_seconds=float(timeout_seconds))


@function_tool
def search_verified_links(query: str, max_results: int = 5) -> List[str]:
    """Search the web and return live, verified https URLs for the query."""
    max_results = max(1, min(int(max_results), 8))
    verified: list[str] = []
    try:
        for result in _search_raw(query, max_results * 4):
            raw = result.get("href") or result.get("url") or ""
            url = strip_tracking_params(raw)
            if url and verify_url(url) and url not in verified:
                verified.append(url)
            if len(verified) >= max_results:
                break
    except Exception:  # pylint: disable=broad-exception-caught
        # Fail soft: return whatever links were verified before the failure.
        return verified
    return verified
