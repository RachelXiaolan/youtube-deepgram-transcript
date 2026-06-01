# video-transcript

Multi-platform video transcription with **3-tier fallback** — works on YouTube, Vimeo, Bilibili, X, Douyin, and 1500+ other sites, even when videos have no subtitles.

## Why?

Most transcript skills only grab YouTube subtitles. **When a video has no subtitles, or you're on Bilibili / Vimeo / X, they fail.** This skill:

- ✅ Pluggable platform adapters (add a new platform = one file)
- ✅ [Deepgram Nova-3](https://deepgram.com) cloud transcription fallback — no GPU required, ~5-7% WER
- ✅ Generic adapter covers 1500+ sites via [yt-dlp](https://github.com/yt-dlp/yt-dlp) out of the box
- ✅ Pre-flight confirmation step shows title/duration before committing to a paid transcription

## The 3-Tier Fallback

```
URL → auto-detect platform → Tier 1 (platform-specific subtitle API)
                              ✅ Free, instant (YouTube only)
                              │
                            Tier 2: yt-dlp audio → Deepgram Nova-3 (shared)
                              ✅ Works on ANY video, no GPU, high accuracy
                              ❌ ~$0.0043/min (requires DEEPGRAM_API_KEY)
                              │
                            Tier 3: yt-dlp metadata (shared)
                              ✅ Always works (unless video is private)
                              ❌ Just title + description
```

## Supported Platforms

| Platform | Tier 1 (native subtitles) | Tier 2 (Deepgram) | Tier 3 (metadata) |
|----------|:---:|:---:|:---:|
| **YouTube** | ✅ | ✅ | ✅ |
| **Generic** (Bilibili, Vimeo, X, Douyin, Twitch, ...) | — | ✅ | ✅ |

To add a new platform with native subtitle support: see [`scripts/platforms/__init__.py`](scripts/platforms/__init__.py).

## Quick Start

### Install dependencies

```bash
pip install youtube-transcript-api yt-dlp deepgram-sdk
```

Make sure `ffmpeg` is also installed (`brew install ffmpeg` / `apt install ffmpeg`).

### Set your Deepgram API key (optional — enables Tier 2)

```bash
export DEEPGRAM_API_KEY="your-key-here"
```

Get a free key with $200 credit at [console.deepgram.com](https://console.deepgram.com).

### Run

```bash
# List supported platforms
python3 scripts/fetch_transcript.py platforms

# Pre-flight: show video info for confirmation (recommended)
python3 scripts/fetch_transcript.py info "https://www.youtube.com/watch?v=VIDEO_ID"

# Fetch transcript (auto-detects platform)
python3 scripts/fetch_transcript.py fetch "https://www.youtube.com/watch?v=VIDEO_ID" -l en

# Works on any yt-dlp-supported site (Bilibili, Vimeo, X, ...)
python3 scripts/fetch_transcript.py fetch "https://vimeo.com/76979871"

# Force a specific platform
python3 scripts/fetch_transcript.py fetch "https://vimeo.com/76979871" --platform generic

# Backward compat: bare URL is treated as 'fetch'
python3 scripts/fetch_transcript.py "VIDEO_URL"

# Other flags
python3 scripts/fetch_transcript.py fetch VIDEO_ID -l zh        # Chinese
python3 scripts/fetch_transcript.py fetch VIDEO_ID -l auto      # auto-detect
python3 scripts/fetch_transcript.py fetch VIDEO_ID -f json      # raw JSON
python3 scripts/fetch_transcript.py fetch VIDEO_ID -f text      # no timestamps

# List videos from a YouTube channel
python3 scripts/fetch_videos.py "https://www.youtube.com/@username" 10
```

### Output example (Markdown)

```markdown
> Source: 🎙️ Deepgram Nova-3 Transcription
> Transcript Language: en
> Duration: 0m 49s
> Platform: generic

[00:05] here at vimeo there's always one thing on our minds how to make your videos look amazing...
[00:15] to make the best thing about vimeo even better so we put our best developers and designers...
```

## As an Agent Skill

Works with any agent that supports the [SKILL.md format](https://skills.sh):

### Hermes Agent

```bash
hermes skills install github.com/RachelXiaolan/video-transcript
```

### Claude Code / Cursor / others

```bash
npx skills add RachelXiaolan/video-transcript
```

### Manual install

Clone this repo into your agent's skills directory.

## Cost

| Tier | Cost | When |
|------|------|------|
| Tier 1 (subtitles) | Free | Video has subtitles (~60-70% of YouTube videos) |
| Tier 2 (Deepgram) | ~$0.0043/min | No subtitles — 10-min video ≈ $0.04 |
| Tier 3 (metadata) | Free | No API key and no subtitles |

Deepgram free tier: **$200 credit on signup** → enough for ~770 hours of audio.

## Comparison

| Feature | This Skill | ZeroPointRepo/youtube-skills | Hermes youtube-content | tapestry-skills |
|---------|-----------|-----|-----|-----|
| **Multi-platform** | ✅ YouTube + 1500+ via generic | ❌ YouTube only | ❌ YouTube only | ❌ YouTube only |
| Subtitle extraction | ✅ | ✅ | ✅ | ✅ |
| No-subtitle fallback | ✅ Deepgram (cloud) | ❌ | ❌ | ✅ Whisper (local GPU) |
| No GPU required | ✅ | ✅ | ✅ | ❌ |
| **Pre-flight confirmation** | ✅ | ❌ | ❌ | ❌ |
| **Pluggable adapters** | ✅ | ❌ | ❌ | ❌ |
| Timestamps | ✅ | ✅ | ✅ | Varies |
| Markdown output (default) | ✅ | ❌ | ❌ | ❌ |
| Cost (no-subtitle) | ~$0.04/10min | N/A (fails) | N/A (fails) | Free (needs GPU) |

## Cloud Server Setup (AWS / GCP / Azure)

YouTube blocks cloud IPs. Run a **Cloudflare WARP proxy** (free) to bypass:

```bash
# One-time setup
docker run -d --name warproxy --cap-add NET_ADMIN \
  --sysctl net.ipv6.conf.all.disable_ipv6=0 \
  -p 1080:1080 kingcc/warproxy

# Use with the skill
export YOUTUBE_PROXY=socks5://127.0.0.1:1080
python3 scripts/fetch_transcript.py "VIDEO_URL"
```

The script auto-detects `YOUTUBE_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`.

See [references/cloud-server-guide.md](references/cloud-server-guide.md) for all proxy options.

## Repository Structure

```
video-transcript/
├── README.md
├── SKILL.md
├── scripts/
│   ├── fetch_transcript.py          # Main CLI entry — auto-detects platform
│   ├── fetch_videos.py              # YouTube channel/playlist video lister
│   ├── platforms/                   # Pluggable platform adapters
│   │   ├── __init__.py              # Registry + URL→adapter routing
│   │   ├── base.py                  # BasePlatform abstract class
│   │   ├── youtube.py               # YouTube (Tier 1 via youtube-transcript-api)
│   │   └── generic.py               # Catch-all (1500+ sites via yt-dlp)
│   └── common/                      # Shared pipeline logic
│       ├── __init__.py
│       ├── deepgram.py              # Tier 2 (audio → Deepgram Nova-3)
│       ├── metadata.py              # Tier 3 (yt-dlp metadata fallback)
│       ├── formatter.py             # Output: md / json / text
│       └── proxy.py                 # Proxy env-var helper
└── references/
    ├── setup-guide.md               # Deepgram API key setup
    └── cloud-server-guide.md        # 5 proxy options for cloud servers
```

## License

MIT
