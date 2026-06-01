#!/usr/bin/env python3
"""
Extract video IDs from a YouTube channel/playlist URL using yt-dlp.

Requires: pip install yt-dlp
"""

import json
import sys


def extract_videos(url, count=10):
    """Extract recent videos from a YouTube channel or playlist."""
    try:
        import yt_dlp
    except ImportError:
        print("Error: yt-dlp is not installed.", file=sys.stderr)
        print("pip install yt-dlp", file=sys.stderr)
        sys.exit(1)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": count,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            videos = []

            if "entries" in info:
                for entry in info["entries"][:count]:
                    if entry is None:
                        continue
                    videos.append({
                        "video_id": entry.get("id", ""),
                        "title": entry.get("title", ""),
                        "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    })
            else:
                videos.append({
                    "video_id": info.get("id", ""),
                    "title": info.get("title", ""),
                    "url": info.get("webpage_url", ""),
                })

            return videos
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fetch_videos.py <youtube-url> [count]", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  fetch_videos.py https://www.youtube.com/@username 5", file=sys.stderr)
        print("  fetch_videos.py https://www.youtube.com/playlist?list=xxx", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    videos = extract_videos(url, count)
    print(json.dumps(videos, ensure_ascii=False, indent=2))
