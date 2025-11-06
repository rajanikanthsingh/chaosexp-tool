# 🚀 Quick Test Guide - Metrics & Graphs Fix

## What Was Fixed

The critical bug preventing metrics collection from the Web UI has been fixed:

### The Problem
- ✅ Before metrics: Used Prometheus (worked)
- ❌ During metrics: Used old Nomad collector (failed/incomplete)
- ✅ After metrics: Used Prometheus (worked)
- **Result**: No complete metrics → No graphs in reports

### The Solution
Now ALL metrics (before/during/after) use Prometheus for node targets!

## 🧪 Test It Now

### Step 1: Run the Verification Script (Optional)
```bash
cd /Users/inderdeep.sidhu/PycharmProjects/chaosmonkey
python test_metrics_collection.py
```

This will verify Prometheus connection and metrics format.

### Step 2: Start the Web UI
```bash
python run_web_ui.py
```

### Step 3: Open Browser
Navigate to: http://localhost:5555

### Step 4: Run a Chaos Experiment
1. Select **"CPU Hog"** (or any chaos type)
2. **IMPORTANT**: Select a **node** as target (e.g., `hostname`)
   - NOT a job or service - must be a node!
3. Click **"Run Chaos Experiment"**
4. Wait for completion (~2-3 minutes)

### Step 5: Check the Report

#### In Terminal Output:
Look for these lines:
```
📊 Collecting baseline metrics for msepg01p1...
   CPU usage: 12.56%
   Memory usage: 65.57%
   ...
📊 Collecting metrics during chaos (duration: 60s, interval: 5s)...
   [Multiple metric collections every 5 seconds]
📊 Collecting post-chaos metrics for msepg01p1...
   ...
📄 Reports generated:
   - JSON: reports/run-XXXXXXXX.json
   - HTML: reports/run-XXXXXXXX.html
```

#### Check Report Has Metrics:
```bash
# Find the latest report
ls -lt reports/run-*.json | head -1

# Check it has metrics
cat reports/run-XXXXXXXX.json | python -c "import sys, json; data=json.load(sys.stdin); print('✅ Has metrics!' if 'metrics' in data else '❌ No metrics')"
```

#### Check HTML Has Graphs:
```bash
# Count Chart.js graphs
grep -c "new Chart" reports/run-XXXXXXXX.html

# Should output: 3 or 4 (number of graphs)
```

### Step 6: Open HTML Report in Browser
```bash
open reports/run-XXXXXXXX.html
```

## ✅ Expected Results

### You Should See:

1. **In the HTML report**:
   - Section with graphs (look for "Metrics" or "Analysis")
   - 3-4 interactive charts showing:
     - **CPU Usage Timeline** (line going up during chaos, down after)
     - **Memory Usage Timeline** (showing memory consumption)
     - **Disk I/O Read** (showing read throughput)
     - **Disk I/O Write** (showing write throughput)
   
2. **In the JSON report** (`reports/run-XXXXXXXX.json`):
   ```json
   {
     "experiment": {...},
     "result": {...},
     "metrics": {
       "before": {
         "cpu": {"percent": 12.5},
         "memory": {"usage": 5287313408, ...},
         "disk": {...}
       },
       "during": [
         {"cpu": {"percent": 45.2}, "label": "during_0", ...},
         {"cpu": {"percent": 67.8}, "label": "during_1", ...},
         ...
       ],
       "after": {
         "cpu": {"percent": 13.1},
         ...
       },
       "analysis": {...}
     }
   }
   ```

## 🐛 If It Doesn't Work

### Debug Checklist:

1. **Verify Prometheus is running**:
   ```bash
   curl -s "http://prometheus/api/v1/query?query=up" | python -m json.tool | head -20
   ```
   Should see: `"status": "success"`

2. **Check node has metrics in Prometheus**:
   ```bash
   curl -s "http://prometheus/api/v1/query?query=up{job=\"node_exporter\",instance=~\"msepg01p1.*\"}" | python -m json.tool
   ```
   Should return results with the node

3. **Check terminal logs** when running experiment:
   Look for ERROR or WARNING messages about metrics collection

4. **Verify you selected a NODE target**:
   - ✅ Node: `hostname` (UUID or FQDN)
   - ❌ Job: `my-service`
   - ❌ Service: `my-service.my-group`
   
   Only nodes have Prometheus metrics!

## 📊 What the Graphs Show

- **Before**: Baseline metrics before chaos starts
- **During**: Multiple data points collected every 5 seconds during chaos
- **After**: Recovery metrics after chaos ends

The graphs should show:
- CPU spike during chaos (for CPU Hog)
- Memory increase during chaos (for Memory Hog)
- Disk I/O spike during chaos (for Disk I/O stress)

## 🎉 Success Indicators

✅ Terminal shows "Collecting metrics" messages  
✅ JSON report has `"metrics"` field with before/during/after  
✅ HTML report has Chart.js `<script>` tags  
✅ Opening HTML shows interactive graphs  
✅ Graphs have real data (not all zeros)  
✅ During phase has multiple data points (12 points for 60s @ 5s intervals)

## 📝 Files Changed

1. `src/chaosmonkey/core/orchestrator.py` - Fixed continuous metrics collection
2. `src/chaosmonkey/core/prometheus_metrics.py` - Added format transformation

## 🆘 Need Help?

If metrics still don't appear:

1. Check `METRICS_FIX_COMPLETE.md` for detailed troubleshooting
2. Run `test_metrics_collection.py` to verify Prometheus works
3. Look for error messages in terminal output
4. Verify node name matches Prometheus instance names

---

**Ready to test?** Just run: `python run_web_ui.py` and try it! 🚀
