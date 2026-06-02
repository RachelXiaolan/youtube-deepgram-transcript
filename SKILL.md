---
name: video-transcript
description: >
  Multi-platform video transcription with 3-tier fallback: native subtitles →
  Deepgram Nova-3 audio transcription → metadata. Supports YouTube natively
  and 1500+ sites (Bilibili, Vimeo, X, Douyin, ...) via yt-dlp. Use when the
  user shares ANY video URL and wants a transcript or summary.
optional_environment_variables:
  - DEEPGRAM_API_KEY
---

# Video Transcript

Transcribe any video — even ones without subtitles — using a 3-tier fallback pipeline. Multi-platform via a pluggable adapter architecture.

## Why This Skill?

Most transcript skills only grab subtitles from one platform. **When a video has no subtitles, or you're on Bilibili / Vimeo / X, they fail.** This skill:

- ✅ Adds Deepgram Nova-3 fallback (cloud API, no GPU, 5-7% WER — better than YouTube auto-captions)
- ✅ Pluggable platform adapters — adding a new platform = one file
- ✅ Generic adapter covers 1500+ sites via yt-dlp out of the box
- ✅ Pre-flight confirmation step shows title/duration/subtitle availability before committing to a (potentially expensive) Deepgram transcription

## Supported Platforms

| Platform | Tier 1 (native subtitles) | Tier 2 (Deepgram) | Tier 3 (metadata) | Notes |
|----------|---------------------------|--------------------|--------------------|-------|
| **YouTube** | ✅ `youtube-transcript-api` | ✅ | ✅ | Full pipeline |
| **Generic** (Bilibili, Vimeo, X, Douyin, ...) | ❌ (no native API) | ✅ | ✅ | Falls back to audio transcription |

To add a new platform with native subtitle support, see `scripts/platforms/__init__.py`.

## The 3-Tier Fallback

```
URL → auto-detect platform → Tier 1 (platform-specific subtitle API)
                              │  ✅ Free, instant
                              │  ❌ Only works if video has subtitles
                              ▼
                            Tier 2: yt-dlp audio → Deepgram Nova-3 (shared)
                              │  ✅ Works on ANY video, no GPU, high accuracy
                              │  ❌ ~$0.0043/min (requires DEEPGRAM_API_KEY)
                              ▼
                            Tier 3: yt-dlp metadata (shared)
                              │  ✅ Always works
                              ❌ Just title + description
```

## Requirements

### Core (Tier 1 + Tier 3 — free, works out of the box)

```bash
pip install youtube-transcript-api yt-dlp
```

Also ensure `ffmpeg` is installed (`brew install ffmpeg` / `apt install ffmpeg`).

### Optional: Tier 2 — Deepgram cloud transcription

```bash
pip install deepgram-sdk
```

Set `DEEPGRAM_API_KEY` in environment. Without it, Tier 2 is skipped automatically — no errors.

> **New users:** Tier 1 (native YouTube subtitles) covers ~60-70% of YouTube videos for free. Only install Deepgram if you need no-subtitle fallback.

## Quick Start

### List supported platforms

```bash
python scripts/fetch_transcript.py platforms
```

### Pre-flight: confirm video info before fetching

```bash
python scripts/fetch_transcript.py info "https://www.youtube.com/watch?v=VIDEO_ID"
```

Output:
```markdown
## 📺 Video Confirmation

**Title:** How to Build AI Agents in 2025
**URL:** https://www.youtube.com/watch?v=VIDEO_ID
**Duration:** 15m 32s
**Platform:** youtube

**Available subtitle languages:** en, zh-Hans
→ Tier 1 (subtitles) will be used
```

### Fetch transcript

```bash
# Auto-detect platform
python scripts/fetch_transcript.py fetch "https://www.youtube.com/watch?v=VIDEO_ID" -l en

# Force platform (skip auto-detection)
python scripts/fetch_transcript.py fetch "https://vimeo.com/76979871" --platform generic

# Backward compat: bare URL/ID is treated as 'fetch'
python scripts/fetch_transcript.py "dQw4w9WgXcQ"
```

### Multi-video from a YouTube channel

```bash
python scripts/fetch_videos.py "https://www.youtube.com/@username" 10
```

Then pass each `video_id` to `fetch_transcript.py fetch`.

