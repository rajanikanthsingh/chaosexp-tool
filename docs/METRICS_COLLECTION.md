# Metrics Collection and Comparison

## Overview

ChaosMonkey now includes a comprehensive metrics collection system that captures resource metrics **before**, **during**, and **after** chaos experiments. This allows you to:

- 📊 Quantify the impact of chaos experiments
- 🔍 Verify system resilience and recovery
- 📈 Generate detailed comparison reports
- ✅ Validate SLOs and performance baselines

## Features

### Three-Phase Metrics Collection

1. **Before Chaos** - Baseline snapshot of system metrics
2. **During Chaos** - Continuous metric collection at configurable intervals
3. **After Chaos** - Post-experiment snapshot to verify recovery

### Supported Metrics

#### CPU Metrics
- CPU percentage utilization
- System mode time
- User mode time
- Total CPU ticks
- Throttling periods and time

#### Memory Metrics
- RSS (Resident Set Size)
- Cache memory
- Swap usage
- Total memory usage
- Maximum usage
- Kernel usage

#### Status Metrics
- Allocation status
- Job health
- Node status
- Scheduling eligibility

## Usage

### CLI

#### Basic Usage with Metrics

```bash
# Run experiment with metrics collection (enabled by default)
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id <allocation-id>
```

#### Disable Metrics Collection

```bash
# Skip metrics collection
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id <allocation-id> \
  --no-metrics
```

#### Customize Metrics Collection

```bash
# Collect metrics for 120 seconds at 10-second intervals
chaosmonkey execute \
  --chaos-type memory-hog \
  --target-id <allocation-id> \
  --metrics-duration 120 \
  --metrics-interval 10
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--collect-metrics` / `--no-metrics` | `True` | Enable/disable metrics collection |
| `--metrics-duration` | `60` | Duration to collect metrics during chaos (seconds) |
| `--metrics-interval` | `5` | Interval between metric collections (seconds) |

### Example Commands

```bash
# CPU hogging experiment with 2-minute metrics collection
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id 47c8d0f2 \
  --duration 120 \
  --metrics-duration 120 \
  --metrics-interval 10

# Memory hogging with fast metric sampling
chaosmonkey execute \
  --chaos-type memory-hog \
  --target-id my-job \
  --metrics-interval 2

# Network latency without metrics
chaosmonkey execute \
  --chaos-type network-latency \
  --target-id node-id \
  --no-metrics
```

## Report Output

### Metrics Comparison Section

The generated reports now include a **Metrics Comparison Report** section:

```markdown
## 📈 Metrics Comparison Report

### CPU Usage

| Phase | CPU % |
|-------|-------|
| **Before Chaos** | 15.23% |
| **Peak During Chaos** | 98.45% |
| **After Chaos** | 16.10% |

**Change During Chaos:** +83.22%

**Recovery Status:** ✅ Recovered

### Memory Usage

| Phase | Memory (MB) |
|-------|-------------|
| **Before Chaos** | 512.00 MB |
| **Peak During Chaos** | 2048.00 MB |
| **After Chaos** | 520.00 MB |

**Change During Chaos:** +1536.00 MB

**Recovery Status:** ✅ Recovered

### Status Stability

**Before:** running

**After:** running

**Stable:** ✅ Yes

### Metrics Timeline

```
CPU Usage During Chaos:
    0s: ███████ 15.2%
    5s: ████████████████████████████████████████ 95.5%
   10s: ████████████████████████████████████████████████ 98.4%
   15s: ████████████████████████████████████████████████ 98.1%
   20s: ████████████████████████████████████████████████ 97.8%
   25s: ███████████████████████████████████████ 92.3%
```
```

### JSON Output

The metrics are also included in the JSON report (`run-*.json`):

```json
{
  "experiment": { ... },
  "result": { ... },
  "metrics": {
    "before": {
      "timestamp": "2024-01-15T10:00:00.000000",
      "label": "before",
      "allocation_id": "47c8d0f2",
      "cpu": {
        "percent": 15.23,
        "system_mode": 1234,
        "user_mode": 5678
      },
      "memory": {
        "rss": 536870912,
        "usage": 536870912
      }
    },
    "during": [
      {
        "timestamp": "2024-01-15T10:01:05.000000",
        "label": "during_0",
        "cpu": { "percent": 95.5 }
      },
      ...
    ],
    "after": {
      "timestamp": "2024-01-15T10:03:00.000000",
      "label": "after",
      "cpu": { "percent": 16.10 }
    },
    "analysis": {
      "cpu": {
        "before_percent": 15.23,
        "peak_during_percent": 98.45,
        "after_percent": 16.10,
        "change_during": 83.22,
        "recovery": -0.87,
        "recovered": true
      },
      "memory": { ... },
      "status": { ... }
    }
  }
}
```

## Python API

### Using MetricsCollector Directly

