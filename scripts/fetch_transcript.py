#!/usr/bin/env python3
"""
Fetch transcript for a YouTube video with three-tier fallback:

  Tier 1: youtube-transcript-api (subtitles, free, instant)
  Tier 2: yt-dlp audio download → Deepgram Nova-3 transcription ($0.0043/min)
  Tier 3: yt-dlp metadata (title + description, last resort)

Requires:
  pip install youtube-transcript-api yt-dlp deepgram-sdk

Environment:
  DEEPGRAM_API_KEY  (optional — enables Tier 2; without it, skips to Tier 3)
"""

import json
import os
import re
import sys
import subprocess
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(msg: str, level: str = "INFO"):
    """Structured logging to stderr so stdout stays clean JSON."""
    print(f"[{level}] {msg}", file=sys.stderr)


def _extract_video_id(input_str: str) -> str:
    """Parse a video ID from various YouTube URL formats or a raw 11-char ID."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:embed/)([A-Za-z0-9_-]{11})",
        r"(?:shorts/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pat in patterns:
        m = re.search(pat, input_str)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract video ID from: {input_str}")


# ---------------------------------------------------------------------------
# Tier 1: youtube-transcript-api
# ---------------------------------------------------------------------------

def _fetch_subtitles(video_id: str, language: str = "en"):
    """Try to fetch subtitles via youtube-transcript-api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
    except ImportError:
        _log("youtube-transcript-api not installed, skipping Tier 1", "WARN")
        return None

    api = YouTubeTranscriptApi()
    try:
        available = api.list(video_id)
    except Exception as e:
        _log(f"Tier 1: transcript listing failed: {e}", "WARN")
        return None

    # Priority: requested lang → Chinese variants → English → first available
    lang_priority = [
        language,
        "zh-TW", "zh-CN", "zh-Hant", "zh-Hans", "zh",
        "en",
    ]
    # Deduplicate while preserving order
    seen = set()
    unique_langs = []
    for l in lang_priority:
        if l not in seen:
            seen.add(l)
            unique_langs.append(l)

    for lang_code in unique_langs:
        try:
            transcript = api.fetch(video_id, languages=[lang_code])
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
            }
        except Exception:
            continue

    # Try first available transcript regardless of language
    try:
        for t_info in available:
            transcript = api.fetch(video_id, languages=[t_info.language_code])
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
                "language": t_info.language_code,
                "has_timestamps": True,
            }
    except Exception:
        pass

    _log("Tier 1: no subtitles found for any language", "INFO")
    return None


# ---------------------------------------------------------------------------
# Tier 2: yt-dlp audio download + Deepgram Nova-3
# ---------------------------------------------------------------------------

