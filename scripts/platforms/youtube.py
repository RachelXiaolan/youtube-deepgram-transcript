"""YouTube platform adapter.

Uses youtube-transcript-api for Tier 1 (subtitles) and shares Tier 2/3
with all other platforms via common/ (yt-dlp + Deepgram, yt-dlp metadata).
"""

from __future__ import annotations
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
from common.proxy import apply_to_env  # noqa: E402
from common.metadata import fetch_video_info_via_ytdlp  # noqa: E402


def _log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}", file=sys.stderr)


class YouTubeAdapter(BasePlatform):
    name = "youtube"
    URL_PATTERNS = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
        r"(?:https?://)?(?:www\.)?youtu\.be/([A-Za-z0-9_-]{11})",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{11})",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]{11})",
        r"(?:https?://)?(?:www\.)?youtube\.com/v/([A-Za-z0-9_-]{11})",
    ]
    SUPPORTS_SUBTITLES = True
    REQUIRES_AUTH = False

    def extract_video_id(self, input_str: str) -> str:
        # Try URL patterns first
        for pat in self.URL_PATTERNS:
            m = re.search(pat, input_str)
            if m:
                return m.group(1)
        # Raw 11-char ID
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", input_str):
            return input_str
        raise ValueError(f"Cannot extract YouTube video ID from: {input_str}")

    def get_stream_url(self, video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"

    def get_info(self, video_id: str) -> dict:
        url = self.get_stream_url(video_id)
        info = {
            "video_id": video_id,
            "url": url,
            "platform": self.name,
            "supports_subtitles": self.SUPPORTS_SUBTITLES,
            "available_subtitle_languages": [],
            "deepgram_available": bool(os.environ.get("DEEPGRAM_API_KEY", "")),
        }

        # Enrich via yt-dlp (title, duration, channel)
        yt_info = fetch_video_info_via_ytdlp(url)
        if yt_info:
            info.update(yt_info)
        else:
            info.setdefault("title", "Unknown")
            info.setdefault("duration_seconds", 0)
            info.setdefault("duration_str", "unknown")

        # Probe available subtitle languages
        info["available_subtitle_languages"] = self._list_subtitle_languages(video_id)
        return info

    def _list_subtitle_languages(self, video_id: str) -> list[str]:
        """Return list of language codes available for this video, or [] on failure."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            _log("youtube-transcript-api not installed", "WARN")
            return []

        apply_to_env()  # propagate proxy to env vars
        api = YouTubeTranscriptApi()
        try:
            langs = []
            for t in api.list(video_id):
                langs.append(t.language_code)
            return langs
        except Exception:
            return []

    def fetch_subtitles(self, video_id: str, language: str = "en") -> Optional[dict]:
        """Tier 1: fetch subtitles via youtube-transcript-api.

        Tries languages in priority: requested → Chinese variants → English → first available.
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            _log("youtube-transcript-api not installed, skipping Tier 1", "WARN")
            return None

        apply_to_env()
        api = YouTubeTranscriptApi()
        try:
            available = api.list(video_id)
        except Exception as e:
            _log(f"Tier 1: transcript listing failed: {e}", "WARN")
            return None

        # Priority order
        lang_priority = [
            language,
            "zh-TW", "zh-CN", "zh-Hant", "zh-Hans", "zh",
            "en",
        ]
        seen = set()
        unique_langs = [l for l in lang_priority if not (l in seen or seen.add(l))]

        for lang_code in unique_langs:
            try:
                transcript = api.fetch(video_id, languages=[lang_code])
                return self._transcript_to_dict(video_id, transcript, lang_code)
            except Exception:
                continue

        # Fallback: first available language
        try:
            for t_info in available:
                transcript = api.fetch(video_id, languages=[t_info.language_code])
                return self._transcript_to_dict(video_id, transcript, t_info.language_code)
        except Exception:
            pass

        _log("Tier 1: no subtitles found for any language", "INFO")
        return None

    @staticmethod
    def _transcript_to_dict(video_id: str, transcript, lang_code: str) -> dict:
        entries = []
        for entry in transcript:
            entries.append({
                "start": round(entry.start, 2),
                "duration": round(entry.duration, 2),
                "text": entry.text,
            })
        return {
            "video_id": video_id,
            "transcript": entries,
            "method": "subtitles",
            "language": lang_code,
            "has_timestamps": True,
            "platform": "youtube",
        }
