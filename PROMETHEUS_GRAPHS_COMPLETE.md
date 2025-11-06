# Prometheus Metrics & Graphs - Complete Implementation

## Overview
Prometheus metrics collection with interactive Chart.js graphs is now fully integrated and working.

## What Was Fixed

### 1. Metrics Format Transformation
**Problem**: PrometheusMetricsCollector returned flat structure but metrics report expected nested structure.

**Solution**: Added `_transform_to_nested_format()` method to convert:
```python
# From (Prometheus format):
{
  "cpu_percent": 12.5,
  "memory_used_bytes": 5287313408,
  "disk_read_bytes": 0,
  "disk_write_bytes": 214054
}

# To (Report format):
{
  "cpu": {"percent": 12.5},
  "memory": {"usage": 5287313408, "total": 8063602688, "percent": 65.57},
  "disk": {"read_bytes": 0, "write_bytes": 214054, "total_bytes": 214054}
}
```

### 2. Graph Support
**Status**: Already implemented in `metrics_report.py`

The report automatically generates:
- **CPU Usage Graph**: Line chart showing CPU percentage before/during/after chaos
- **Memory Usage Graph**: Line chart showing memory consumption in MB
- **Disk I/O Graph**: Dual-line chart showing read/write bytes per second

## How to Use

### From Web UI
1. Select a chaos experiment (CPU Hog, Memory Hog, etc.)
2. Choose a **node** target (graphs work best with node targets)
3. Click "Run Chaos Experiment"
4. **Metrics are collected automatically** (collect_metrics=true by default)
5. View the generated HTML report with interactive graphs

### From CLI
```bash
chaos-monkey run cpu-hog \
  --target-id hostname \
  --collect-metrics \
  --metrics-duration 60 \
  --metrics-interval 5
```

## Prometheus Configuration

### Current Settings (config.yaml)
```yaml
prometheus:
  url: "http://prometheus"
  timeout: 30
```

### Override Prometheus URL
```bash
# Via CLI
chaos-monkey run cpu-hog --prometheus-url http://your-prometheus:9090

# Via Environment Variable
export PROMETHEUS_URL=http://your-prometheus:9090
```

## Metrics Collected

### CPU Metrics
- **Query**: `100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- **Unit**: Percentage
- **Shows**: CPU utilization (inverted from idle time)

### Memory Metrics
- **Query**: 
  - Used: `node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes`
  - Percent: `(1 - MemAvailable/MemTotal) * 100`
- **Unit**: Bytes, Percentage
- **Shows**: Memory consumption and availability

### Disk I/O Metrics
- **Queries**:
  - Read: `rate(node_disk_read_bytes_total[5m])`
  - Write: `rate(node_disk_written_bytes_total[5m])`
- **Unit**: Bytes per second
- **Shows**: Disk read/write throughput

## Files Modified

1. **src/chaosmonkey/core/prometheus_metrics.py**
   - Added `_transform_to_nested_format()` method
   - Updated `collect_node_metrics()` to use transformation
   - Lines 134, 384-426

## Report Generation Flow

```
1. Orchestrator collects metrics
   ├─ Before: collect_node_metrics(node_name, label="before")
   ├─ During: collect_node_metrics(node_name, label="during_N") [multiple times]
   └─ After: collect_node_metrics(node_name, label="after")

2. MetricsCollector.compare_metrics()
   ├─ Analyzes CPU changes (before → peak → after)
   ├─ Analyzes memory changes
   ├─ Analyzes disk I/O changes
   └─ Returns metrics_comparison dict

3. generate_metrics_html_report()
   ├─ Extracts timeline data from metrics_comparison
   ├─ Generates Chart.js configurations
   ├─ Creates interactive HTML with graphs
   └─ Saves as run-XXXXXXXX.html
```

## Verification

### Test Prometheus Connection
```bash
python -c "
from src.chaosmonkey.config import load_settings
from src.chaosmonkey.core.prometheus_metrics import PrometheusMetricsCollector
from pathlib import Path

settings = load_settings(Path('config.yaml'))
collector = PrometheusMetricsCollector(
    prometheus_url=settings.prometheus.url,
    timeout=settings.prometheus.timeout,
)

