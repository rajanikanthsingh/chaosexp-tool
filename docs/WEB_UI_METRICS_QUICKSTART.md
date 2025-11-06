# Web UI Metrics - Quick Summary

## ✅ What Was Done

Integrated automatic metrics collection into the ChaosMonkey Web UI.

## 🎯 Changes Made

### 1. Backend (app.py)
Added metrics support to `/api/execute` endpoint:
```python
# Support for metrics collection (enabled by default)
if data.get("collect_metrics") is False:
    cmd.append("--no-metrics")

if data.get("metrics_duration"):
    cmd.extend(["--metrics-duration", str(data["metrics_duration"])])

if data.get("metrics_interval"):
    cmd.extend(["--metrics-interval", str(data["metrics_interval"])])
```

### 2. Frontend (app.js)
Updated `executeChaos()` function to send metrics parameters:
```javascript
const formData = {
    chaos_type: chaosType,
    target_id: targetId,
    dry_run: dryRun,
    // ✅ NEW: Metrics enabled by default
    collect_metrics: true,
    metrics_duration: 60,   // 60 seconds
    metrics_interval: 5     // Every 5 seconds
};
```

## 📊 User Experience

### Before
- Execute chaos from Web UI
- ❌ No metrics collected
- ❌ Reports had no data
- ❌ Empty graphs

### After ✅
- Execute chaos from Web UI
- ✅ **Metrics automatically collected**
- ✅ **Reports show interactive charts**
- ✅ **CPU, Memory, Disk I/O visualized**
- ✅ **Before/During/After analysis**

## 🚀 How to Use

1. **Start Web UI:**
   ```bash
   python3 run_web_ui.py
   ```

2. **Execute Chaos:**
   - Open browser: http://localhost:5001
   - Select a target
   - Click "Execute Chaos"
   - Choose chaos type

3. **View Metrics:**
   - Go to "Reports" tab
   - Click "View" on any report
   - Click "HTML" tab
   - See beautiful interactive charts! 📊

## 📈 What You'll See

**Interactive Charts:**
- 📊 CPU Usage Over Time (red line chart)
- 📊 Memory Usage Over Time (blue line chart)
- 📊 Disk I/O Over Time (green read, orange write)
- 📊 Combined Metrics View (dual-axis)

**Summary Cards:**
- 🔥 CPU: Before/Peak/After with recovery status
- 💾 Memory: Before/Peak/After with recovery status
- 💿 Disk: Read/Write bytes and operations
- ✅ Status: Target stability check

## ⚙️ Default Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| `collect_metrics` | `true` | Always enabled for Web UI |
| `metrics_duration` | `60` | 60 seconds of monitoring |
| `metrics_interval` | `5` | Snapshot every 5 seconds |

## 🔧 Customization (Optional)

To change defaults, edit `app.js`:

```javascript
// For shorter experiments
metrics_duration: 30,
metrics_interval: 2

// For longer experiments
metrics_duration: 120,
metrics_interval: 10

// To disable metrics
collect_metrics: false
```

## 📁 Files Modified

1. `src/chaosmonkey/web/app.py` (Lines 1805-1816)
   - Added metrics parameters to execute endpoint

2. `src/chaosmonkey/web/static/app.js` (Lines 2139-2149)
   - Updated executeChaos() to include metrics

## ✅ Testing

```bash
# 1. Start Web UI
python3 run_web_ui.py

# 2. Execute chaos from browser
# - Select any target
# - Choose "cpu-hog" or "memory-hog"
# - Click Execute

# 3. View report
# - Go to Reports tab
# - Click "View"
# - Switch to "HTML" tab
# - Verify charts display with data

# 4. Check JSON report
cat reports/run-<latest>.json | jq .metrics
# Should show: before, during, after, analysis
```

## 🎉 Benefits

✅ **Zero configuration** - Works automatically  
✅ **Full metrics collection** - CPU, Memory, Disk I/O  
✅ **Beautiful visualizations** - Interactive Chart.js graphs  
✅ **Recovery validation** - Automatic analysis  
✅ **Easy viewing** - Right in the browser  
✅ **Professional reports** - Share with stakeholders  

## 📚 Documentation

- [WEB_UI_METRICS_INTEGRATION.md](WEB_UI_METRICS_INTEGRATION.md) - Complete guide
- [METRICS_COLLECTION.md](METRICS_COLLECTION.md) - Metrics details
- [HTML_METRICS_VISUALIZATION.md](HTML_METRICS_VISUALIZATION.md) - Charts info

## 🎯 Summary

**Metrics collection is now automatic for all Web UI chaos experiments!**

No extra steps needed - just execute chaos from the browser and view beautiful interactive reports with full metrics analysis. 🚀📊✨

---

*Feature: Web UI Metrics Integration*  
*Date: October 10, 2025*  
*Status: Production Ready* ✅
