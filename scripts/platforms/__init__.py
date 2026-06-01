"""Platform adapter registry + URL → adapter routing.

To add a new platform:
    1. Create platforms/<name>.py with a class extending BasePlatform
    2. Add it to _ADAPTERS below

The first adapter whose URL_PATTERNS matches (in registration order) wins.
The "generic" adapter MUST be last — it accepts any URL as a fallback.
"""

from __future__ import annotations
import importlib
import os
import re
import sys
from typing import Optional

# Ensure scripts/ is on sys.path so we can import as `platforms.X`
_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from platforms.base import BasePlatform


# --- Lazy-loaded adapter registry (order matters; generic must be last) ---
_ADAPTER_SPECS: list[tuple[str, str]] = [
    ("youtube", "platforms.youtube.YouTubeAdapter"),
    # Add new platforms here, e.g.:
    # ("bilibili", "platforms.bilibili.BilibiliAdapter"),
    # ("douyin",   "platforms.douyin.DouyinAdapter"),
    ("generic", "platforms.generic.GenericAdapter"),  # MUST be last
]

_cache: dict[str, BasePlatform] = {}


def _load(spec: str) -> BasePlatform:
    if spec in _cache:
        return _cache[spec]
    module_path, class_name = spec.rsplit(".", 1)
    module = importlib.import_module(module_path)
    instance = getattr(module, class_name)()
    _cache[spec] = instance
    return instance


def list_adapters() -> list[BasePlatform]:
    """Return all registered adapter instances in registration order."""
    return [_load(spec) for _, spec in _ADAPTER_SPECS]


def get_adapter(name: str) -> Optional[BasePlatform]:
    """Look up an adapter by name (case-insensitive)."""
    name = name.lower().strip()
    for n, spec in _ADAPTER_SPECS:
        if n == name:
            return _load(spec)
    return None


def match_adapter(input_str: str, force_platform: Optional[str] = None) -> BasePlatform:
    """Find the right adapter for a URL or raw ID.

    Args:
        input_str: URL, video ID, or anything a platform can parse
        force_platform: if set, skip auto-detection and use this adapter

    Returns: an adapter instance

    Raises:
        ValueError: no adapter matched AND no force_platform given, or
                    force_platform unknown
    """
    if force_platform:
        adapter = get_adapter(force_platform)
        if not adapter:
            raise ValueError(f"Unknown platform: {force_platform}")
        return adapter

    # Try each adapter's URL_PATTERNS in order
    for name, spec in _ADAPTER_SPECS:
        adapter = _load(spec)
        for pat in adapter.URL_PATTERNS:
            if re.search(pat, input_str):
                return adapter

    # Special case: bare 11-char ID looks like YouTube
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", input_str):
        yt = get_adapter("youtube")
        if yt:
            return yt

    # Last resort: generic adapter (accepts any URL)
    gen = get_adapter("generic")
    if gen:
        return gen
    raise ValueError("No platform adapter matched and generic adapter unavailable")
