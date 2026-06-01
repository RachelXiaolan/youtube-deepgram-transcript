"""Tier 2: audio download via yt-dlp + Deepgram Nova-3 transcription.

Platform-agnostic. yt-dlp handles 1500+ sites, so this works for YouTube,
Bilibili, Douyin, Twitter/X, etc. without changes.
"""

from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile

# Allow running as script or as module
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.proxy import get_proxy
else:
    from .proxy import get_proxy


def _log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}", file=sys.stderr)


def download_audio(url: str, output_dir: str, video_id_hint: str = "audio") -> str | None:
    """Download best-quality audio from any yt-dlp-supported URL.

    Returns path to the audio file, or None on failure.
    `video_id_hint` is used as a filename prefix; provide a sanitized version
    of the platform's video ID for predictable output paths.
    """
    # Sanitize hint for filesystem
    safe_hint = "".join(c for c in video_id_hint if c.isalnum() or c in "-_") or "audio"
    output_template = os.path.join(output_dir, f"{safe_hint}.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-x",                          # extract audio
        "--audio-format", "mp3",
        "--audio-quality", "0",        # best
        "--no-warnings",
        "--newline",
        "-o", output_template,
    ]

    proxy = get_proxy()
    if proxy:
        cmd.extend(["--proxy", proxy])
        _log(f"Using proxy: {proxy[:30]}...")

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            _log(f"yt-dlp download failed: {result.stderr.strip()}", "WARN")
            return None
        for ext in ("mp3", "m4a", "webm", "opus", "wav"):
            path = os.path.join(output_dir, f"{safe_hint}.{ext}")
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


def transcribe_deepgram(audio_path: str, language: str = "en") -> dict | None:
    """Send audio to Deepgram Nova-3 and return timestamped transcript.

    Supports deepgram-sdk v3 and v7+ (Fern-generated API).

    Returns dict in the standard transcript schema:
        {
            "transcript": [{start, duration, text}, ...],
            "method": "deepgram",
            "language": str,
            "has_timestamps": True,
            "duration_seconds": float,
        }
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

        # SDK v7 returns Pydantic-like; v3 returns dict-like
        if hasattr(response, "model_dump"):
            result = response.model_dump()
        elif hasattr(response, "to_dict"):
            result = response.to_dict()
        else:
            result = json.loads(json.dumps(response))

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
                if not entries and alt.get("transcript"):
                    entries = [{
                        "start": 0,
                        "duration": round(alt.get("duration", 0), 2),
                        "text": alt["transcript"],
                    }]
                break  # only first alternative

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


def fetch_via_deepgram(url: str, language: str = "en", video_id_hint: str = "audio") -> dict | None:
    """Full Tier 2 pipeline: download audio → transcribe → cleanup.

    Args:
        url: watch URL that yt-dlp can consume
        language: language code or "auto"
        video_id_hint: filename prefix (use the platform's video ID)
    """
    with tempfile.TemporaryDirectory(prefix="video-transcript-") as tmpdir:
        _log(f"Tier 2: downloading audio from {url[:60]}...")
        audio_path = download_audio(url, tmpdir, video_id_hint)
        if not audio_path:
            return None
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        _log(f"Audio downloaded: {os.path.basename(audio_path)} ({file_size_mb:.1f} MB)")

        _log("Tier 2: transcribing with Deepgram Nova-3...")
        result = transcribe_deepgram(audio_path, language)
        if result:
            result["video_id"] = video_id_hint
        return result
