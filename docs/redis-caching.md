# Redis Caching Setup for ChaosMonkey

## Overview
ChaosMonkey now uses Redis for caching Nomad client data, making the UI significantly faster with intelligent incremental updates.

## Features
- **Fast Initial Load**: Cached data served in milliseconds
- **Incremental Updates**: Only fetches changed nodes on refresh
- **Smart Caching**: 60s cache for full queries, 5min for node details
- **Graceful Fallback**: Works without Redis (caching disabled)

## Installation

### macOS (Homebrew)
```bash
brew install redis
brew services start redis
```

### Docker
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
```

## Configuration

Set the Redis URL (optional, defaults to `redis://localhost:6379/0`):
```bash
export REDIS_URL="redis://localhost:6379/0"
```

## How It Works

### Initial Load
1. User opens dashboard → API call to `/api/discover/clients`
2. Check Redis cache (key: `nomad:clients:all`)
3. If cached (< 60s old), return immediately
4. Otherwise, fetch from Nomad API and cache

### Refresh Operation
1. User clicks "Refresh" → API call with `?refresh=true`
2. Load cached node details from Redis hash (`nomad:clients:hash`)
3. For each Nomad node:
   - Check if status/drain changed
   - If unchanged, use cached version
   - If changed, fetch fresh details from Nomad
4. Update cache with new/changed nodes only

### Cache Keys
- `nomad:clients:all` - Full client list (TTL: 60s)
- `nomad:clients:hash` - Individual node details (TTL: 5min)

### Performance Gains

**Before (No Cache):**
- Initial load: ~2-5 seconds (depends on node count)
- Refresh: ~2-5 seconds (full reload)

**After (With Cache):**
- Initial load (cached): ~50-100ms 
- Initial load (uncached): ~2-5 seconds (same as before)
- Refresh (no changes): ~100-200ms (uses cached data)
- Refresh (partial changes): ~500ms-1s (only updates changed nodes)

### API Endpoints

#### Get Clients (Cached)
```bash
curl http://localhost:8080/api/discover/clients
```

#### Force Refresh (Bypass Cache)
```bash
curl http://localhost:8080/api/discover/clients?refresh=true
```

#### Clear Cache
```bash
curl -X POST http://localhost:8080/api/cache/clear
```

#### Cache Statistics
```bash
curl http://localhost:8080/api/cache/stats
```

## Monitoring

Check cache hit rate:
```bash
redis-cli INFO stats | grep keyspace
```

View cached keys:
```bash
redis-cli KEYS "nomad:*"
```

Get cached client count:
```bash
redis-cli HLEN nomad:clients:hash
```

## Troubleshooting

### Redis Not Running
If Redis is unavailable, the app will continue to work with caching disabled:
```
⚠️  Redis unavailable, caching disabled: Connection refused
```

### Clear Stuck Cache
```bash
redis-cli FLUSHDB
```

Or via API:
```bash
curl -X POST http://localhost:8080/api/cache/clear \
  -H "Content-Type: application/json" \
  -d '{"pattern": "nomad:*"}'
```

## Development

### Testing Cache Behavior
```python
from chaosmonkey.web.cache import get_cache, invalidate_cache

# Get cache instance
cache = get_cache()

# Check if enabled
print(cache.enabled)

# Manually set/get
cache.set("test:key", {"data": "value"}, ttl=60)
data = cache.get("test:key")

# Clear pattern
invalidate_cache("nomad:*")
```

## Production Recommendations

1. **Use Redis Persistence**: Enable RDB or AOF for data durability
2. **Set Max Memory**: Configure `maxmemory` with `allkeys-lru` policy
3. **Monitor**: Use Redis monitoring tools (RedisInsight, etc.)
4. **Adjust TTLs**: Tune cache TTLs based on your update frequency

### Example Redis Config
```
maxmemory 256mb
maxmemory-policy allkeys-lru
save 60 1000
appendonly yes
```
