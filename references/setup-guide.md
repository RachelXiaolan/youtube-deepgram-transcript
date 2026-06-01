# Setting Up Deepgram API Key

## Get Your Free API Key

1. Go to [console.deepgram.com](https://console.deepgram.com/signup)
2. Sign up (Google/GitHub OAuth or email)
3. You get **$200 free credit** (no credit card required)
4. Go to **API Keys** → Create a new API key
5. Copy the key (starts with a long hex string)

## Configure for This Skill

### Option A: Environment variable (recommended)

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export DEEPGRAM_API_KEY="your-key-here"
```

Then reload:
```bash
source ~/.bashrc
```

### Option B: Inline per-command

```bash
DEEPGRAM_API_KEY="your-key" python scripts/fetch_transcript.py "https://youtube.com/..."
```

### Option C: Hermes Agent

If using as a Hermes skill, set it in your environment config:

```bash
hermes config set env.DEEPGRAM_API_KEY "your-key-here"
```

Or add to `~/.hermes/.env`:
```
DEEPGRAM_API_KEY=your-key-here
```

## Verify It Works

```bash
python -c "
import os
from deepgram import DeepgramClient
client = DeepgramClient(os.environ['DEEPGRAM_API_KEY'])
print('✅ Deepgram API key is valid')
"
```

## Cost Estimates

| Video Length | Deepgram Cost | Credits Used |
|-------------|---------------|------------- |
| 5 min | $0.02 | ~$0.02 |
| 10 min | $0.04 | ~$0.04 |
| 30 min | $0.13 | ~$0.13 |
| 1 hour | $0.26 | ~$0.26 |
| **$200 free credit** | | **~770 hours** |

## Without DEEPGRAM_API_KEY

The skill still works, but with reduced capability:
- ✅ Tier 1: Subtitles (if available) — still works
- ❌ Tier 2: Deepgram transcription — **skipped**
- ✅ Tier 3: Metadata fallback — still works

You only need the API key for videos **without subtitles**.
