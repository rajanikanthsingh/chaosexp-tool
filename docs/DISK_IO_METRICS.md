# Disk I/O Metrics - Implementation Summary

## Overview

Added comprehensive **Disk I/O metrics** tracking and visualization to the ChaosMonkey metrics collection system. Now you can monitor read/write operations and data transfer during chaos experiments.

## Features Added

### 1. Metrics Collection (`src/chaosmonkey/core/metrics.py`)

#### Disk I/O Data Collected:
- **Read Bytes**: Total bytes read from disk
- **Write Bytes**: Total bytes written to disk
- **Total Bytes**: Combined read + write
- **Read Operations**: Number of read I/O operations
- **Write Operations**: Number of write I/O operations  
- **Total Operations**: Combined read + write ops

#### Collection Points:
- ✅ **Before chaos** - Baseline disk I/O
- ✅ **During chaos** - Continuous monitoring
- ✅ **After chaos** - Post-experiment state

### 2. Metrics Comparison (`src/chaosmonkey/core/metrics.py`)

The `compare_metrics()` method now includes disk I/O analysis:

```python
"disk": {
    "before_read_bytes": ...,
    "before_write_bytes": ...,
    "peak_read_bytes": ...,      # Peak during chaos
    "peak_write_bytes": ...,      # Peak during chaos
    "after_read_bytes": ...,
    "after_write_bytes": ...,
    "read_increase": ...,         # Peak - Before
    "write_increase": ...,        # Peak - Before
    "total_increase": ...,        # Total I/O increase
    "read_ops_before": ...,
    "write_ops_before": ...,
    "read_ops_after": ...,
    "write_ops_after": ...,
}
```

### 3. HTML Visualization (`src/chaosmonkey/core/metrics_report.py`)

#### New Chart: Disk I/O Over Time
- **Dual-line chart** showing read and write separately
- **Green line** for read operations (RGB: 16, 185, 129)
- **Orange line** for write operations (RGB: 245, 158, 11)
- **Interactive tooltips** showing exact MB values
- **Smooth animations** with gradient fills

#### New Summary Card: 💿 Disk I/O Metrics
Displays:
- Before Read/Write (MB)
- Peak Read/Write (MB)
- Total I/O Increase (MB)
- Read Operations (before → after)
- Write Operations (before → after)

### 4. Timeline Data (`src/chaosmonkey/core/metrics_report.py`)

The `_prepare_metrics_timeline()` function now extracts:
- Read bytes over time
- Write bytes over time
- Converts to MB for charts
- Includes before/during/after points

## Usage

### Automatic Collection

Disk I/O metrics are **automatically collected** when you run experiments:

```bash
chaosmonkey execute --chaos-type disk-io --target-id <alloc-id>
```

### View in HTML Report

```bash
# Generate and open HTML report
chaosmonkey report --format html --open
```

### Example Output

**Disk I/O Chart:**
```
Disk I/O Over Time
┌─────────────────────────────────────────┐
│ Read (MB)  ━━━  Write (MB) ━━━         │
│ 500MB ┤                                 │
│       ┤      ╱─────╲                    │
│ 250MB ┤    ╱         ╲                  │
│       ┤  ╱             ╲                │
│ 100MB ┼╭─╯               ╰─╮            │
│       └──────────────────────           │
│       Before→During→After                │
└─────────────────────────────────────────┘
```

**Summary Card:**
```
┌──────────────────────────────────────┐
│ 💿 Disk I/O Metrics                  │
├──────────────────────────────────────┤
│ Before Read       │ 100.00 MB        │
│ Peak Read         │ 480.00 MB        │
│ Before Write      │ 50.00 MB         │
│ Peak Write        │ 460.00 MB        │
│ Total I/O Increase│ +790.00 MB       │
│ Read Ops          │ 1000 → 1100      │
│ Write Ops         │ 500 → 550        │
└──────────────────────────────────────┘
```

## Files Modified

### 1. `src/chaosmonkey/core/metrics.py`
**Lines Modified:** ~60 lines added

**Changes:**
- Added `disk` dictionary to metrics structure
- Extract device stats from Nomad API
- Aggregate read/write stats across tasks
- Added disk I/O comparison in `compare_metrics()`
- Track peak read/write during chaos

### 2. `src/chaosmonkey/core/metrics_report.py`
**Lines Modified:** ~150 lines added

**Changes:**
- Added disk I/O chart generation (dual-line)
- Added disk I/O summary card
- Updated `_prepare_metrics_timeline()` for disk data
- Converted bytes to MB for visualization
- Added disk to summary data structure

### 3. `examples/generate_html_report.py`
**Lines Modified:** ~100 lines updated

**Changes:**
- Added sample disk I/O data to demo
- Included disk metrics in before/during/after
- Added disk analysis to sample output
- Shows realistic I/O patterns

## Chart Configuration

### Disk I/O Chart Settings

```javascript
{
  type: 'line',
  datasets: [
    {
      label: 'Read (MB)',
      borderColor: 'rgb(16, 185, 129)',      // Green
      backgroundColor: 'rgba(16, 185, 129, 0.1)',
      borderWidth: 3,
      tension: 0.4,                           // Smooth curves
    },
    {
      label: 'Write (MB)',
      borderColor: 'rgb(245, 158, 11)',       // Orange
      backgroundColor: 'rgba(245, 158, 11, 0.1)',
      borderWidth: 3,
      tension: 0.4,
    }
  ],
  options: {
    responsive: true,
    maintainAspectRatio: false,
    // ... tooltips, scales, etc.
  }
}
```

