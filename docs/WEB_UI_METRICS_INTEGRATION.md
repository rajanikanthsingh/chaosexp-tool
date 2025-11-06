# Web UI Metrics Integration

## Overview

The ChaosMonkey Web UI now automatically collects and displays metrics for all chaos experiments executed through the browser interface.

## What's New

### Automatic Metrics Collection ✅

When you execute a chaos experiment from the Web UI:
- **Metrics are collected by default** - No extra configuration needed
- **Before/During/After snapshots** captured automatically
- **Interactive HTML reports** with Chart.js visualizations
- **Real-time progress** shown in execution output

### Default Metrics Settings

```javascript
{
  collect_metrics: true,      // ✅ Always enabled for Web UI
  metrics_duration: 60,        // 60 seconds of continuous monitoring
  metrics_interval: 5          // Collect snapshot every 5 seconds
}
```

## User Experience

### 1. Execute Chaos Experiment

**From Dashboard:**
1. Select a target (node, allocation, job, or service)
2. Click "Execute Chaos" button
3. Choose chaos type (cpu-hog, memory-hog, etc.)
4. Optionally check "Dry Run" for simulation

**Metrics Collection Happens Automatically:**
```
📊 Collecting baseline metrics...
🔥 Executing chaos experiment...
📊 Collecting metrics during chaos (60s, every 5s)...
📊 Collecting post-chaos metrics...
✅ Experiment completed!
📄 Reports generated (JSON, Markdown, HTML)
```

### 2. View Interactive Reports

**Reports Tab:**
- Lists all chaos experiments with metrics
- Click "View" button to see full report
- Three tabs available:
  - **JSON**: Raw data structure
  - **Markdown**: Text summary
  - **HTML**: Interactive charts 📊

**HTML Report Features:**
- ✅ CPU Usage Chart (line chart with gradient)
- ✅ Memory Usage Chart (dynamic MB scale)
- ✅ Disk I/O Chart (read/write dual-line)
- ✅ Combined Metrics View (CPU + Memory)
- ✅ Summary Cards (recovery status)
- ✅ Interactive tooltips on hover
- ✅ Responsive design

### 3. Modal View

When you click "View" on a report:
```
┌─────────────────────────────────────────────────┐
│  Report: run-abc123              [X]            │
├─────────────────────────────────────────────────┤
│                                                 │
│  [ JSON ] [ Markdown ] [ HTML ]                 │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │                                           │  │
│  │   📊 Metrics Timeline                     │  │
│  │   [Interactive Charts Displayed]          │  │
│  │                                           │  │
│  │   • CPU Usage Over Time                   │  │
│  │   • Memory Usage Over Time                │  │
│  │   • Disk I/O Over Time                    │  │
│  │   • Combined Metrics                      │  │
│  │                                           │  │
│  │   📊 Summary Cards                        │  │
│  │   [CPU] [Memory] [Disk] [Status]         │  │
│  │                                           │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  [ Download JSON ] [ Download HTML ]            │
│  [ View Full Report in New Tab ]                │
└─────────────────────────────────────────────────┘
```

## Technical Implementation

### Frontend (app.js)

**Updated `executeChaos()` function:**
```javascript
async function executeChaos(chaosType, targetId, dryRun) {
    const formData = {
        chaos_type: chaosType,
        target_id: targetId,
        dry_run: dryRun,
        // ✅ NEW: Metrics enabled by default
        collect_metrics: true,
        metrics_duration: 60,
        metrics_interval: 5
    };
    
    // POST to /api/execute endpoint
    const response = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    });
    
    // Display results with metrics info
    displayExecutionResult(await response.json());
}
```

### Backend (app.py)

**Updated `/api/execute` endpoint:**
```python
@app.route("/api/execute", methods=["POST"])
def execute_chaos():
    data = request.json
    cmd = ["chaosmonkey", "execute"]
    
    # ... existing parameters ...
    
    # ✅ NEW: Metrics collection support
    if data.get("collect_metrics") is False:
        cmd.append("--no-metrics")
    
    if data.get("metrics_duration"):
        cmd.extend(["--metrics-duration", str(data["metrics_duration"])])
    
    if data.get("metrics_interval"):
        cmd.extend(["--metrics-interval", str(data["metrics_interval"])])
    
    result = run_cli_command(cmd)
    return jsonify(result)
```

### Report Viewing

**HTML Report Display:**
```javascript
async function showReport(runId) {
    // Load HTML report
    const htmlResponse = await fetch(`/api/reports/${runId}?format=html`);
    const htmlData = await htmlResponse.json();
    
    // ✅ Render HTML with embedded Chart.js visualizations
    document.getElementById('report-html-content').innerHTML = htmlData.content;
    
    // Charts automatically initialize via Chart.js in HTML
    modal.show();
}
```

## API Endpoints

### Execute Chaos with Metrics

**Endpoint:** `POST /api/execute`

**Request Body:**
```json
{
  "chaos_type": "cpu-hog",
  "target_id": "node-abc123",
  "dry_run": false,
  "collect_metrics": true,        // ✅ Default: true
  "metrics_duration": 60,          // Optional: default 60
  "metrics_interval": 5            // Optional: default 5
}
```

**Response:**
```json
{
  "success": true,
  "output": "... chaos execution output ...",
  "run_id": "run-abc123"
}
```

### Get HTML Report

**Endpoint:** `GET /api/reports/<run_id>/html`

**Response:** Full HTML page with embedded Chart.js charts

**Example:**
```bash
curl http://localhost:5001/api/reports/run-abc123/html
# Returns: Complete HTML document with interactive charts
```

