"""
Platform adapter base class.

Every platform (YouTube, Bilibili, generic, ...) implements this interface.
The main pipeline (Tier 1 → Tier 2 → Tier 3) talks to platforms only through
this interface, so adding a new platform = adding one file under platforms/.

Tier 2 (audio download + Deepgram) and Tier 3 (yt-dlp metadata) are shared
across all platforms — they live in common/ and use yt-dlp, which supports
1500+ sites. Only Tier 1 (native subtitles) needs per-platform code.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional


class BasePlatform(ABC):
    """Abstract base for a video platform adapter.

    Subclasses MUST set:
        name:           short identifier (e.g. "youtube", "bilibili")
        URL_PATTERNS:   list of regex strings; first match wins
        SUPPORTS_SUBTITLES: whether Tier 1 (native subtitles) is implemented

    Subclasses MUST implement:
        extract_video_id(input_str) -> str
        get_info(video_id) -> dict
        fetch_subtitles(video_id, language) -> dict | None

    Tier 2 and Tier 3 are NOT implemented here — they're handled by common/
    because they're yt-dlp-based and platform-agnostic.
    """

    # --- Class-level metadata (override in subclasses) ---
    name: str = ""
    URL_PATTERNS: list[str] = []
    SUPPORTS_SUBTITLES: bool = False
    REQUIRES_AUTH: bool = False  # e.g. Bilibili SESSDATA for some subtitles
    AUTH_ENV_VARS: list[str] = []  # env vars this platform might use

    # --- Abstract methods ---

    @abstractmethod
    def extract_video_id(self, input_str: str) -> str:
        """Parse a URL or raw ID into the platform's canonical video ID."""

    @abstractmethod
    def get_info(self, video_id: str) -> dict:
        """Return metadata dict for the confirmation step.

        Must include at minimum:
            video_id, url, title, duration_seconds, duration_str,
            available_subtitle_languages (list[str], may be empty),
            deepgram_available (bool),
            platform (str = self.name)
        """

    @abstractmethod
    def fetch_subtitles(self, video_id: str, language: str = "en") -> Optional[dict]:
        """Tier 1: fetch native subtitles. Return None if unavailable.

        Return format must match the common transcript schema:
            {
                "video_id": str,
                "transcript": [{"start": float, "duration": float, "text": str}, ...],
                "method": "subtitles",
                "language": str,
                "has_timestamps": bool,
            }
        """

    # --- Optional hooks (subclasses may override) ---

    def get_stream_url(self, video_id: str) -> str:
        """Return the watch URL that yt-dlp will consume (for Tier 2/3).

        Default: subclasses are responsible for setting it via get_info.
        Override only if you need a non-obvious URL format.
        """
        raise NotImplementedError

    def auth_status(self) -> dict:
        """Check whether required env vars for auth are set.

        Returns dict like {"authenticated": bool, "missing": [env_var, ...]}.
        Default: REQUIRES_AUTH=False → always authenticated.
        """
        if not self.REQUIRES_AUTH:
            return {"authenticated": True, "missing": []}
        missing = [v for v in self.AUTH_ENV_VARS if not __import__("os").environ.get(v)]
        return {"authenticated": not missing, "missing": missing}
