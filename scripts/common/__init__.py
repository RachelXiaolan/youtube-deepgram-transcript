"""Shared utilities used by every platform adapter and the main pipeline."""

from .proxy import get_proxy
from .deepgram import transcribe_deepgram, fetch_via_deepgram
from .metadata import fetch_metadata, fetch_video_info_via_ytdlp
from .formatter import format_transcript_md, fmt_ts

__all__ = [
    "get_proxy",
    "transcribe_deepgram",
    "fetch_via_deepgram",
    "fetch_metadata",
    "fetch_video_info_via_ytdlp",
    "format_transcript_md",
    "fmt_ts",
]
