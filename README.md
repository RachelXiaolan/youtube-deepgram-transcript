# youtube-deepgram-transcript

YouTube video transcription with **3-tier fallback** — works even when videos have no subtitles.

## Why?

Most YouTube transcript skills only grab subtitles. **When a video has no subtitles, they fail.** This skill adds [Deepgram Nova-3](https://deepgram.com) as a cloud transcription fallback — no GPU required, just an API key.

## The 3-Tier Fallback

```
Tier 1: youtube-transcript-api (subtitles)
  ✅ Free, instant
  ❌ Only works if the video has subtitles enabled
  │
Tier 2: yt-dlp audio download → Deepgram Nova-3
  ✅ Works on ANY video, no GPU needed, high accuracy (~5-7% WER)
  ❌ Requires DEEPGRAM_API_KEY (~$0.0043/min)
  │
Tier 3: yt-dlp metadata (title + description)
  ✅ Always works (unless video is private)
  ❌ Not a real transcript, just metadata
```

## Quick Start

### Install dependencies

```bash
pip install youtube-transcript-api yt-dlp deepgram-sdk ffmpeg-python
```

Make sure `ffmpeg` is also installed (`brew install ffmpeg` / `apt install ffmpeg`).

### Set your Deepgram API key (optional — enables Tier 2)

```bash
export DEEPGRAM_API_KEY="your-key-here"
```

Get a free key with $200 credit at [console.deepgram.com](https://console.deepgram.com).

### Run

```bash
# Default: Markdown output with timestamps
python3 scripts/fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Specify language
python3 scripts/fetch_transcript.py VIDEO_ID -l zh

# Auto-detect language
python3 scripts/fetch_transcript.py VIDEO_ID -l auto

# Raw JSON output
python3 scripts/fetch_transcript.py VIDEO_ID -f json

# Plain text (no timestamps)
python3 scripts/fetch_transcript.py VIDEO_ID -f text

# List videos from a channel
python3 scripts/fetch_videos.py "https://www.youtube.com/@username" 10
```

### Output example (Markdown)

```markdown
> Source: 🎙️ Deepgram Nova-3 Transcription
> Language: en
> Duration: 8m 32s

[00:00] Welcome to today's video where we'll be looking at ...
[00:11] The first thing you need to understand is ...
```

## As an Agent Skill

Works with any agent that supports the [SKILL.md format](https://skills.sh):

### Hermes Agent

```bash
hermes skills install github.com/RachelXiaolan/youtube-deepgram-transcript
```

### Claude Code / Cursor / others

```bash
npx skills add RachelXiaolan/youtube-deepgram-transcript
```

### Manual install

Clone this repo into your agent's skills directory.

## Cost

| Tier | Cost | When |
|------|------|------|
| Tier 1 (subtitles) | Free | Video has subtitles (~60-70% of videos) |
| Tier 2 (Deepgram) | ~$0.0043/min | No subtitles — 10-min video ≈ $0.04 |
| Tier 3 (metadata) | Free | No API key and no subtitles |

Deepgram free tier: **$200 credit on signup** → enough for ~770 hours of audio.

## Comparison

| Feature | This Skill | ZeroPointRepo/youtube-skills | Hermes youtube-content | tapestry-skills |
|---------|-----------|-----|-----|-----|
| Subtitle extraction | ✅ | ✅ | ✅ | ✅ |
| No-subtitle fallback | ✅ Deepgram (cloud) | ❌ | ❌ | ✅ Whisper (local GPU) |
| No GPU required | ✅ | ✅ | ✅ | ❌ |
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

## License

MIT