metrics = collector.collect_node_metrics(node_name='bisls01p1')
print(f'CPU: {metrics[\"cpu\"][\"percent\"]:.2f}%')
print(f'Memory: {metrics[\"memory\"][\"percent\"]:.2f}%')
print(f'Disk Write: {metrics[\"disk\"][\"write_bytes\"]} bytes/sec')
"
```

### Check Report Has Graphs
```bash
# Run chaos with metrics
chaos-monkey run cpu-hog --target-id hostname

# Check the latest report has Chart.js
ls -lt reports/*.html | head -1 | awk '{print $NF}' | xargs grep -c "chart.js"
# Should output: 5 (or similar non-zero number)
```

## Troubleshooting

### Metrics Not Showing in Report
1. **Check Prometheus is accessible**:
   ```bash
   curl -s "http://prometheus/api/v1/query?query=up" | jq '.status'
   # Should return: "success"
   ```

2. **Check node has node_exporter**:
   ```bash
   curl -s "http://prometheus/api/v1/query?query=up{job=\"node_exporter\"}" | jq '.data.result | length'
   # Should return: > 0
   ```

3. **Check node name pattern**:
   - Prometheus instances use FQDN: `hostname:9100`
   - Short names are tried first: `bisls01p1:9100`
   - Both patterns are supported

### Graphs Not Rendering
1. **Check report has metrics data**:
   ```bash
   cat reports/run-XXXXXXXX.json | jq '.metrics | keys'
   # Should return: ["after", "analysis", "before", "during"]
   ```

2. **Check HTML has Chart.js**:
   ```bash
   grep "chart.js" reports/run-XXXXXXXX.html
   # Should find: <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/...">
   ```

## Next Steps

### For Node Targets
✅ **Prometheus metrics collection** - Working
✅ **Chart.js graphs in reports** - Working
✅ **Before/during/after comparison** - Working

### For Other Targets (Jobs, Allocations, Services)
- Still use old Nomad-based metrics collector
- No Prometheus integration (Nomad targets don't have node_exporter)
- Graphs will still work if metrics are collected

## Example Output

When you run a chaos experiment on a node:

```
🎯 Running chaos experiment: cpu-hog
📊 Collecting before metrics from Prometheus for node: bisls01p1
   CPU usage: 12.56%
   Memory usage: 65.57%
   Disk I/O - Read: 0, Write: 328082
🔥 Executing chaos...
📊 Collecting during metrics...
   CPU usage: 87.23%
   ...
📊 Collecting post-chaos metrics for bisls01p1
   CPU usage: 13.45%
   ...
📄 Reports generated:
   - JSON: /reports/run-abc123.json
   - Markdown: /reports/run-abc123.md
   - HTML: /reports/run-abc123.html
```

Open `run-abc123.html` in browser to see interactive graphs! 📊📈

## Architecture

```
┌─────────────────┐
│   Web UI / CLI  │
└────────┬────────┘
         │ collect_metrics=true
         ▼
┌─────────────────────────┐
│   Orchestrator          │
│  • run_experiment()     │
│  • _collect_target_     │
│    metrics()            │
└────────┬────────────────┘
         │ For node targets
         ▼
┌──────────────────────────┐
│ PrometheusMetrics        │
│ Collector                │
│  • collect_node_metrics()│
│  • _transform_to_nested_ │
│    format()              │
└────────┬─────────────────┘
         │ PromQL queries
         ▼
┌─────────────────────────┐
│   Prometheus Server     │
│   http://inpro01p1:9090 │
│  • node_exporter metrics│
│  • CPU, Memory, Disk I/O│
└─────────────────────────┘
         │
         ▼ Metrics returned
┌─────────────────────────┐
│  MetricsCollector       │
│  • compare_metrics()    │
│  • Analyze changes      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ generate_metrics_html   │
│ _report()               │
│  • Chart.js graphs      │
│  • Interactive timeline │
└─────────────────────────┘
         │
         ▼
   📊 HTML Report
```

## Status
✅ **Prometheus Integration**: Complete
✅ **Metrics Collection**: Working for node targets
✅ **Graph Generation**: Working with Chart.js
✅ **Web UI Support**: Enabled by default
✅ **CLI Support**: Full support with options

**Ready for Production Use!** 🎉
