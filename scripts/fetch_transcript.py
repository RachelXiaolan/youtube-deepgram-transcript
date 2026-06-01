#!/usr/bin/env python3
"""
Fetch transcript for any video URL with a 3-tier fallback pipeline.

Supported platforms (auto-detected from URL):
  - YouTube    (full 3-tier: subtitles → Deepgram → metadata)
  - Generic    (Tier 2/3 only via yt-dlp: Bilibili, Douyin, X, Vimeo, ...)

Add a new platform: drop a new file under scripts/platforms/ and register
it in scripts/platforms/__init__.py.

Usage:
    # Pre-flight: show video info for user confirmation
    python fetch_transcript.py info "https://www.youtube.com/watch?v=VIDEO_ID"

    # Fetch transcript (auto-detects platform)
    python fetch_transcript.py fetch "https://www.youtube.com/watch?v=VIDEO_ID" -l en

    # Explicit platform (skip auto-detection)
    python fetch_transcript.py fetch "https://example.com/video" --platform generic

    # Backward compat: bare URL/ID is treated as 'fetch'
    python fetch_transcript.py "VIDEO_ID"
    python fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" -l zh

    # List supported platforms
    python fetch_transcript.py platforms

Environment:
    DEEPGRAM_API_KEY  (optional — enables Tier 2; without it, falls back to Tier 3)
    YOUTUBE_PROXY / HTTPS_PROXY / ALL_PROXY  (optional — proxy for cloud servers)
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path

# Add scripts/ to sys.path so we can import common/ and platforms/ as packages
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from platforms import match_adapter, list_adapters, get_adapter
from common.deepgram import fetch_via_deepgram
from common.metadata import fetch_metadata
from common.formatter import format_transcript_md, format_video_info_md


def _log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def get_video_info(video_input: str, platform: str | None = None) -> dict:
    """Pre-flight: detect platform and return video metadata for confirmation."""
    adapter = match_adapter(video_input, force_platform=platform)

    if adapter.name == "generic":
        # Generic adapter expects the URL itself (no extractable video ID)
        info = adapter.get_info(video_input)
    else:
        video_id = adapter.extract_video_id(video_input)
        info = adapter.get_info(video_id)

    info.setdefault("platform", adapter.name)
    return info


def fetch_transcript(
    video_input: str,
    language: str = "en",
    output_format: str = "md",
    platform: str | None = None,
) -> str:
    """Three-tier fallback transcript fetcher (auto-detects platform).

    Args:
        video_input: URL or video ID
        language: language code or "auto"
        output_format: "md" | "json" | "text"
        platform: force a specific platform (skip auto-detection)

    Returns: formatted transcript string
    """
    adapter = match_adapter(video_input, force_platform=platform)

    # --- Resolve video_id and watch URL for downstream tiers ---
    if adapter.name == "generic":
        url = video_input if video_input.startswith("http") else f"https://{video_input}"
        video_id = adapter.extract_video_id(url)
    else:
        video_id = adapter.extract_video_id(video_input)
        url = adapter.get_stream_url(video_id)

    _log(f"Platform: {adapter.name} | video_id={video_id} | url={url[:80]}")

    # --- Tier 1: native subtitles (if platform supports it) ---
    result = None
    if adapter.SUPPORTS_SUBTITLES:
        _log(f"Tier 1: fetching subtitles via {adapter.name}...")
        result = adapter.fetch_subtitles(video_id, language)
        if result:
            _log(f"✅ Tier 1 success ({adapter.name} subtitles, lang={result['language']})")

    # --- Tier 2: Deepgram audio transcription (shared, platform-agnostic) ---
    if not result:
        _log("Tier 1 unavailable/failed, trying Tier 2: Deepgram...")
        result = fetch_via_deepgram(url, language, video_id_hint=video_id)
        if result:
            dur = result.get("duration_seconds", 0)
            _log(f"✅ Tier 2 success (Deepgram, {int(dur)//60}m{int(dur)%60}s)")

    # --- Tier 3: metadata fallback (shared) ---
    if not result:
        _log("Tier 2 unavailable/failed, trying Tier 3: metadata...")
        result = fetch_metadata(url, video_id)
        if result:
            _log("⚠️ Tier 3: using metadata only")

    if not result:
        _log("❌ All tiers failed", "ERROR")
        result = {
            "video_id": video_id,
            "transcript": None,
            "method": "failed",
            "error": "All three tiers failed",
            "platform": adapter.name,
        }

    # Tag result with platform
    result.setdefault("platform", adapter.name)

    # --- Output formatting ---
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "text":
        if result.get("transcript"):
            return " ".join(e["text"] for e in result["transcript"])
        return ""
    else:  # md (default)
        return format_transcript_md(result)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_platforms():
    """Print available platforms."""
    print("\nSupported platforms:\n")
    for adapter in list_adapters():
        auth = " (auth required)" if adapter.REQUIRES_AUTH else ""
        sub = "Tier 1 ✅" if adapter.SUPPORTS_SUBTITLES else "Tier 2/3 only"
        print(f"  {adapter.name:<12}  {sub}{auth}")
        if adapter.URL_PATTERNS and adapter.name != "generic":
            print(f"               patterns: {len(adapter.URL_PATTERNS)}")
    print("\nGeneric adapter covers 1500+ sites via yt-dlp (Bilibili, Douyin, X, Vimeo, ...)")
    print("Add a dedicated adapter: see scripts/platforms/__init__.py\n")


def main():
    import argparse

    # Pre-parse for backward compat: bare URL/ID → treat as "fetch <URL>"
    argv = sys.argv[1:]
    if argv and argv[0] not in ("info", "fetch", "platforms", "-h", "--help"):
        argv = ["fetch"] + argv

    parser = argparse.ArgumentParser(
        description="Fetch video transcript with 3-tier fallback (subtitles → Deepgram → metadata)"
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # --- info ---
    info_p = sub.add_parser("info", help="Show video info for confirmation before fetching")
    info_p.add_argument("video", help="Video URL or ID")
    info_p.add_argument("-p", "--platform", default=None, help="Force platform (skip auto-detect)")

    # --- fetch ---
    fetch_p = sub.add_parser("fetch", help="Fetch transcript")
    fetch_p.add_argument("video", help="Video URL or ID")
    fetch_p.add_argument("-l", "--language", default="en",
                         help="Language code (default: en, use 'auto' for auto-detect)")
    fetch_p.add_argument("-f", "--format", choices=["md", "json", "text"], default="md",
                         help="Output format (default: md)")
    fetch_p.add_argument("-p", "--platform", default=None, help="Force platform (skip auto-detect)")
    fetch_p.add_argument("--api-key", default=None, dest="api_key",
                         help="Deepgram API key (overrides DEEPGRAM_API_KEY env var). "
                              "Use this if you don't want to set the env var permanently.")

    # --- platforms ---
    sub.add_parser("platforms", help="List supported platforms")

    args = parser.parse_args(argv)

    if args.command == "platforms":
        _cmd_platforms()
        return

    if args.command == "info":
        info = get_video_info(args.video, platform=args.platform)
        print(format_video_info_md(info))
        return

    # fetch (or default)
    # Honor --api-key if given (overrides env var for this run)
    if getattr(args, "api_key", None):
        os.environ["DEEPGRAM_API_KEY"] = args.api_key

    output = fetch_transcript(
        args.video,
        language=args.language,
        output_format=args.format,
        platform=args.platform,
    )
    print(output)


if __name__ == "__main__":
    main()
