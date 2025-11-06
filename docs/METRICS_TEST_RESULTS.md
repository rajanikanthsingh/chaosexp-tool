# Metrics Source Testing Results

**Date:** October 10, 2025  
**Purpose:** Determine which metrics source provides real-time data for chaos monitoring

---

## 🎯 WINNER: PROMETHEUS ✅

Based on testing, **Prometheus is the clear winner** for metrics collection:

---

## Test Results Summary

### 1. ✅ PROMETHEUS - **WORKS PERFECTLY**

**Status:** ✅ FULLY FUNCTIONAL

**Test Results:**
```
✓ Prometheus is accessible!
✓ Prometheus API is working
✓ Found 148 'up' metrics

✓ Available Metrics:
  - CPU Usage: 168 series
  - Memory Available: 52 series
  - Memory Total: 52 series
  - Disk Read Bytes: 220 series
  - Disk Write Bytes: 220 series
  - Network Receive: 112 series
  - Network Transmit: 112 series

✓ Found 52 nodes with metrics

Sample Data (REAL VALUES):
  Node 1: hostname
    CPU Usage: 10.00%
    Memory Usage: 65.60%

  Node 2: hostname
    CPU Usage: 13.22%
    Memory Usage: 96.21%

  Node 3: hostname
    CPU Usage: 5.55%
    Memory Usage: 98.58%

✓ Time-series data works:
  - Retrieved data for last 5 minutes
  - 11 data points per series
  - Perfect for before/during/after graphs
```

**What It Provides:**
- ✅ Real-time CPU % usage
- ✅ Real-time memory consumption
- ✅ Disk I/O read/write rates
- ✅ Network I/O rates
- ✅ Time-series data (historical)
- ✅ 52 nodes monitored
- ✅ Multiple metrics per node

**Connection Details:**
- URL: `http://prometheus`
- Authentication: None (already accessible)
- Protocol: HTTP REST API
- Format: JSON responses
- Query Language: PromQL

---

### 2. ⚠️ NOMAD - **PARTIALLY WORKS**

**Status:** ⚠️ LIMITED FUNCTIONALITY

**Test Results:**
```
✓ Connected to Nomad
✓ Found 34 nodes

Node Details:
  Name: hostname
  Status: ready
  Resources (Static Capacity):
    - CPU: 0 MHz
    - Memory: 0 MB
    - Disk: 0 MB
  
  ⚠️ These are CAPACITY values, not usage!

✓ Found 4 allocations
  - Running: 4

✗ Allocation Stats: FAILED
  AttributeError (API not accessible)

✓ Client Stats: SUCCESS (but requires direct node access)
  URL: http://10.174.27.92:4646/v1/client/stats
  ⚠️ Requires hitting each client node individually
```

**What It Provides:**
- ✅ Node static capacity (total resources)
- ✅ Node status (ready/down)
- ✅ Allocation list and status
- ⚠️ Client stats (requires direct node access)
- ❌ No aggregated node-level usage
- ❌ No time-series data

**Limitations:**
- Only provides static capacity, not real-time usage
- Allocation stats API not accessible from server
- Would need to hit each client node directly
- No historical data retention
- Complex to aggregate across allocations

---

### 3. ❓ OVIRT - **NOT TESTED YET**

**Status:** ⏸️ TEST INTERRUPTED

**Issue:** Connection test was taking too long

**Expected Capabilities (if accessible):**
- VM-level CPU, memory, disk I/O stats
- Hypervisor-accurate metrics
- Would require VM to Nomad node mapping

**Recommendation:** Skip OVIRT since Prometheus works perfectly

---

## 📊 Comparison Matrix

| Feature | Prometheus | Nomad | OVIRT |
|---------|-----------|-------|-------|
| **Real CPU Usage** | ✅ YES (10%, 13%, 5.5% real values) | ❌ NO (only capacity) | ❓ Unknown |
| **Real Memory Usage** | ✅ YES (65%, 96%, 98% real values) | ❌ NO (only capacity) | ❓ Unknown |
| **Disk I/O** | ✅ YES | ❌ NO | ❓ Unknown |
| **Time-series** | ✅ YES (5min history tested) | ❌ NO | ❓ Limited |
| **Nodes Monitored** | ✅ 52 nodes | ✅ 34 nodes | ❓ Unknown |
| **Already Working** | ✅ YES | ⚠️ Partial | ❓ Not tested |
| **Easy Integration** | ✅ YES | ⚠️ Complex | ⚠️ Complex |
| **API Accessible** | ✅ YES | ⚠️ Partial | ❓ Unknown |

---

## 🎯 Recommendation: USE PROMETHEUS

### Why Prometheus Wins:

1. **✅ Actually Works**
   - Connected successfully
   - Returns real data (not zeros!)
   - 52 nodes already monitored

