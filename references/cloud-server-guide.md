# Cloud Server YouTube Access Guide

## The Problem

YouTube aggressively blocks requests from cloud provider IPs (AWS, GCP, Azure, etc.):
- **Tier 1** (`youtube-transcript-api`): Returns "IP blocked" or "RequestBlocked"
- **Tier 2** (`yt-dlp` download): Returns "Sign in to confirm you're not a bot"

This affects **all server-based tools** (not just this skill). On a local machine with residential IP, everything works fine.

## Solutions (pick one)

### Option 1: Cloudflare WARP Proxy (Recommended, Free)

Cloudflare WARP provides residential-like IPs that YouTube does **not** blacklist. The easiest way is to run it as a Docker container:

**Using [warproxy](https://github.com/kingcc/warproxy) (one command):**

```bash
docker run -d --name warproxy \
  --cap-add NET_ADMIN \
  --sysctl net.ipv6.conf.all.disable_ipv6=0 \
  -p 1080:1080 \
  kingcc/warproxy
```

This starts a SOCKS5 proxy on `localhost:1080`.

**Then run the skill with proxy:**

```bash
# For yt-dlp (Tier 2)
https_proxy=socks5://127.0.0.1:1080 python3 scripts/fetch_transcript.py "VIDEO_URL"

# For youtube-transcript-api (Tier 1) — requires code change, see below
ALL_PROXY=socks5://127.0.0.1:1080 python3 scripts/fetch_transcript.py "VIDEO_URL"
```

**For youtube-transcript-api**, set the proxy in environment:

```python
import os
os.environ['HTTP_PROXY'] = 'socks5://127.0.0.1:1080'
os.environ['HTTPS_PROXY'] = 'socks5://127.0.0.1:1080'
```

Or install `pysocks` for SOCKS5 support:

```bash
pip install pysocks
```

**Docker Compose (persistent):**

```yaml
services:
  warproxy:
    image: kingcc/warproxy
    container_name: warproxy
    cap_add:
      - NET_ADMIN
    sysctls:
      - net.ipv6.conf.all.disable_ipv6=0
    ports:
      - "1080:1080"
    restart: unless-stopped
```

### Option 2: PO Token Plugin (No Docker needed)

yt-dlp supports [PO Token provider plugins](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) that automatically generate proof-of-origin tokens to bypass bot detection.

```bash
# Install the PO Token framework
pip install yt-dlp-get-pot

# Install a PO Token provider (e.g., bgutil)
pip install bgutil-ytdlp-pot-provider

# Run the provider server (background)
docker run -d --name bgutil-provider -p 4416:4416 brainicism/bgutil-ytdlp-pot-provider

# yt-dlp will automatically use the PO token
python3 scripts/fetch_transcript.py "VIDEO_URL"
```

> **Note:** PO Token only helps with yt-dlp (Tier 2), not with `youtube-transcript-api` (Tier 1).

### Option 3: Residential Proxy (Paid)

Services like [Webshare](https://www.webshare.io/) or [Bright Data](https://brightdata.com/) offer residential proxies:

```bash
# Set proxy for all HTTP requests
export HTTP_PROXY="http://user:pass@proxy.webshare.io:80"
export HTTPS_PROXY="http://user:pass@proxy.webshare.io:80"

python3 scripts/fetch_transcript.py "VIDEO_URL"
```

Cost: ~$1-5/GB of traffic.

### Option 4: Tor (Free but slow)

```bash
# Run Tor proxy
docker run -d --name tor -p 9050:9050 dperson/torproxy

# Use Tor
https_proxy=socks5://127.0.0.1:9050 python3 scripts/fetch_transcript.py "VIDEO_URL"
```

> **Note:** Tor is slow and YouTube sometimes blocks Tor exit nodes. Not recommended for production.

### Option 5: Cookies (Fragile)

Export cookies from your browser using a [cookies.txt extension](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc):

```bash
yt-dlp --cookies cookies.txt "VIDEO_URL"
```

> **Warning:** YouTube frequently invalidates exported cookies. Not reliable for automation.

## Recommendation Matrix

| Option | Cost | Reliability | Setup | Covers Tier 1? | Covers Tier 2? |
|--------|------|-------------|-------|:-:|:-:|
| **WARP Proxy** | Free | ⭐⭐⭐⭐ | Docker one-liner | ✅ | ✅ |
| **PO Token** | Free | ⭐⭐⭐ | pip + Docker | ❌ | ✅ |
| **Residential Proxy** | $1-5/GB | ⭐⭐⭐⭐⭐ | env vars | ✅ | ✅ |
| **Tor** | Free | ⭐⭐ | Docker one-liner | ✅ | ✅ |
| **Cookies** | Free | ⭐ | Manual export | ❌ | ✅ |

**For most users:** Cloudflare WARP (Option 1) is the best balance of free + reliable + easy setup.
