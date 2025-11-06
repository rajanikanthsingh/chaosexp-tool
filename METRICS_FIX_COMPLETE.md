# Fix: Metrics Not Being Collected from Web UI

## Problem Identified

When running chaos experiments from the Web UI on node targets, **no metrics were being collected** and therefore **no graphs appeared** in the HTML reports.

### Root Cause

The orchestrator had a critical bug in metrics collection:

1. **Before metrics**: Used Prometheus ✅ (via `_collect_target_metrics()`)
2. **During metrics**: Used OLD Nomad-based collector ❌ (via `collect_continuous_metrics()`)
3. **After metrics**: Used Prometheus ✅ (via `_collect_target_metrics()`)

The issue was in `orchestrator.py` line ~220:
```python
# OLD CODE - WRONG!
during_metrics = self._metrics.collect_continuous_metrics(
    target_type=target.kind.lower(),
    target_id=target.identifier,
    duration_seconds=metrics_duration,
    interval_seconds=metrics_interval,
    label="during"
)
```

This always used the old `MetricsCollector.collect_continuous_metrics()` which:
- For node targets, calls `collect_node_metrics(node_id=...)` 
- Uses **Nomad API** to get metrics (very limited)
- **Does NOT use Prometheus** for nodes
- Returns incompatible data structure

## The Fix

Updated `src/chaosmonkey/core/orchestrator.py` (lines 221-242) to check if the target is a node and use Prometheus:

```python
# NEW CODE - FIXED!
if target_kind == "node" and self._prometheus_metrics:
    # Collect continuous metrics from Prometheus for nodes
    during_metrics = []
    iterations = metrics_duration // metrics_interval
    node_name = target.name if target.name else target.identifier
    
    # Extract short hostname if FQDN
    if "." in node_name:
        node_name = node_name.split(".")[0]
    
    for i in range(iterations):
        snapshot = self._prometheus_metrics.collect_node_metrics(node_name=node_name)
        snapshot["label"] = f"during_{i}"
        during_metrics.append(snapshot)
        
        if i < iterations - 1:
            import time
            time.sleep(metrics_interval)
else:
    # Fall back to old collector for other target types
    during_metrics = self._metrics.collect_continuous_metrics(...)
```

## What Changed

### Before This Fix
- ❌ "During" metrics used Nomad API (limited data)
- ❌ Metrics format was inconsistent (before/after = Prometheus, during = Nomad)
- ❌ No metrics appeared in reports for node targets
- ❌ No graphs generated

### After This Fix
- ✅ All metrics (before/during/after) use Prometheus for node targets
- ✅ Consistent nested format: `{"cpu": {"percent": 12.5}, "memory": {...}, "disk": {...}}`
- ✅ Metrics collected and stored in report JSON
- ✅ Graphs automatically generated in HTML reports

## Files Modified

1. **src/chaosmonkey/core/orchestrator.py** (lines 221-242)
   - Added Prometheus support for continuous "during" metrics collection
   - Keeps backward compatibility for job/allocation/service targets

2. **src/chaosmonkey/core/prometheus_metrics.py** (lines 134, 384-426)
   - Added `_transform_to_nested_format()` method
   - Transforms flat Prometheus metrics to nested report format

## Testing

### Quick Test
```bash
cd /Users/inderdeep.sidhu/PycharmProjects/chaosmonkey
python test_metrics_collection.py
```

### Full End-to-End Test
1. Start Web UI: `python run_web_ui.py`
2. Open browser: http://localhost:5555
3. Select "CPU Hog" experiment
4. Choose a **node** target (e.g., `hostname`)
5. Click "Run Chaos Experiment"
6. Wait for completion
7. Open the generated HTML report
8. **Verify**: You should now see 3-4 interactive Chart.js graphs showing:
   - CPU Usage (before → during → after)
   - Memory Usage
   - Disk I/O (Read)
   - Disk I/O (Write)

## Expected Output