def _download_audio(video_id: str, output_dir: str) -> str | None:
    """Download best-quality audio from YouTube, return path to file or None."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = os.path.join(output_dir, f"{video_id}.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-x",                          # extract audio
        "--audio-format", "mp3",
        "--audio-quality", "0",        # best
        "--no-warnings",
        "--newline",
        "-o", output_template,
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            _log(f"yt-dlp download failed: {result.stderr.strip()}", "WARN")
            return None
        # Find the downloaded file
        for ext in ("mp3", "m4a", "webm", "opus", "wav"):
            path = os.path.join(output_dir, f"{video_id}.{ext}")
            if os.path.exists(path):
                return path
        _log("yt-dlp finished but output file not found", "WARN")
        return None
    except subprocess.TimeoutExpired:
        _log("yt-dlp download timed out (5min)", "WARN")
        return None
    except Exception as e:
        _log(f"yt-dlp error: {e}", "WARN")
        return None


def _transcribe_deepgram(audio_path: str, language: str = "en") -> dict | None:
    """Send audio to Deepgram Nova-3 and return timestamped transcript.

    Supports deepgram-sdk >= 3.0 (including v7.x Fern-generated API):
      client = DeepgramClient(api_key=...)
      client.listen.v1.media.transcribe_file(request=bytes, model="nova-3", ...)
    """
    api_key = os.environ.get("DEEPGRAM_API_KEY", "")
    if not api_key:
        _log("DEEPGRAM_API_KEY not set, skipping Tier 2", "WARN")
        return None

    try:
        from deepgram import DeepgramClient
    except ImportError:
        _log("deepgram-sdk not installed, skipping Tier 2", "WARN")
        return None

    try:
        client = DeepgramClient(api_key=api_key)

        with open(audio_path, "rb") as f:
            audio_data = f.read()

        # Build kwargs — only pass language when not auto-detecting
        detect_lang = language in ("auto", "unknown", "")
        kwargs = dict(
            request=audio_data,
            model="nova-3",
            smart_format=True,
            punctuate=True,
            paragraphs=True,
            detect_language=detect_lang or None,
        )
        if not detect_lang:
            kwargs["language"] = language

        _log(f"Sending to Deepgram Nova-3 (lang={language if not detect_lang else 'auto-detect'})...")
        response = client.listen.v1.media.transcribe_file(**kwargs)

        # Convert response to dict — SDK v7 returns Pydantic-like objects
        if hasattr(response, "model_dump"):
            result = response.model_dump()
        elif hasattr(response, "to_dict"):
            result = response.to_dict()
        else:
            result = json.loads(json.dumps(response))

        # Parse words into our standard format
        entries = []
        channels = result.get("results", {}).get("channels", [])
        for channel in channels:
            for alt in channel.get("alternatives", []):
                for word in alt.get("words", []):
                    entries.append({
                        "start": round(word.get("start", 0), 2),
                        "duration": round(word.get("end", 0) - word.get("start", 0), 2),
                        "text": word.get("word", word.get("punctuated_word", "")),
                    })
                # If no words, fall back to full transcript
                if not entries and alt.get("transcript"):
                    entries = [{
                        "start": 0,
                        "duration": round(alt.get("duration", 0), 2),
                        "text": alt["transcript"],
                    }]
                break  # Only use first alternative

        if not entries:
            _log("Deepgram returned empty transcript", "WARN")
            return None

        detected_lang = channels[0].get("detected_language", language) if channels else language

        return {
            "transcript": entries,
            "method": "deepgram",
            "language": detected_lang or language,
            "has_timestamps": True,
            "duration_seconds": round(entries[-1]["start"] + entries[-1]["duration"], 2) if entries else 0,
        }
    except Exception as e:
        _log(f"Deepgram transcription failed: {e}", "WARN")
        return None


def _fetch_via_deepgram(video_id: str, language: str = "en"):
    """Full Tier 2 pipeline: download audio → transcribe → cleanup."""
    with tempfile.TemporaryDirectory(prefix="yt-transcript-") as tmpdir:
        _log(f"Tier 2: downloading audio for {video_id}...")
        audio_path = _download_audio(video_id, tmpdir)
        if not audio_path:
            return None

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        _log(f"Audio downloaded: {os.path.basename(audio_path)} ({file_size_mb:.1f} MB)")

        _log("Tier 2: transcribing with Deepgram Nova-3...")
        result = _transcribe_deepgram(audio_path, language)
        if result:
            result["video_id"] = video_id
        # tmpdir auto-cleans
        return result


# ---------------------------------------------------------------------------
# Tier 3: yt-dlp metadata fallback
# ---------------------------------------------------------------------------

def _fetch_metadata(video_id: str):
    """Last resort: get title + description via yt-dlp."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json", "--no-warnings", url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        duration = data.get("duration", 0)
        pseudo = (
            f"Title: {data.get('title', '')}\n\n"
            f"Description:\n{data.get('description', '')}\n\n"
            f"Duration: {duration // 60}m {duration % 60}s\n"
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


# ---------------------------------------------------------------------------
# Markdown output formatter
# ---------------------------------------------------------------------------

def _format_transcript_md(result: dict) -> str:
    """Convert transcript result to clean Markdown."""
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
        lines.append(f"> Language: {result['language']}")
    if result.get("duration_seconds"):
        dur = result["duration_seconds"]
        lines.append(f"> Duration: {int(dur) // 60}m {int(dur) % 60}s")
    lines.append("")

    entries = result["transcript"]

    if method == "metadata":
        # Just dump the text as-is
        lines.append(entries[0]["text"])
        return "\n".join(lines)

    if method == "deepgram":
        # Deepgram gives word-level timestamps; group into ~10s chunks
        # for readability
        chunk_text = []
        current_chunk = []
        chunk_start = 0.0
        for entry in entries:
            if not current_chunk:
                chunk_start = entry["start"]
            current_chunk.append(entry["text"])
            chunk_end = entry["start"] + entry["duration"]
            if chunk_end - chunk_start >= 10.0 or entry is entries[-1]:
                ts = _fmt_ts(chunk_start)
                text = " ".join(current_chunk)
                chunk_text.append(f"[{ts}] {text}")
                current_chunk = []
                chunk_start = chunk_end
        lines.extend(chunk_text)
    else:
        # Subtitles — already sentence-level, just format
        for entry in entries:
            ts = _fmt_ts(entry["start"])
            lines.append(f"[{ts}] {entry['text']}")

    return "\n".join(lines)


def _fmt_ts(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def fetch_transcript(video_input: str, language: str = "en", output_format: str = "md"):
    """
    Three-tier fallback transcript fetcher.

    Args:
        video_input: YouTube URL or 11-char video ID.
        language: Language code (default: "en"). Use "auto" for auto-detect.
        output_format: "md" (markdown, default), "json" (raw JSON), "text" (plain text).

    Returns:
        str: Formatted transcript.
    """
    video_id = _extract_video_id(video_input)

    # --- Tier 1: Subtitles ---
    _log(f"Tier 1: fetching subtitles for {video_id}...")
    result = _fetch_subtitles(video_id, language)
    if result:
        _log(f"✅ Tier 1 success (subtitles, lang={result['language']})")
    else:
        # --- Tier 2: Deepgram ---
        _log("Tier 1 failed, trying Tier 2: Deepgram audio transcription...")
        result = _fetch_via_deepgram(video_id, language)
        if result:
            dur = result.get("duration_seconds", 0)
            _log(f"✅ Tier 2 success (Deepgram, {int(dur)//60}m{int(dur)%60}s)")
        else:
            # --- Tier 3: Metadata ---
            _log("Tier 2 failed/skipped, trying Tier 3: metadata fallback...")
            result = _fetch_metadata(video_id)
            if result:
                _log("⚠️ Tier 3: using metadata only (title + description)")
            else:
                _log("❌ All tiers failed", "ERROR")
                result = {
                    "video_id": video_id,
                    "transcript": None,
                    "method": "failed",
                    "error": "All three tiers failed: no subtitles, no Deepgram, no metadata",
                }

    # --- Output formatting ---
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "text":
        if result.get("transcript"):
            return " ".join(e["text"] for e in result["transcript"])
        return ""
    else:  # md (default)
        return _format_transcript_md(result)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch YouTube transcript with 3-tier fallback (subtitles → Deepgram → metadata)"
    )
    parser.add_argument("video", help="YouTube URL or video ID")
    parser.add_argument("-l", "--language", default="en", help="Language code (default: en, use 'auto' for auto-detect)")
    parser.add_argument(
        "-f", "--format",
        choices=["md", "json", "text"],
        default="md",
        help="Output format (default: md)",
    )
    args = parser.parse_args()

    output = fetch_transcript(args.video, args.language, args.format)
    print(output)
