# Quick Start: Metrics Collection

Get started with metrics collection for chaos experiments in 5 minutes.

## Prerequisites

- ChaosMonkey installed
- Nomad cluster running with allocations
- Python 3.11+

## 1. Run Your First Experiment with Metrics

```bash
# Execute a CPU hog experiment with metrics collection
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id <your-allocation-id> \
  --duration 60
```

**What happens:**
- ✅ Collects baseline metrics BEFORE chaos
- ✅ Executes CPU hogging for 60 seconds
- ✅ Monitors metrics DURING chaos (every 5 seconds)
- ✅ Collects recovery metrics AFTER chaos
- ✅ Generates comparison report

## 2. View the Report

```bash
# View the latest report
chaosmonkey report

# Or view a specific run
chaosmonkey report run-abc12345
```

**Look for the "📈 Metrics Comparison Report" section:**

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
```

## 3. Customize Metrics Collection

### Extended Duration
```bash
# Collect metrics for 2 minutes at 10-second intervals
chaosmonkey execute \
  --chaos-type memory-hog \
  --target-id <allocation-id> \
  --metrics-duration 120 \
  --metrics-interval 10
```

### Fast Sampling
```bash
# High-frequency sampling (2-second intervals)
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id <allocation-id> \
  --metrics-interval 2
```

### Disable Metrics
```bash
# Skip metrics collection entirely
chaosmonkey execute \
  --chaos-type network-latency \
  --target-id <allocation-id> \
  --no-metrics
```

## 4. Try the Demo Script

```bash
# Run the interactive demo
python examples/metrics_collection_demo.py
```

**The demo shows:**
- Real-time metrics collection
- Before/during/after snapshots
- Automatic comparison
- Recovery validation
- JSON report generation

## 5. Understanding the Output

### During Execution

You'll see progress messages:

```
📊 Collecting baseline metrics for alloc-123...
⚡ Executing chaos experiment...
📊 Collecting metrics during chaos (duration: 60s, interval: 5s)...
📊 Collecting post-chaos metrics for alloc-123...
```

### In the Report

**CPU Analysis:**
- Shows baseline, peak, and recovery values
- Calculates change during chaos
- Validates recovery (within 5%)

**Memory Analysis:**
- Tracks memory usage in MB
- Shows peak consumption
- Validates recovery (within 10%)

**Status Stability:**
- Confirms system status before/after
- Flags any state changes

**Timeline Visualization:**
- ASCII chart of metrics over time
- Shows metric trends during chaos

## 6. Common Use Cases

### Verify CPU Hogging Impact

```bash
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id <alloc-id> \
  --duration 120
```

**Check report for:**
- CPU spike to 90-100%
- Return to baseline within 5%

### Validate Memory Recovery

```bash
chaosmonkey execute \
  --chaos-type memory-hog \
  --target-id <alloc-id> \
  --duration 90
```

**Check report for:**
- Memory increase during chaos
- Full recovery after chaos

### Monitor Long-Running Experiments

```bash
chaosmonkey execute \
  --chaos-type network-latency \
  --target-id <alloc-id> \
  --duration 300 \
  --metrics-duration 300 \
  --metrics-interval 15
```

**Results in:**
- 20 metric snapshots (300s / 15s)
- Extended timeline visualization
- Detailed impact analysis

## 7. Troubleshooting

### "No allocations found"
**Solution:** Ensure you have running jobs in Nomad:
```bash
nomad job status
nomad alloc status <alloc-id>
```

### "Failed to collect metrics"
**Solution:** Verify Nomad connectivity:
```bash
export NOMAD_ADDR="http://localhost:4646"
chaosmonkey discover
```

### "Metrics show no recovery"
**Possible causes:**
- System is genuinely not recovering
- Need more time for recovery
- Resource leak in application

**Solution:** Check application logs and extend metrics collection duration

## 8. Next Steps

- 📖 Read [full documentation](METRICS_COLLECTION.md)
- 🔧 Try different chaos types
- 📊 Compare multiple experiments
- 🎨 Export metrics to monitoring tools
- 🤖 Integrate into CI/CD pipelines

## CLI Reference

| Option | Default | Description |
|--------|---------|-------------|
| `--collect-metrics` | `True` | Enable metrics collection |
| `--no-metrics` | - | Disable metrics collection |
| `--metrics-duration` | `60` | Duration in seconds |
| `--metrics-interval` | `5` | Interval in seconds |

## Quick Tips

✅ **DO:**
- Use default settings for most experiments
- Increase interval for long experiments
- Review metrics timeline in reports
- Compare experiments over time

❌ **DON'T:**
- Use intervals < 2 seconds (rate limiting)
- Set duration > experiment duration
- Skip metrics for production tests
- Ignore recovery warnings

## Support

For issues or questions:
1. Check [full documentation](METRICS_COLLECTION.md)
2. Review [examples](../examples/README.md)
3. Check [troubleshooting guide](METRICS_COLLECTION.md#troubleshooting)

Happy chaos engineering! 🎉
