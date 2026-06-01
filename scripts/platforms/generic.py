"""Generic platform adapter — the "we don't know what this is" fallback.

This adapter handles ANY URL that yt-dlp can process (1500+ sites including
Bilibili, Douyin, Twitter/X, Vimeo, Twitch, etc.). It has no Tier 1
(native subtitle API), so it goes straight to Tier 2 (Deepgram) or Tier 3
(metadata).

When you add a dedicated adapter for a specific platform (e.g. Bilibili),
the new adapter gets registered BEFORE generic and wins URL matching.
"""

from __future__ import annotations
import hashlib
import os
import re
import sys
from typing import Optional

# Make scripts/ importable when run as a standalone script
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.dirname(_HERE)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from platforms.base import BasePlatform  # noqa: E402
from common.metadata import fetch_video_info_via_ytdlp  # noqa: E402


class GenericAdapter(BasePlatform):
    """Catch-all adapter for any URL yt-dlp understands."""

    name = "generic"
    # Generic matches any http(s) URL — must be last in registry
    URL_PATTERNS = [
        r"^https?://.+",
    ]
    SUPPORTS_SUBTITLES = False  # No native Tier 1; relies on Tier 2/3
    REQUIRES_AUTH = False

    def extract_video_id(self, input_str: str) -> str:
        """Use a hash of the URL as a stable video ID for generic adapters.

        We can't extract a real platform-specific ID without knowing the
        platform, so we use a 12-char MD5 prefix — enough to avoid collisions
        in filename generation, and stable across runs (so caching works).
        """
        if not (input_str.startswith("http://") or input_str.startswith("https://")):
            # Auto-add https:// if missing
            input_str = "https://" + input_str
        return hashlib.md5(input_str.encode()).hexdigest()[:12]

    def get_stream_url(self, video_id: str) -> str:
        """Generic adapter can't reconstruct URL from a hash ID.

        The main pipeline MUST pass the original URL — we store it via the
        `_original_urls` dict (set by fetch_transcript.py before calling
        Tier 2/3) so this method is rarely called.
        """
        raise NotImplementedError(
            "Generic adapter cannot reconstruct URL from hash ID. "
            "Pass the original URL via fetch_transcript.py's pipeline."
        )

    def get_info(self, video_id: str) -> dict:
        """For generic adapter, the 'video_id' arg is actually expected to be
        the original URL — see fetch_transcript.py which passes the URL directly
        for generic/platform-unknown cases. We tolerate hash IDs too by
        treating them as URLs (will fail yt-dlp, but won't crash).
        """
        # If it looks like a URL, use it directly; else we can't recover it
        url = video_id if video_id.startswith("http") else f"https://{video_id}"
        video_id = self.extract_video_id(url)

        info = {
            "video_id": video_id,
            "_original_url": url,  # stash for Tier 2/3
            "url": url,
            "platform": self.name,
            "supports_subtitles": self.SUPPORTS_SUBTITLES,
            "available_subtitle_languages": [],
            "deepgram_available": bool(os.environ.get("DEEPGRAM_API_KEY", "")),
        }

        yt_info = fetch_video_info_via_ytdlp(url)
        if yt_info:
            info.update(yt_info)
        else:
            info.setdefault("title", "Unknown")
            info.setdefault("duration_seconds", 0)
            info.setdefault("duration_str", "unknown")

        return info

    def fetch_subtitles(self, video_id: str, language: str = "en") -> Optional[dict]:
        """Generic adapter has no Tier 1 — always returns None.

        The main pipeline will fall back to Tier 2 (Deepgram) or Tier 3 (metadata).
        """
        _log("Generic adapter has no native subtitle API — skipping Tier 1")
        return None


def _log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}", file=sys.stderr)
