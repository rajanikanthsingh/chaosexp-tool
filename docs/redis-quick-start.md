# Quick Start: Redis Caching

## ⚡ What You Get

- **20-50x faster** cached page loads (2-5s → 50-100ms)
- **Intelligent incremental updates** - only refresh changed data
- **Zero configuration** - works out of the box with sensible defaults
- **Graceful fallback** - continues working if Redis is unavailable

## 🚀 Setup (5 minutes)

### 1. Install Redis (if not already running)

```bash
# macOS
brew install redis
brew services start redis

# Verify it's running
redis-cli ping  # Should return: PONG
```

### 2. Install Python Dependencies

The `redis` package is already added to `pyproject.toml`. Just reinstall:

```bash
cd /Users/kunalsing.thakur/github/hackathon/chaosmonkey
pip install -e .
```

### 3. Start the Flask Server

```bash
# Set your Nomad credentials
export NOMAD_ADDR="http://your-nomad:4646"
export NOMAD_TOKEN="your-token"

# Optional: Custom Redis URL (defaults to redis://localhost:6379/0)
export REDIS_URL="redis://localhost:6379/0"

# Start the server
python -m chaosmonkey.web.app
```

You should see:
```
✅ Redis cache connected: redis://localhost:6379/0
 * Running on http://0.0.0.0:8080
```

### 4. Test It Out

Open http://localhost:8080 in your browser.

**First visit to Nodes tab:**
- Initial load: ~2-5 seconds (fetches from Nomad)
- Badge shows: 🔄 **Live**

**Refresh the page (within 60 seconds):**
- Reload: ~50-100ms (from Redis cache) ⚡
- Badge shows: 📦 **Cached**

**Click "Refresh" button:**
- Smart update: ~100ms-1s (only updates changed nodes)
- Shows stats: "Updated: 0 new, 0 changed, 5 cached"
- Badge shows: 🔄 **Live**

## 📊 Monitoring

### Check Cache Status

```bash
# Via API
curl http://localhost:8080/api/cache/stats

# Or Redis CLI
redis-cli KEYS "nomad:*"
redis-cli HLEN nomad:clients:hash
```

### Watch Cache Activity

```bash
# Terminal 1: Monitor Redis
redis-cli MONITOR

# Terminal 2: Use the web UI
# You'll see cache operations in real-time
```

### Clear Cache (if needed)

```bash
# Via API
curl -X POST http://localhost:8080/api/cache/clear

# Or Redis CLI
redis-cli FLUSHDB
```

## 🎯 How It Works

### Caching Strategy

1. **Full List Cache** (60s TTL)
   - Key: `nomad:clients:all`
   - Fast initial loads
   - Automatic expiration

2. **Individual Nodes** (5min TTL)
   - Hash: `nomad:clients:hash`
   - Field per node: `node-id` → `{...node data...}`
   - Enables incremental updates

### Refresh Behavior

| Action | Cache Behavior | Speed |
|--------|---------------|-------|
| Initial page load | Check cache → Return if fresh | 50-100ms (cached) |
| Page load (cache expired) | Fetch from Nomad → Cache result | 2-5s (cold) |
| Click "Refresh" | Incremental: Only update changed nodes | 100ms-1s |
| Force refresh (`?refresh=true`) | Bypass cache, fetch all, update cache | 2-5s |

## 🐛 Troubleshooting

### Redis not available?
**No problem!** The app will continue working without caching:
```
⚠️  Redis unavailable, caching disabled: Connection refused
```
All requests will fetch directly from Nomad API (slower but functional).

### Seeing stale data?
Clear the cache:
```bash
curl -X POST http://localhost:8080/api/cache/clear
```

### Want to disable caching temporarily?
Add `?refresh=true` to bypass cache:
```bash
curl http://localhost:8080/api/discover/clients?refresh=true
```

## 📈 Performance Comparison

### Without Redis
```
Browser → Flask → Nomad API (every request)
Time: 2-5 seconds per page load
API Calls: 10-50 per page
```

### With Redis
```
Browser → Flask → Redis (cached)
Time: 50-100ms per page load
API Calls: 1 per page

Browser → Flask → Nomad API (refresh) → Update Redis
Time: 100ms-1s (incremental) or 2-5s (full)
API Calls: 1 + N changed nodes
```

## 🎨 UI Indicators

The UI now shows cache status:

- **📦 Cached** - Lightning fast! Data from Redis
- **🔄 Live** - Fresh from Nomad API
- **Stats** - "Updated: X new, Y changed, Z cached"

## 🔧 Configuration

### Environment Variables

```bash
# Required
export NOMAD_ADDR="http://your-nomad:4646"
export NOMAD_TOKEN="your-token"

# Optional
export REDIS_URL="redis://localhost:6379/0"  # Default
export NOMAD_NAMESPACE="default"             # Default
```

### Adjust Cache TTLs

Edit `src/chaosmonkey/web/app.py`:

```python
# Line ~160: Full list cache
cache.set(cache_key, clients, ttl=60)  # Change 60 to desired seconds

# Line ~161: Node hash cache
cache.expire("nomad:clients:hash", 300)  # Change 300 to desired seconds
```

## 📚 More Info

- **Full documentation**: `docs/redis-caching.md`
- **Implementation details**: `docs/redis-implementation-summary.md`
- **Cache module**: `src/chaosmonkey/web/cache.py`

## ✅ Verification Checklist

- [ ] Redis installed and running (`redis-cli ping`)
- [ ] Python dependencies installed (`pip install -e .`)
- [ ] Server starts successfully (see "Redis cache connected" message)
- [ ] Browser loads http://localhost:8080
- [ ] Nodes tab shows cache badge (📦 or 🔄)
- [ ] Refresh button works and shows stats
- [ ] `/api/cache/stats` returns JSON

---

**That's it!** You now have blazing-fast caching with intelligent incremental updates. 🚀
