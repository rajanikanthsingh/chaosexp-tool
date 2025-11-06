# Fix: Chaos Types Not Showing in UI

## Problem
The web UI was showing "No chaos types available" despite having 6 template files in the `experiments/templates/` directory.

## Root Cause
The `WORKSPACE_ROOT` path calculation in `app.py` was incorrect:

```python
# WRONG - Too many .parent calls
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.parent
```

This resulted in:
```
/Users/kunalsing.thakur/github/hackathon  (too high!)
```

Instead of:
```
/Users/kunalsing.thakur/github/hackathon/chaosmonkey  (correct!)
```

## Solution
Fixed the path calculation to use 4 `.parent` calls instead of 5:

```python
# CORRECT - 4 parents from app.py to workspace root
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
```

### Path Breakdown
```
/Users/kunalsing.thakur/github/hackathon/chaosmonkey/
└── src/
    └── chaosmonkey/
        └── web/
            └── app.py  (start here)
                ↓ .parent
            web/
                ↓ .parent  
            chaosmonkey/
                ↓ .parent
            src/
                ↓ .parent (4th parent)
            chaosmonkey/ ← WORKSPACE_ROOT ✅
```

## Verification
After the fix, the API now returns 6 chaos types:

```json
{
  "chaos_types": [
    {
      "name": "cpu_hog",
      "display_name": "Cpu Hog",
      "description": "Placeholder experiment that schedules a CPU intensive job...",
      "icon": "🔥"
    },
    {
      "name": "memory_hog",
      "display_name": "Memory Hog",
      "description": "Experiment that consumes memory on the target node...",
      "icon": "💾"
    },
    {
      "name": "network_latency",
      "display_name": "Network Latency",
      "description": "Placeholder experiment introducing artificial latency...",
      "icon": "🐌"
    },
    {
      "name": "packet_loss",
      "display_name": "Packet Loss",
      "description": "Placeholder experiment introducing packet loss via...",
      "icon": "📦"
    },
    {
      "name": "host_down",
      "display_name": "Host Down",
      "description": "Drain a Nomad node, causing all allocations to be migrated...",
      "icon": "💀"
    },
    {
      "name": "disk_io",
      "display_name": "Disk Io",
      "description": "Experiment that creates heavy disk I/O load...",
      "icon": "💿"
    }
  ]
}
```

## Files Modified
- `src/chaosmonkey/web/app.py` - Line 22: Fixed WORKSPACE_ROOT path calculation

## Testing
```bash
# Test the endpoint
curl http://localhost:8080/api/chaos-types | jq

# Should return 6 chaos types with icons and descriptions
```

## Impact
✅ **Dashboard Tab**: Chaos type cards now display all 6 types  
✅ **Execute Tab**: Dropdown now populated with all chaos types  
✅ **API**: `/api/chaos-types` returns complete list  

## Status
**RESOLVED** ✅

The chaos types are now available in the UI and can be selected for chaos experiments.