```python
from chaosmonkey.core.metrics import MetricsCollector
from chaosmonkey.core.nomad import NomadClient

# Initialize
nomad_client = NomadClient(address="http://localhost:4646")
metrics = MetricsCollector(nomad_client=nomad_client)

# Collect snapshot
before = metrics.collect_nomad_allocation_metrics(
    allocation_id="47c8d0f2",
    label="before"
)

# Continuous collection during experiment
during = metrics.collect_continuous_metrics(
    target_type="allocation",
    target_id="47c8d0f2",
    duration_seconds=60,
    interval_seconds=5,
    label="during"
)

# After snapshot
after = metrics.collect_nomad_allocation_metrics(
    allocation_id="47c8d0f2",
    label="after"
)

# Compare
comparison = metrics.compare_metrics(
    before=before,
    during=during,
    after=after
)

print(f"CPU change: {comparison['analysis']['cpu']['change_during']:.2f}%")
print(f"Recovered: {comparison['analysis']['cpu']['recovered']}")
```

### Target Types

The MetricsCollector supports multiple target types:

- **`allocation`** - Nomad allocation metrics
- **`job`** - Aggregated metrics for all allocations in a job
- **`node`** - Node-level resource metrics

```python
# Job-level metrics
job_metrics = metrics.collect_nomad_job_metrics(
    job_id="my-web-service",
    label="before"
)

# Node-level metrics
node_metrics = metrics.collect_node_metrics(
    node_id="node-123",
    label="before"
)
```

## Configuration

### Via Settings

Metrics collection is enabled by default and controlled per-experiment. No global configuration is required.

### Integration with Orchestrator

The `ChaosOrchestrator` automatically:

1. Initializes the `MetricsCollector` with Nomad/Kubernetes clients
2. Collects baseline metrics before experiment execution
3. Monitors metrics continuously during the experiment
4. Captures final metrics after completion
5. Generates comparison analysis
6. Includes metrics in reports (JSON and Markdown)

## Recovery Validation

The metrics comparison includes automatic recovery validation:

### CPU Recovery
System is considered recovered if CPU usage is within **5%** of baseline:
```python
recovered = abs(after_cpu - before_cpu) < 5
```

### Memory Recovery
System is considered recovered if memory usage is within **10%** of baseline:
```python
recovered = abs(after_mem - before_mem) < (before_mem * 0.1)
```

### Status Recovery
System is considered stable if status matches pre-chaos state:
```python
stable = before_status == after_status
```

## Troubleshooting

### Metrics Collection Failed

**Symptom:** Warnings like `⚠️ Failed to collect before metrics: ...`

**Solutions:**
1. Verify Nomad/Kubernetes connectivity
2. Check target ID exists and is accessible
3. Ensure proper permissions/tokens
4. Check the orchestrator logs for detailed errors

### No Metrics in Report

**Possible Causes:**
- Metrics collection disabled (`--no-metrics`)
- Dry-run mode active (`--dry-run`)
- Metrics collection failed (check warnings)
- Target type not supported for metrics

### Continuous Metrics Empty

**Check:**
1. `metrics_duration` > 0
2. Target still exists during experiment
3. Network connectivity maintained
4. No rate limiting from API

## Performance Considerations

### Metric Collection Overhead

- Minimal CPU/memory overhead (~0.1% per collection)
- API calls: 2 + (duration / interval) per experiment
- Storage: ~5KB per snapshot, ~100KB per full report

### Recommended Settings

| Experiment Duration | Metrics Duration | Interval |
|---------------------|------------------|----------|
| < 30s | 30s | 2s |
| 30s - 2m | 60s | 5s |
| 2m - 5m | 120s | 10s |
| > 5m | 300s | 15s |

### Rate Limiting

To avoid overwhelming APIs:
- Use intervals ≥ 2 seconds
- Limit duration for long experiments
- Consider job-level metrics for high cardinality

## Examples

### Example 1: CPU Hogging Analysis

```bash
# Run CPU hogging with detailed metrics
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id web-service-alloc \
  --duration 60 \
  --metrics-duration 60 \
  --metrics-interval 5
```

**Expected Report:**
- Before: ~10-20% CPU
- During: 90-100% CPU (sustained)
- After: Returns to ~10-20% CPU within 5%
- Recovery: ✅ Verified

### Example 2: Memory Hogging Analysis

```bash
# Run memory hogging with extended monitoring
chaosmonkey execute \
  --chaos-type memory-hog \
  --target-id database-alloc \
  --duration 120 \
  --metrics-duration 180 \
  --metrics-interval 10
```

**Expected Report:**
- Before: Baseline memory usage
- During: Memory increases to hog amount
- After: Memory returns to within 10% of baseline
- Recovery: Monitor for 60s post-experiment

### Example 3: Multi-Target Job Analysis

```bash
# Analyze entire job impact
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id my-job \
  --metrics-duration 90 \
  --metrics-interval 5
```

**Report Includes:**
- Aggregate CPU/memory for all allocations
- Per-allocation breakdown
- Running allocation count
- Overall job health

## Future Enhancements

Planned features for metrics collection:

- [ ] Network I/O metrics (bytes in/out, packets)
- [ ] Disk I/O metrics (read/write throughput)
- [ ] Custom metric sources (Prometheus, Datadog)
- [ ] Real-time metrics streaming to web UI
- [ ] Metric alerting and anomaly detection
- [ ] Historical metrics comparison
- [ ] Export to time-series databases
- [ ] Grafana dashboard integration

## See Also

- [Architecture Documentation](ARCHITECTURE_AND_IMPLEMENTATION.md)
- [Report Guide](REPORTS_GUIDE.md)
- [Web UI Guide](WEB_UI_GUIDE.md)
- [Chaos Implementation Details](CHAOS_IMPLEMENTATION.md)