2. **✅ Provides What We Need**
   - Real-time CPU % (10%, 13%, 5.5% - actual values!)
   - Real-time memory usage (65%, 96%, 98% - actual values!)
   - Disk I/O rates
   - Network I/O rates
   - Time-series data for before/during/after graphs

3. **✅ Already Deployed**
   - No setup required
   - No authentication required
   - Simple HTTP API
   - Working right now

4. **✅ Easy Integration**
   - Simple REST API
   - PromQL query language (powerful)
   - JSON responses (easy to parse)
   - Good documentation

5. **✅ Industry Standard**
   - Widely used
   - Well-maintained
   - Extensive ecosystem
   - Best practices available

---

## 📝 Implementation Plan

### Step 1: Install Python Prometheus Client

```bash
pip install prometheus-api-client
```

### Step 2: Create PrometheusMetricsCollector

New file: `src/chaosmonkey/core/prometheus_metrics.py`

Key features:
- Connect to Prometheus API
- Query node_exporter metrics
- Map Nomad node names to Prometheus instances
- Collect CPU, memory, disk I/O metrics
- Support time-series queries (before/during/after)

### Step 3: Update Orchestrator

Modify `src/chaosmonkey/core/orchestrator.py`:
- Replace `MetricsCollector` with `PrometheusMetricsCollector`
- Pass Prometheus URL from config
- Keep same interface (before/during/after)

### Step 4: Update Configuration

Add to `src/chaosmonkey/config.py`:
```python
@dataclass
class PrometheusSettings:
    url: str = field(default_factory=lambda: os.getenv(
        "PROMETHEUS_URL", 
        "http://prometheus"
    ))
```

### Step 5: Update CLI

Add `--prometheus-url` option to CLI commands

---

## 🔧 Example PromQL Queries

### CPU Usage %
```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

### Memory Usage %
```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

### Disk Read Rate (bytes/sec)
```promql
rate(node_disk_read_bytes_total[5m])
```

### Disk Write Rate (bytes/sec)
```promql
rate(node_disk_written_bytes_total[5m])
```

### Time-Series Query (last 5 minutes)
```python
response = requests.get(
    f"{prometheus_url}/api/v1/query_range",
    params={
        'query': 'rate(node_cpu_seconds_total{mode="idle"}[1m])',
        'start': start_time.timestamp(),
        'end': end_time.timestamp(),
        'step': '30s'  # 30 second intervals
    }
)
```

---

## 📈 Expected Results

### Before Fix (Current):
```
Metrics:
  before: {cpu: 0, memory: 0, disk_read: 0, disk_write: 0}
  during: {cpu: 0, memory: 0, disk_read: 0, disk_write: 0}
  after: {cpu: 0, memory: 0, disk_read: 0, disk_write: 0}
```

### After Prometheus Integration:
```
Metrics:
  before: {cpu: 10.5%, memory: 4.2GB, disk_read: 1.5MB/s, disk_write: 0.8MB/s}
  during: {cpu: 87.3%, memory: 6.8GB, disk_read: 12.4MB/s, disk_write: 8.2MB/s}
  after: {cpu: 15.2%, memory: 4.5GB, disk_read: 2.1MB/s, disk_write: 1.2MB/s}
```

**With real graphs showing:**
- CPU spike during chaos
- Memory increase during chaos
- Disk I/O spike during chaos
- Recovery after chaos ends

---

## 🚀 Next Steps

1. **✅ COMPLETED: Test metrics sources**
2. **⏭️ PENDING: Get approval** to implement Prometheus integration
3. **⏭️ PENDING: Implement PrometheusMetricsCollector**
4. **⏭️ PENDING: Update orchestrator to use Prometheus**
5. **⏭️ PENDING: Test with real chaos experiment**
6. **⏭️ PENDING: Verify graphs show real data**

---

## 📚 Supporting Evidence

### Test Files Created:
- ✅ `tests/test_nomad_metrics_api.py` (tested, partial functionality)
- ✅ `tests/test_prometheus_metrics_api.py` (tested, full functionality)
- ✅ `tests/test_ovirt_metrics_api.py` (not tested, not needed)

### Test Outputs:
- ✅ Nomad: Shows static capacity only
- ✅ Prometheus: Shows real CPU/memory/disk values
- ⏸️ OVIRT: Test interrupted (not needed)

### Documentation:
- ✅ `docs/METRICS_TESTING_GUIDE.md`
- ✅ This results summary

---

## 💡 Conclusion

**PROMETHEUS is the clear winner:**
- ✅ Works now (no setup needed)
- ✅ Provides real data (not zeros)
- ✅ Has everything we need (CPU, memory, disk I/O)
- ✅ Time-series for graphs
- ✅ 52 nodes monitored
- ✅ Easy to integrate

**Ready to implement?** 🚀

Give approval and I'll:
1. Install prometheus-api-client
2. Create PrometheusMetricsCollector
3. Update orchestrator
4. Test with chaos experiment
5. Verify graphs show real data

**No more zeros!** 📈
