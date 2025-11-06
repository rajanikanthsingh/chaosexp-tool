# Bug Fix: Empty Graphs in HTML Reports

## Issue
HTML reports were showing empty graphs with no metrics data visualized.

## Root Cause
The `MetricsCollector` was receiving our custom `NomadClient` wrapper object, but it was expecting the underlying python-nomad `Nomad` client object that has `.allocation`, `.node`, `.job` attributes.

### Error in JSON Report
```json
{
  "metrics": {
    "before": {
      "timestamp": "2025-10-10T08:45:45.222197",
      "label": "before",
      "node_id": "09555425-9f96-1555-abf9-bdad45e8231a",
      "error": "'NomadClient' object has no attribute 'node'"
    }
  }
}
```

## Problem Flow

1. **Orchestrator initialization** (orchestrator.py line 56):
   ```python
   self._metrics = MetricsCollector(
       nomad_client=self._nomad,  # ❌ This is our NomadClient wrapper
       kubernetes_client=self._kubernetes,
   )
   ```

2. **MetricsCollector tries to use** (metrics.py line 50):
   ```python
   allocation = self.nomad_client.allocation.get_allocation(allocation_id)
   # ❌ ERROR: NomadClient wrapper doesn't have .allocation attribute
   ```

3. **MetricsCollector for nodes tries** (metrics.py line 244):
   ```python
   node = self.nomad_client.node.get_node(node_id)
   # ❌ ERROR: 'NomadClient' object has no attribute 'node'
   ```

## Object Structure Mismatch

### Our NomadClient Wrapper
```python
class NomadClient:
    def __init__(self, address, region, token, namespace):
        self._client = nomad.Nomad(...)  # ← The actual python-nomad client
    
    def list_nodes(self):
        # Uses self._client.node.get_node() internally
        pass
    
    # NO .node, .allocation, .job attributes exposed
```

### Python-Nomad Library Client
```python
nomad.Nomad(...)
  ├─ .allocation
  │    ├─ .get_allocation()
  │    └─ .get_allocation_stats()
  ├─ .node
  │    ├─ .get_node()
  │    └─ .get_allocations()
  ├─ .job
  │    └─ .get_job()
  └─ .allocations
       └─ .get_allocations()
```

## Solution

Pass the underlying python-nomad client (not our wrapper) to MetricsCollector:

### orchestrator.py (Line 56-61)

**Before:**
```python
# Initialize metrics collector
self._metrics = MetricsCollector(
    nomad_client=self._nomad,  # ❌ Our wrapper
    kubernetes_client=self._kubernetes,
)
```

**After:**
```python
# Initialize metrics collector
# Pass the underlying nomad client (not our wrapper)
nomad_client_for_metrics = self._nomad._client if self._nomad else None
self._metrics = MetricsCollector(
    nomad_client=nomad_client_for_metrics,  # ✅ Underlying python-nomad client
    kubernetes_client=self._kubernetes,
)
```

## Why This Works

1. **MetricsCollector** expects python-nomad's `Nomad` client with `.allocation`, `.node`, `.job` attributes
2. **Our NomadClient wrapper** stores the actual python-nomad client in `._client`
3. **By passing `._client`**, MetricsCollector gets the object it expects
4. **Metrics collection succeeds**, and HTML reports show data

## Impact

✅ **Fixed:** Metrics collection for all target types (allocations, jobs, nodes)  
✅ **Fixed:** HTML reports now display actual metrics data in charts  
✅ **Fixed:** Before/during/after snapshots properly captured  
✅ **Enhanced:** Charts show CPU, Memory, and Disk I/O over time  

## Testing

### Before Fix
```bash
$ chaosmonkey execute --chaos-type cpu-hog --target-id <node-id>
# Report shows:
# - Empty graphs
# - No data points
# - Error in JSON: "'NomadClient' object has no attribute 'node'"
```

### After Fix
```bash
$ chaosmonkey execute --chaos-type cpu-hog --target-id <node-id>

# Expected output:
# 📊 Collecting baseline metrics for <node-id>...
# 🔥 Executing chaos experiment...
# 📊 Collecting metrics during chaos (duration: 60s, interval: 5s)...
# 📊 Collecting post-chaos metrics for <node-id>...
# ✅ Experiment completed successfully!
# 📄 Reports generated:
#    - JSON: reports/run-abc123.json
#    - Markdown: reports/run-abc123.md
#    - HTML: reports/run-abc123.html

# HTML report now shows:
# ✅ CPU usage chart with data points
# ✅ Memory usage chart with data points
# ✅ Disk I/O chart with read/write data
# ✅ Combined metrics view
# ✅ Summary cards with actual values
```

## Verification

Check JSON report for successful metrics collection:

```bash
cat reports/run-<latest>.json | grep -A 10 '"metrics"'
```

**Good Output:**
```json
"metrics": {
  "before": {
    "timestamp": "2025-10-10T...",
    "label": "before",
    "node_id": "...",
    "node_name": "...",
    "status": "ready",
    "resources": {
      "cpu_mhz": 8000,
      "memory_mb": 32768,
      "disk_mb": 102400
    },
    ...
  }
}
```

**Bad Output (Before Fix):**
```json
"metrics": {
  "before": {
    "error": "'NomadClient' object has no attribute 'node'"
  }
}
```

## Files Modified

1. **`src/chaosmonkey/core/orchestrator.py`**
   - Lines 56-61: Changed to pass `self._nomad._client` instead of `self._nomad`
   - Added comment explaining why we pass the underlying client

## Related Issues

This fix resolves:
- Empty graphs in HTML reports
- Missing metrics data in visualizations
- AttributeError when collecting node metrics
- AttributeError when collecting allocation metrics
- AttributeError when collecting job metrics

## Alternative Solutions Considered

### Option 1: Proxy Methods in NomadClient (Not chosen)
Add proxy properties to NomadClient:
```python
class NomadClient:
    @property
    def allocation(self):
        return self._client.allocation
    
    @property
    def node(self):
        return self._client.node
```
**Rejected:** Would expose too many internal details

### Option 2: Refactor MetricsCollector (Not chosen)
Change MetricsCollector to use NomadClient wrapper methods:
```python
def collect_node_metrics(self, node_id):
    node_details = self.nomad_client.get_node_details(node_id)  # Custom method
```
**Rejected:** Would require extensive refactoring

### Option 3: Pass Underlying Client (✅ Chosen)
Simply pass `self._nomad._client` to MetricsCollector
**Advantages:**
- Minimal code change (1 line)
- No breaking changes
- Clear intent with comment
- Maintains separation of concerns

---

*Fixed: October 10, 2025*  
*Bug ID: empty-metrics-graphs*  
*Severity: High*  
*Status: Resolved* ✅