## Input Formats

| Platform | Accepted |
|----------|----------|
| YouTube | `watch?v=ID`, `youtu.be/ID`, `shorts/ID`, `embed/ID`, raw 11-char ID |
| Generic | Any `http(s)://...` URL that yt-dlp supports |

## Output Formats

| Flag | Format | Description |
|------|--------|-------------|
| `-f md` (default) | Markdown | Timestamped transcript with metadata header |
| `-f json` | JSON | Raw structured data including platform, tier used, language |
| `-f text` | Plain text | Continuous text, no timestamps |

### Markdown output example

```markdown
> Source: 🎙️ Deepgram Nova-3 Transcription
> Transcript Language: en
> Duration: 8m 32s
> Platform: youtube

[00:00] Welcome to today's video where we'll be looking at ...
[00:11] The first thing you need to understand is ...
```

## Cost

| Tier | Cost | Notes |
|------|------|-------|
| Tier 1 (subtitles) | Free | Works ~60-70% of the time on YouTube |
| Tier 2 (Deepgram) | ~$0.0043/min | 10-min video ≈ $0.04 |
| Tier 3 (metadata) | Free | Title + description only |

**Deepgram free tier**: $200 credit on signup → ~46,000 minutes of transcription.

## Recommended Workflow

### Confirm → Fetch (2-step, recommended for agents)

```bash
# 1) Show video info for user confirmation
python scripts/fetch_transcript.py info "VIDEO_URL"

# 2) After user confirms, fetch
python scripts/fetch_transcript.py fetch "VIDEO_URL" -l zh
```

### Direct fetch (skip confirmation)

```bash
python scripts/fetch_transcript.py "VIDEO_URL"
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPGRAM_API_KEY` | No | Enables Tier 2 (Deepgram transcription). Without it, falls back to Tier 3 (metadata) when no subtitles exist. Get one free at [console.deepgram.com](https://console.deepgram.com) |
| `YOUTUBE_PROXY` | No | Proxy URL for cloud servers (overrides `HTTPS_PROXY`/`ALL_PROXY` for this skill) |
| `HTTPS_PROXY` / `ALL_PROXY` | No | Standard proxy env vars — auto-picked up |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `yt-dlp not found` | `pip install yt-dlp` |
| `deepgram-sdk not found` | `pip install deepgram-sdk` |
| `ffmpeg not found` | `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux) |
| `DEEPGRAM_API_KEY not set` | Tier 2 is skipped. Set the env var or pass it inline: `DEEPGRAM_API_KEY=xxx python scripts/fetch_transcript.py ...` |
| Video download hangs | yt-dlp may be rate-limited. Update: `pip install -U yt-dlp` |
| Wrong language detected | Pass `-l zh` or `-l en` explicitly |
| Generic platform returns metadata only | Set `DEEPGRAM_API_KEY` to enable Tier 2 audio transcription |

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

## Adding a New Platform

1. Create `scripts/platforms/<name>.py` with a class extending `BasePlatform`
2. Implement `extract_video_id`, `get_info`, `fetch_subtitles` (Tier 1)
3. Register in `scripts/platforms/__init__.py:_ADAPTER_SPECS` **before** generic
4. Tier 2 and Tier 3 work automatically via yt-dlp

The platform's `URL_PATTERNS` are tried in registration order; first match wins.

## Comparison with Other Skills

| Feature | This Skill | ZeroPointRepo/youtube-skills | Hermes youtube-content | tapestry-skills |
|---------|-----------|-----|-----|-----|
| Multi-platform | ✅ YouTube + 1500+ via generic | ❌ YouTube only | ❌ YouTube only | ❌ YouTube only |
| Subtitle extraction | ✅ | ✅ | ✅ | ✅ |
| No-subtitle fallback | ✅ Deepgram (cloud, no GPU) | ❌ | ❌ | ✅ Whisper (local GPU) |
| Pre-flight confirmation | ✅ | ❌ | ❌ | ❌ |
| Markdown output | ✅ default | ❌ | ❌ | ❌ |
| Pluggable adapters | ✅ | ❌ | ❌ | ❌ |
| Cost (no-subtitle) | ~$0.04/10min | N/A (fails) | N/A (fails) | Free (needs GPU) |
