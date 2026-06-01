---
name: youtube-deepgram-transcript
description: >
  YouTube video transcription with 3-tier fallback: subtitles → Deepgram Nova-3 audio
  transcription → metadata. Solves the "video has no subtitles" problem. Outputs clean
  Markdown by default. Use when the user shares a YouTube URL, asks to transcribe or
  summarize a video, or needs a transcript from any YouTube video.
required_environment_variables:
  - DEEPGRAM_API_KEY
---

# YouTube Deepgram Transcript

Transcribe any YouTube video — even ones without subtitles — using a 3-tier fallback pipeline.

## Why This Skill?

Most YouTube transcript skills only grab subtitles. **When a video has no subtitles, they fail.** This skill adds Deepgram Nova-3 as a fallback: it downloads the audio and transcribes it via cloud API (no GPU required), achieving 5-7% WER — better than YouTube's own auto-captions.

## The 3-Tier Fallback

```
Tier 1: youtube-transcript-api (subtitles)
  │  ✅ Free, instant
  │  ❌ Only works if the video has subtitles enabled
  ▼
Tier 2: yt-dlp audio download → Deepgram Nova-3
  │  ✅ Works on ANY video, no GPU needed, high accuracy
  │  ❌ Requires DEEPGRAM_API_KEY (~$0.0043/min)
  ▼
Tier 3: yt-dlp metadata (title + description)
  │  ✅ Always works (unless video is private)
  ❌ Not a real transcript, just metadata
```

## Requirements

```bash
pip install youtube-transcript-api yt-dlp deepgram-sdk
```

Also ensure:
- `ffmpeg` is installed (`brew install ffmpeg` / `apt install ffmpeg`)
- `DEEPGRAM_API_KEY` is set in environment (optional — enables Tier 2)

## Quick Start

### Single video — get transcript as Markdown (default)

```bash
python scripts/fetch_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Single video — specify language

```bash
python scripts/fetch_transcript.py dQw4w9WgXcQ -l zh
```

### Single video — auto-detect language

```bash
python scripts/fetch_transcript.py "https://youtu.be/dQw4w9WgXcQ" -l auto
```

### Single video — raw JSON output

```bash
python scripts/fetch_transcript.py dQw4w9WgXcQ -f json
```

### Channel / Playlist — list videos

```bash
python scripts/fetch_videos.py "https://www.youtube.com/@username" 10
```

Then pass each `video_id` to `fetch_transcript.py`.

## Input Formats

All of these work:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- Raw 11-character video ID: `dQw4w9WgXcQ`

## Output Formats

| Flag | Format | Description |
|------|--------|-------------|
| `-f md` (default) | Markdown | Timestamped transcript with metadata header |
| `-f json` | JSON | Raw structured data with all tiers info |
| `-f text` | Plain text | Continuous text, no timestamps |

### Markdown output example

```markdown
> Source: 🎙️ Deepgram Nova-3 Transcription
> Language: en
> Duration: 8m 32s

[00:00] Welcome to today's video where we'll be looking at ...
[00:11] The first thing you need to understand is ...
```

## Cost

| Tier | Cost | Notes |
|------|------|-------|
| Tier 1 (subtitles) | Free | Works ~60-70% of the time |
| Tier 2 (Deepgram) | ~$0.0043/min | 10-min video ≈ $0.04 |
| Tier 3 (metadata) | Free | Title + description only |

**Deepgram free tier**: $200 credit on signup → ~46,000 minutes of transcription.

## Workflow for Summarization

1. Run `scripts/fetch_transcript.py <url>` to get the transcript in Markdown
2. Use the transcript as input for AI summarization
3. Optional: use the prompt template in `templates/summary-prompt.md`

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPGRAM_API_KEY` | No | Enables Tier 2 (Deepgram transcription). Without it, falls back to Tier 3 (metadata) when no subtitles exist. Get one free at [console.deepgram.com](https://console.deepgram.com) |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `yt-dlp not found` | `pip install yt-dlp` |
| `deepgram-sdk not found` | `pip install deepgram-sdk` |
| `ffmpeg not found` | `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux) |
| `DEEPGRAM_API_KEY not set` | Tier 2 is skipped. Set the env var or pass it inline: `DEEPGRAM_API_KEY=xxx python scripts/fetch_transcript.py ...` |
| Video download hangs | yt-dlp may be rate-limited. Update: `pip install -U yt-dlp` |
| Wrong language detected | Pass `-l zh` or `-l en` explicitly |

## ⚠️ Cloud Server Users (AWS / GCP / Azure)

YouTube blocks requests from cloud IPs. If you're running on a server, you need a proxy.

**Quickest fix — Cloudflare WARP (free, one command):**

```bash
# Start WARP proxy
docker run -d --name warproxy --cap-add NET_ADMIN \
  --sysctl net.ipv6.conf.all.disable_ipv6=0 \
  -p 1080:1080 kingcc/warproxy

# Use it
YOUTUBE_PROXY=socks5://127.0.0.1:1080 python3 scripts/fetch_transcript.py "VIDEO_URL"
```

The script auto-detects proxy from `YOUTUBE_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY` env vars.

See [`references/cloud-server-guide.md`](references/cloud-server-guide.md) for all options (WARP, PO Token, residential proxies, Tor).

## Comparison with Other Skills

| Feature | This Skill | ZeroPointRepo/youtube-skills | Hermes youtube-content | tapestry-skills |
|---------|-----------|-----|-----|-----|
| Subtitle extraction | ✅ | ✅ | ✅ | ✅ |
| No-subtitle fallback | ✅ Deepgram (cloud) | ❌ | ❌ | ✅ Whisper (local GPU) |
| No GPU required | ✅ | ✅ | ✅ | ❌ |
| Timestamps | ✅ | ✅ | ✅ | Varies |
| Markdown output | ✅ default | ❌ | ❌ | ❌ |
| Cost (no-subtitle) | ~$0.04/10min | N/A (fails) | N/A (fails) | Free (needs GPU) |
