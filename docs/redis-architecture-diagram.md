# Redis Caching Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser / Client                         │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    │ HTTP GET /api/discover/clients
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Web Server                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Cache Check Flow                              │  │
│  │                                                            │  │
│  │  1. Check Redis cache: nomad:clients:all                 │  │
│  │     ├─ Found & Fresh (< 60s)? → Return cached ⚡        │  │
│  │     └─ Not found or stale? → Continue to step 2          │  │
│  │                                                            │  │
│  │  2. Load cached node details: nomad:clients:hash         │  │
│  │     └─ Get previously cached node data for incremental   │  │
│  │                                                            │  │
│  │  3. Fetch from Nomad API                                  │  │
│  │     ├─ Get list of all nodes                             │  │
│  │     └─ For each node:                                    │  │
│  │         ├─ In cache & unchanged? → Use cached ⚡        │  │
│  │         ├─ In cache but changed? → Fetch details 🔄     │  │
│  │         └─ New node? → Fetch full details 🆕           │  │
│  │                                                            │  │
│  │  4. Update Redis cache                                    │  │
│  │     ├─ Set nomad:clients:all (TTL: 60s)                 │  │
│  │     └─ Update nomad:clients:hash (TTL: 5min)            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────┬─────────────────────────────┬─────────────────────┘
              │                             │
              │                             │
              ▼                             ▼
    ┌──────────────────┐          ┌──────────────────┐
    │   Redis Cache    │          │   Nomad API      │
    │                  │          │                  │
    │  • Quick lookup  │          │  • Source of     │
    │  • 50-100ms      │          │    truth         │
    │  • In-memory     │          │  • 2-5s queries  │
    └──────────────────┘          └──────────────────┘
```

## Cache Keys Structure

```
Redis Database 0
│
├─ nomad:clients:all                    [String, TTL: 60s]
│  └─ Value: JSON array of all clients
│     Example: [
│       {"id": "abc123", "name": "node-1", "status": "ready", ...},
│       {"id": "def456", "name": "node-2", "status": "ready", ...}
│     ]
│
└─ nomad:clients:hash                   [Hash, TTL: 5min]
   ├─ Field: "abc123"  → Value: {...node-1 data...}
   ├─ Field: "def456"  → Value: {...node-2 data...}
   └─ Field: "ghi789"  → Value: {...node-3 data...}
```

## Request Flow Diagrams

### Scenario 1: Initial Load (Cold Cache)

```
Browser                Flask                Redis              Nomad
   │                     │                    │                  │
   │─── GET /clients ───>│                    │                  │
   │                     │                    │                  │
   │                     │─── GET key ───────>│                  │
   │                     │<── NOT FOUND ──────│                  │
   │                     │                    │                  │
   │                     │─────── List nodes ────────────────────>│
   │                     │<────── 5 nodes ───────────────────────│
   │                     │                    │                  │
   │                     │─────── Node details (5x API calls) ───>│
   │                     │<────── Node data ─────────────────────│
   │                     │                    │                  │
   │                     │─── SET cache ─────>│                  │
   │                     │<── OK ─────────────│                  │
   │                     │                    │                  │
   │<── Response (2-5s) ─│                    │                  │
   │    [5 nodes]        │                    │                  │

Result: Full fetch from Nomad, cache populated
Time: 2-5 seconds
API Calls: 6 (1 list + 5 details)
```

### Scenario 2: Subsequent Load (Hot Cache)

```
Browser                Flask                Redis              Nomad
   │                     │                    │                  │
   │─── GET /clients ───>│                    │                  │
   │                     │                    │                  │
   │                     │─── GET key ───────>│                  │
   │                     │<── [5 nodes] ──────│                  │
   │                     │                    │                  │
   │<── Response (50ms) ─│                    │                  │
   │    [5 nodes] 📦     │                    │                  │

Result: Instant response from Redis
Time: 50-100ms
API Calls: 0 (all from cache)
```

### Scenario 3: Refresh with Changes (Incremental)

```
Browser                Flask                Redis              Nomad
   │                     │                    │                  │
   │─ GET ?refresh=true >│                    │                  │
   │                     │                    │                  │
   │                     │─ HGETALL hash ────>│                  │
   │                     │<─ {5 cached} ──────│                  │
   │                     │                    │                  │
   │                     │─────── List nodes ────────────────────>│
   │                     │<────── 5 nodes ───────────────────────│
   │                     │                    │                  │
   │                     │  Compare:          │                  │
   │                     │  • node-1: unchanged → use cache ⚡    │
   │                     │  • node-2: status changed → fetch 🔄  │
   │                     │  • node-3: unchanged → use cache ⚡    │
   │                     │  • node-4: unchanged → use cache ⚡    │
   │                     │  • node-5: unchanged → use cache ⚡    │
   │                     │                    │                  │
   │                     │─── Details for node-2 only ───────────>│
   │                     │<── Node-2 data ───────────────────────│
   │                     │                    │                  │
   │                     │─ UPDATE cache ────>│                  │
   │                     │<── OK ─────────────│                  │
   │                     │                    │                  │
   │<── Response (500ms)─│                    │                  │
   │  Updated: 0 new,    │                    │                  │
   │           1 changed,│                    │                  │
   │           4 cached  │                    │                  │