## Data Source

### Nomad API

Disk I/O data comes from Nomad's allocation stats:

```
GET /v1/client/allocation/{alloc_id}/stats
```

**Response Structure:**
```json
{
  "Tasks": {
    "task-name": {
      "ResourceUsage": {
        "DeviceStats": [
          {
            "ReadStats": {
              "BytesTransferred": 1234567,
              "Ops": 100
            },
            "WriteStats": {
              "BytesTransferred": 9876543,
              "Ops": 50
            }
          }
        ]
      }
    }
  }
}
```

## Example Scenarios

### 1. Disk I/O Hogging Experiment

```bash
chaosmonkey execute \
  --chaos-type disk-io \
  --target-id my-allocation \
  --duration 60 \
  --metrics-duration 60 \
  --metrics-interval 5
```

**Expected Results:**
- Read/Write bytes spike during experiment
- Clear visualization in HTML chart
- Returns to baseline after experiment
- Operations count increases proportionally

### 2. Database Load Test

```bash
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id database-alloc \
  --metrics-interval 2
```

**Observe:**
- Disk writes may increase with CPU load
- Read operations for cache misses
- I/O patterns correlated with CPU spikes

### 3. Log-Heavy Application

```bash
chaosmonkey execute \
  --chaos-type memory-hog \
  --target-id logging-service
```

**Monitor:**
- Write operations from logging
- Minimal read operations
- Steady increase in write bytes

## Benefits

### 1. Complete Resource Picture
- **Before**: Only CPU + Memory
- **After**: CPU + Memory + Disk I/O
- **Result**: Full system resource visibility

### 2. Identify I/O Bottlenecks
- See if chaos causes disk saturation
- Correlate I/O with CPU/memory usage
- Identify unexpected I/O patterns

### 3. Validate Recovery
- Ensure I/O returns to normal
- Check for I/O leaks
- Verify cleanup effectiveness

### 4. Performance Analysis
- Compare I/O across experiments
- Identify high-I/O operations
- Optimize based on patterns

## Chart Interactions

### Hover Tooltips
- Hover over any point for exact values
- Shows timestamp and MB value
- Separate tooltips for read/write

### Zoom and Pan
- Click and drag to zoom
- Double-click to reset
- Pan across timeline

### Legend Toggle
- Click legend to hide/show lines
- Useful for focusing on read or write

## Performance Considerations

### Data Volume
- Each snapshot adds ~200 bytes (disk data)
- 12 snapshots (60s @ 5s) = ~2.4 KB
- Minimal overhead on report size

### API Calls
- Same Nomad API calls as before
- Disk data included in allocation stats
- No additional API requests needed

### Chart Rendering
- Smooth rendering with Chart.js
- Hardware-accelerated
- No performance impact on browser

## Troubleshooting

### No Disk I/O Data

**Problem:** Chart shows but no data points

**Causes:**
1. Nomad version too old (needs DeviceStats support)
2. Target has no disk I/O
3. Task doesn't report device stats

**Solution:**
- Check Nomad version (≥ 1.0.0 recommended)
- Verify allocation has file I/O
- Check Nomad client logs

### All Zeros

**Problem:** Disk metrics show 0 MB

**Causes:**
1. Very low I/O (< 1 MB)
2. Metrics collection too fast
3. Device stats not available

**Solution:**
- Increase metrics interval
- Run longer experiments
- Check if allocation actually performs I/O

### Chart Not Showing

**Problem:** CPU and Memory charts work, disk doesn't

**Solution:**
1. Check browser console for errors
2. Verify disk data in JSON report
3. Regenerate HTML report
4. Clear browser cache

## Future Enhancements

Planned improvements:

- [ ] **I/O Rate** - Bytes/second instead of cumulative
- [ ] **IOPS Tracking** - Operations per second
- [ ] **Device Breakdown** - Per-disk metrics
- [ ] **Read/Write Ratio** - Pie chart of read vs write
- [ ] **Latency Tracking** - I/O operation latency
- [ ] **Bandwidth Limits** - Show if hitting disk limits
- [ ] **Historical Trends** - Compare I/O across runs
- [ ] **Alerts** - Notify on unusual I/O patterns

## Comparison with Other Metrics

| Metric | Collection | Visualization | Analysis |
|--------|-----------|---------------|----------|
| **CPU** | ✅ % usage | ✅ Line chart | ✅ Peak + Recovery |
| **Memory** | ✅ Bytes | ✅ Line chart | ✅ Peak + Recovery |
| **Disk I/O** | ✅ Read/Write bytes | ✅ Dual-line chart | ✅ Peak + Ops |
| **Status** | ✅ State | ✅ Summary card | ✅ Stability |

## See Also

- [Metrics Collection Guide](METRICS_COLLECTION.md)
- [HTML Visualization Guide](HTML_METRICS_VISUALIZATION.md)
- [Metrics Quick Start](METRICS_QUICKSTART.md)
- [Architecture Documentation](ARCHITECTURE_AND_IMPLEMENTATION.md)

---

## Quick Test

Try the demo to see disk I/O visualization:

```bash
# Generate sample report with disk I/O
python examples/generate_html_report.py

# Open the HTML report
open reports/run-demo-sample.html
```

**You should see:**
- ✅ Three charts (CPU, Memory, Disk I/O)
- ✅ Four summary cards (CPU, Memory, Disk I/O, Status)
- ✅ Interactive tooltips on all charts
- ✅ Beautiful gradient design

---

**Disk I/O metrics are now fully integrated! 📊💿✨**
