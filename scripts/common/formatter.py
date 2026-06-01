"""Output formatters — shared across all platforms."""

from __future__ import annotations


def fmt_ts(seconds: float) -> str:
    """Format seconds as MM:SS (or HH:MM:SS for videos >= 1h)."""
    s = int(seconds)
    if s >= 3600:
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}"
    m = s // 60
    sec = s % 60
    return f"{m:02d}:{sec:02d}"


def format_transcript_md(result: dict, output_language: str = "") -> str:
    """Convert a transcript result dict to clean Markdown.

    Works for any platform — the dict schema is shared:
        {
            video_id, method ("subtitles"|"deepgram"|"metadata"|"failed"),
            language, has_timestamps, transcript: [{start, duration, text}, ...],
            [duration_seconds], [note]
        }
    """
    if not result or not result.get("transcript"):
        return "*No transcript available.*\n"

    lines = []
    method_label = {
        "subtitles": "📝 Subtitles",
        "deepgram": "🎙️ Deepgram Nova-3 Transcription",
        "metadata": "📋 Video Metadata (no subtitles or audio transcription available)",
    }
    method = result.get("method", "unknown")
    lines.append(f"> Source: {method_label.get(method, method)}")
    if result.get("language"):
        lines.append(f"> Transcript Language: {result['language']}")
    if output_language:
        lines.append(f"> Output Language: {output_language}")
    if result.get("duration_seconds"):
        dur = result["duration_seconds"]
        lines.append(f"> Duration: {int(dur) // 60}m {int(dur) % 60}s")
    if result.get("platform"):
        lines.append(f"> Platform: {result['platform']}")
    lines.append("")

    entries = result["transcript"]

    if method == "metadata":
        lines.append(entries[0]["text"])
        return "\n".join(lines)

    if method == "deepgram":
        # Word-level timestamps → group into ~10s chunks for readability
        chunk_text = []
        current_chunk = []
        chunk_start = 0.0
        for entry in entries:
            if not current_chunk:
                chunk_start = entry["start"]
            current_chunk.append(entry["text"])
            chunk_end = entry["start"] + entry["duration"]
            if chunk_end - chunk_start >= 10.0 or entry is entries[-1]:
                ts = fmt_ts(chunk_start)
                text = " ".join(current_chunk)
                chunk_text.append(f"[{ts}] {text}")
                current_chunk = []
                chunk_start = chunk_end
        lines.extend(chunk_text)
    else:
        # Subtitles — already sentence-level
        for entry in entries:
            ts = fmt_ts(entry["start"])
            lines.append(f"[{ts}] {entry['text']}")

    return "\n".join(lines)


def format_video_info_md(info: dict) -> str:
    """Format video info dict (from adapter.get_info) as a confirmation block."""
    lines = [
        "## 📺 Video Confirmation\n",
        f"**Title:** {info.get('title', 'Unknown')}",
        f"**URL:** {info.get('url', '')}",
        f"**Duration:** {info.get('duration_str', 'unknown')}",
    ]
    if info.get("uploader"):
        lines.append(f"**Channel:** {info['uploader']}")
    if info.get("upload_date"):
        d = info["upload_date"]
        if len(d) == 8:
            lines.append(f"**Upload date:** {d[:4]}-{d[4:6]}-{d[6:8]}")
        else:
            lines.append(f"**Upload date:** {d}")
    if info.get("platform"):
        lines.append(f"**Platform:** {info['platform']}")

    lines.append("")
    sub_langs = info.get("available_subtitle_languages", [])
    deepgram_ok = info.get("deepgram_available", False)

    if sub_langs:
        lines.append(f"**Available subtitle languages:** {', '.join(sub_langs)}")
        lines.append("→ Tier 1 (subtitles) will be used")
    elif info.get("supports_subtitles"):
        lines.append("**Subtitles:** Not available for this video")
        if deepgram_ok:
            lines.append("→ Tier 2 (Deepgram audio transcription) will be used (~$0.0043/min)")
        else:
            lines.append("**Deepgram:** Not configured (no DEEPGRAM_API_KEY)")
            lines.append("→ Tier 3 (metadata only) — ⚠️ limited content")
    else:
        lines.append("**Subtitles:** This platform has no native subtitle API")
        if deepgram_ok:
            lines.append("→ Tier 2 (Deepgram audio transcription) will be used (~$0.0043/min)")
        else:
            lines.append("**Deepgram:** Not configured (no DEEPGRAM_API_KEY)")
            lines.append("→ Tier 3 (metadata only) — ⚠️ limited content")

    return "\n".join(lines)