Result: Only changed node fetched from Nomad
Time: 500ms - 1s
API Calls: 2 (1 list + 1 detail for changed node)
```

## Cache State Transitions

```
┌─────────────────────────────────────────────────────────┐
│                    Cache Lifecycle                       │
└─────────────────────────────────────────────────────────┘

    [Empty Cache]
         │
         │ First Request
         ▼
    [Cold Cache]
         │
         │ Data fetched & stored
         ▼
    [Hot Cache] ◄──────┐
         │             │
         │ TTL < 60s   │ Refresh
         │             │
         ├─────────────┘
         │
         │ TTL expired
         ▼
    [Stale Cache]
         │
         │ Incremental update
         ▼
    [Hot Cache]

    Cycle continues...
```

## Performance Metrics

### Cache Hit Scenarios

```
┌──────────────────────┬─────────────┬──────────┬─────────────┐
│ Scenario             │ Cache State │ Time     │ Nomad Calls │
├──────────────────────┼─────────────┼──────────┼─────────────┤
│ Initial Load         │ COLD        │ 2-5s     │ 6+          │
│ Page Refresh (<60s)  │ HOT         │ 50-100ms │ 0           │
│ Page Refresh (>60s)  │ STALE       │ 100-200ms│ 1           │
│ Manual Refresh       │ STALE       │ 500ms-1s │ 1-6         │
│ Force Refresh        │ BYPASS      │ 2-5s     │ 6+          │
└──────────────────────┴─────────────┴──────────┴─────────────┘
```

### Cache Efficiency

```
Without Cache:
  ┌──────────────────────────────────────────────┐
  │████████████████████████████████████ 2-5s     │  Every request
  └──────────────────────────────────────────────┘

With Cache (Hot):
  ┌──┐                                            
  │██│ 50-100ms                                    Most requests
  └──┘

With Cache (Incremental):
  ┌───────┐
  │███████│ 500ms-1s                               Changed data only
  └───────┘

Performance Improvement: 20-50x faster!
```

## Code Flow

### Flask Endpoint: `/api/discover/clients`

```python
def discover_clients():
    # 1. Check query parameter
    force_refresh = request.args.get('refresh') == 'true'
    
    # 2. Try cache (unless forcing refresh)
    if not force_refresh:
        cached = cache.get("nomad:clients:all")
        if cached:
            return cached  # ⚡ Fast path
    
    # 3. Get cached node details for incremental update
    existing = cache.get_all_hash("nomad:clients:hash")
    
    # 4. Fetch from Nomad
    nodes = nomad.nodes.get_nodes()
    
    # 5. Smart merge: only fetch details for new/changed
    for node in nodes:
        if node in existing and not_changed(node):
            use_cached(node)  # ⚡ Fast
        else:
            fetch_details(node)  # 🔄 Update
    
    # 6. Update cache
    cache.set("nomad:clients:all", clients, ttl=60)
    cache.set_hash("nomad:clients:hash", ...)
    
    return clients
```

## Monitoring & Observability

### Key Metrics to Track

```
┌─────────────────────────────────────────────────────┐
│              Cache Performance Dashboard             │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Cache Hit Rate: ████████████████░░░░ 85%          │
│                                                      │
│  Average Response Time:                              │
│    • Cached:     50ms  ⚡                           │
│    • Uncached:  2.5s   🐢                           │
│                                                      │
│  Requests per minute:                                │
│    • From cache: 48 ████████████████████            │
│    • From Nomad:  2 █                               │
│                                                      │
│  Cache Memory: 1.2MB / 256MB (0.5%)                 │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Redis CLI Commands

```bash
# Watch cache activity
redis-cli MONITOR

# Check hit rate
redis-cli INFO stats | grep keyspace_hits

# View cached keys
redis-cli KEYS "nomad:*"

# Check specific cache
redis-cli GET nomad:clients:all
redis-cli HGETALL nomad:clients:hash

# Memory usage
redis-cli MEMORY USAGE nomad:clients:all
```

## Best Practices

### ✅ Do's
- Use short TTL (60s) for frequently changing data
- Use longer TTL (5min) for stable reference data
- Implement graceful fallback when Redis unavailable
- Monitor cache hit rates
- Clear cache after destructive operations

### ❌ Don'ts
- Don't cache sensitive credentials
- Don't set TTL too long (stale data)
- Don't cache errors or failures
- Don't ignore cache invalidation
- Don't assume Redis is always available

## Troubleshooting Guide

```
Problem: Seeing stale data
Solution: curl -X POST http://localhost:8080/api/cache/clear

Problem: Cache not working
Check:
  1. Redis running? → redis-cli ping
  2. Connection OK? → Check Flask logs for "Redis cache connected"
  3. Keys exist? → redis-cli KEYS "nomad:*"

Problem: Too slow with cache
Check:
  1. Cache hit rate → /api/cache/stats
  2. TTL too short? → Adjust in code
  3. Network latency? → Use local Redis

Problem: Memory usage high
Solution:
  1. Set maxmemory: redis-cli CONFIG SET maxmemory 256mb
  2. Set eviction: redis-cli CONFIG SET maxmemory-policy allkeys-lru
```
