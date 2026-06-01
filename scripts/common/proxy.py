"""Proxy helper — shared across all tiers and platforms.

Reads from these env vars in priority order:
    1. YOUTUBE_PROXY  (our custom, takes priority — explicit per-service override)
    2. HTTPS_PROXY / https_proxy
    3. ALL_PROXY / all_proxy

Usage:
    from common.proxy import get_proxy, apply_to_env
    proxy = get_proxy()
    if proxy:
        apply_to_env(proxy)  # sets HTTP_PROXY/HTTPS_PROXY for libraries that read env
"""

from __future__ import annotations
import os

_PROXY_VARS = ("YOUTUBE_PROXY", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy")


def get_proxy() -> str | None:
    """Return the first non-empty proxy URL from env vars, or None."""
    for var in _PROXY_VARS:
        val = os.environ.get(var, "")
        if val:
            return val
    return None


def apply_to_env(proxy: str | None = None) -> None:
    """Set HTTP_PROXY/HTTPS_PROXY if not already set, so request libraries pick them up.

    If proxy is None, calls get_proxy() internally.
    """
    proxy = proxy or get_proxy()
    if not proxy:
        return
    for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        if not os.environ.get(var):
            os.environ[var] = proxy