### Get Report Data

**Endpoint:** `GET /api/reports/<run_id>?format=<json|markdown|html>`

**JSON Response:**
```json
{
  "experiment": { ... },
  "result": { ... },
  "metrics": {
    "before": {
      "timestamp": "2025-10-10T...",
      "cpu": { "percent": 15.5 },
      "memory": { "usage": 536870912 },
      "disk": { "read_bytes": 104857600, "write_bytes": 52428800 }
    },
    "during": [ ... 12 snapshots ... ],
    "after": { ... },
    "analysis": {
      "cpu": { "recovered": true },
      "memory": { "recovered": true },
      "disk": { ... }
    }
  }
}
```

## Customization Options

### Disable Metrics (Advanced)

If you need to disable metrics for specific experiments:

```javascript
// In app.js, modify executeChaos() call
const formData = {
    chaos_type: chaosType,
    target_id: targetId,
    dry_run: dryRun,
    collect_metrics: false  // ❌ Disable metrics
};
```

### Adjust Collection Duration

For longer experiments:

```javascript
const formData = {
    chaos_type: chaosType,
    target_id: targetId,
    dry_run: dryRun,
    collect_metrics: true,
    metrics_duration: 120,   // 2 minutes instead of 60s
    metrics_interval: 10     // 10s intervals instead of 5s
};
```

### Custom Metrics UI Controls

To add UI controls for metrics settings, update `index.html`:

```html
<!-- Add to chaos execution modal -->
<div class="form-group">
    <label>Metrics Collection</label>
    <input type="checkbox" id="collect-metrics" checked>
    <label for="collect-metrics">Enable metrics collection</label>
</div>

<div class="form-group">
    <label for="metrics-duration">Duration (seconds)</label>
    <input type="number" id="metrics-duration" value="60" min="10" max="300">
</div>

<div class="form-group">
    <label for="metrics-interval">Interval (seconds)</label>
    <input type="number" id="metrics-interval" value="5" min="1" max="30">
</div>
```

Then update JavaScript:

```javascript
async function executeChaos(chaosType, targetId, dryRun) {
    const formData = {
        chaos_type: chaosType,
        target_id: targetId,
        dry_run: dryRun,
        collect_metrics: document.getElementById('collect-metrics').checked,
        metrics_duration: parseInt(document.getElementById('metrics-duration').value),
        metrics_interval: parseInt(document.getElementById('metrics-interval').value)
    };
    // ... rest of function
}
```

## Troubleshooting

### Charts Not Showing

**Problem:** HTML report modal shows "Not available" or empty charts

**Solution:**
1. Check if metrics were collected:
   ```bash
   cat reports/run-<latest>.json | grep -A 5 '"metrics"'
   ```

2. Verify no errors in metrics collection:
   ```bash
   cat reports/run-<latest>.json | grep "error"
   ```

3. Ensure target type is supported (node, allocation, job, service)

### Slow Report Loading

**Problem:** Report takes long time to load in modal

**Solution:**
1. Reduce metrics duration: Change from 60s to 30s
2. Increase interval: Change from 5s to 10s
3. Use "View Full Report" button to open in new tab

### Missing Data Points

**Problem:** Charts show gaps or missing data

**Solution:**
1. Check if chaos duration < metrics duration
2. Verify target remained accessible during chaos
3. Check network connectivity to Nomad cluster

## Best Practices

### For Short Experiments (< 60s)
```javascript
metrics_duration: 30,    // Match or slightly exceed experiment duration
metrics_interval: 2      // Frequent sampling for short tests
```

### For Long Experiments (> 2 minutes)
```javascript
metrics_duration: 120,   // Extended monitoring
metrics_interval: 10     // Less frequent sampling
```

### For Production Testing
```javascript
collect_metrics: true,   // Always collect for post-mortem
metrics_duration: 60,    // Standard duration
metrics_interval: 5      // Balance detail vs overhead
```

### For Development/Testing
```javascript
collect_metrics: true,   // Keep enabled for debugging
metrics_duration: 30,    // Shorter for faster iteration
metrics_interval: 3      // More frequent for detail
```

## Files Modified

1. **`src/chaosmonkey/web/app.py`**
   - Lines 1805-1816: Added metrics parameters to `/api/execute` endpoint
   - Supports `collect_metrics`, `metrics_duration`, `metrics_interval`

2. **`src/chaosmonkey/web/static/app.js`**
   - Lines 2139-2149: Updated `executeChaos()` to include metrics by default
   - Automatically sends metrics parameters to backend

## Related Documentation

- [METRICS_COLLECTION.md](METRICS_COLLECTION.md) - Complete metrics guide
- [METRICS_QUICKSTART.md](METRICS_QUICKSTART.md) - Quick start guide
- [HTML_METRICS_VISUALIZATION.md](HTML_METRICS_VISUALIZATION.md) - Chart details
- [WEB_UI_GUIDE.md](WEB_UI_GUIDE.md) - Web UI user guide

## Summary

✅ **Metrics are now automatically collected for all Web UI chaos experiments**  
✅ **No configuration required - works out of the box**  
✅ **Beautiful interactive HTML reports with Chart.js visualizations**  
✅ **View reports directly in browser with modal or new tab**  
✅ **Supports all target types: nodes, allocations, jobs, services**  

**Start using it now:**
1. Open Web UI: `python3 run_web_ui.py`
2. Execute any chaos experiment
3. Click "View" on the report
4. See interactive charts! 📊✨

---

*Integration completed: October 10, 2025*  
*Feature: Web UI Metrics Collection*  
*Status: Production Ready* ✅
