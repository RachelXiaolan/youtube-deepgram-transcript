"""Tier 3: yt-dlp metadata fallback + generic video info fetcher.

Platform-agnostic. Used both as Tier 3 (last-resort metadata) and as a
"give me basic info about any URL" helper for platform adapters that don't
have a native API for metadata (e.g. generic adapter).
"""

from __future__ import annotations
import json
import os
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.proxy import get_proxy
else:
    from .proxy import get_proxy


def _log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}", file=sys.stderr)


def fetch_video_info_via_ytdlp(url: str) -> dict | None:
    """Get metadata for any yt-dlp-supported URL.

    Returns dict with: title, duration_seconds, uploader, upload_date, url.
    Returns None on failure.
    """
    cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--no-warnings", url]
    proxy = get_proxy()
    if proxy:
        cmd.extend(["--proxy", proxy])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        dur = data.get("duration", 0) or 0
        return {
            "title": data.get("title", "Unknown"),
            "duration_seconds": dur,
            "duration_str": f"{int(dur) // 60}m {int(dur) % 60}s" if dur else "unknown",
            "uploader": data.get("uploader", ""),
            "upload_date": data.get("upload_date", ""),
            "url": url,
        }
    except Exception as e:
        _log(f"yt-dlp metadata fetch failed: {e}", "WARN")
        return None


def fetch_metadata(url: str, video_id: str) -> dict | None:
    """Tier 3: build a pseudo-transcript from title + description.

    Used when both Tier 1 (subtitles) and Tier 2 (Deepgram) fail / skip.
    """
    cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--no-warnings", url]
    proxy = get_proxy()
    if proxy:
        cmd.extend(["--proxy", proxy])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        duration = data.get("duration", 0) or 0
        pseudo = (
            f"Title: {data.get('title', '')}\n\n"
            f"Description:\n{data.get('description', '')}\n\n"
            f"Duration: {int(duration) // 60}m {int(duration) % 60}s\n"
            f"Uploader: {data.get('uploader', '')}\n"
            f"Upload date: {data.get('upload_date', '')}"
        )
        return {
            "video_id": video_id,
            "transcript": [{
                "start": 0,
                "duration": float(duration),
                "text": pseudo,
            }],
            "method": "metadata",
            "language": "unknown",
            "has_timestamps": False,
            "note": "No subtitles available and Deepgram skipped/failed. Using title + description.",
        }
    except Exception as e:
        _log(f"Tier 3 metadata fetch failed: {e}", "WARN")
        return None