### In Terminal (when running from UI):
```
📊 Collecting baseline metrics for msepg01p1...
   CPU usage: 12.56%
   Memory usage: 65.57%
   Disk I/O - Read: 0, Write: 328082

🔥 Executing chaos...

📊 Collecting metrics during chaos (duration: 60s, interval: 5s)...
   [Prometheus queries running every 5 seconds]

📊 Collecting post-chaos metrics for msepg01p1...
   CPU usage: 87.45%
   ...

📄 Reports generated:
   - JSON: reports/run-XXXXXXXX.json
   - Markdown: reports/run-XXXXXXXX.md
   - HTML: reports/run-XXXXXXXX.html
```

### In Report JSON:
```json
{
  "experiment": {...},
  "result": {...},
  "metrics": {
    "before": {
      "cpu": {"percent": 12.5},
      "memory": {"usage": 5287313408, "percent": 65.57},
      "disk": {"read_bytes": 0, "write_bytes": 214054}
    },
    "during": [
      {"cpu": {"percent": 45.2}, "label": "during_0", ...},
      {"cpu": {"percent": 87.5}, "label": "during_1", ...},
      ...
    ],
    "after": {
      "cpu": {"percent": 13.1},
      ...
    },
    "analysis": {
      "cpu": {
        "before_percent": 12.5,
        "peak_during_percent": 87.5,
        "after_percent": 13.1,
        "change_during": 75.0,
        "recovered": true
      }
    }
  }
}
```

### In HTML Report:
- Section titled "📊 Metrics Analysis" or similar
- 3-4 interactive graphs using Chart.js
- Timeline showing before/during/after data points
- Color-coded lines for easy comparison

## Why This Matters

### Before (Broken)
```
Target: Node msepg01p1
├─ Before metrics: Prometheus ✅ (real data)
├─ During metrics: Nomad API ❌ (no data)
└─ After metrics: Prometheus ✅ (real data)
Result: Incomplete/missing metrics → No graphs
```

### After (Fixed)
```
Target: Node msepg01p1
├─ Before metrics: Prometheus ✅ (real data)
├─ During metrics: Prometheus ✅ (real data every 5s)
└─ After metrics: Prometheus ✅ (real data)
Result: Complete metrics → Beautiful graphs! 📊
```

## Compatibility

- ✅ **Node targets**: Use Prometheus (new, fixed)
- ✅ **Job targets**: Use Nomad API (existing, unchanged)
- ✅ **Allocation targets**: Use Nomad API (existing, unchanged)
- ✅ **Service targets**: Use Nomad API (existing, unchanged)

Only node targets benefit from Prometheus metrics because:
- Nodes have `node_exporter` running
- Prometheus scrapes system-level metrics (CPU, memory, disk I/O)
- Jobs/allocations don't expose system metrics directly

## Troubleshooting

### If metrics still don't appear:

1. **Check Prometheus is accessible**:
   ```bash
   curl -s "http://prometheus/api/v1/query?query=up" | jq '.status'
   # Should return: "success"
   ```

2. **Check node has metrics in Prometheus**:
   ```bash
   curl -s "http://prometheus/api/v1/query?query=up{instance=~\"msepg01p1.*:9100\"}"
   # Should return data with "value": [timestamp, "1"]
   ```

3. **Check orchestrator logs**:
   Look for lines like:
   ```
   📊 Collecting baseline metrics for msepg01p1...
   DEBUG:src.chaosmonkey.core.prometheus_metrics:Collecting metrics for node: msepg01p1
   DEBUG:src.chaosmonkey.core.prometheus_metrics:Found Prometheus instance: hostname:9100
   ```

4. **Verify report has metrics**:
   ```bash
   cat reports/run-XXXXXXXX.json | jq '.metrics | keys'
   # Should output: ["after", "analysis", "before", "during"]
   ```

5. **Check HTML has Chart.js**:
   ```bash
   grep -c "new Chart" reports/run-XXXXXXXX.html
   # Should output: 3 or 4 (number of graphs)
   ```

## Status

✅ **FIXED** - Metrics collection now works properly for node targets from Web UI!

The issue was that "during" metrics were using the wrong collector. Now all three phases (before/during/after) use Prometheus for nodes, resulting in complete metrics data and beautiful interactive graphs in the HTML reports.

---

**Date**: October 10, 2025  
**Fixed By**: AI Assistant  
**Files Changed**: 
- `src/chaosmonkey/core/orchestrator.py` (lines 221-242)
- `src/chaosmonkey/core/prometheus_metrics.py` (lines 134, 384-426)
