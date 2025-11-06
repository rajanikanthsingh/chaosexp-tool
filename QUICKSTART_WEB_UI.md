# ChaosMonkey Web UI - Quick Start Guide

## 🚀 Start the Web UI

### Method 1: Using the Python Script (Recommended)

```bash
cd /Users/kunalsing.thakur/github/hackathon/chaosmonkey
python3 run_web_ui.py
```

### Method 2: Using Python Module

```bash
cd /Users/kunalsing.thakur/github/hackathon/chaosmonkey
python3 -m chaosmonkey.web.app
```

Note: The Web UI currently invokes the `chaosmonkey` CLI for some operations (execute, list jobs, discover services). To avoid "command not found" or environment mismatches, run the Web UI in the same Python environment where `chaosmonkey` is installed. A safer invocation is:

```bash
# run the web UI using the same Python interpreter that has the package installed
python3 -c "import sys; import runpy; runpy.run_module('chaosmonkey.web.app', run_name='__main__')"
```

Or set the CLI invocation to use the current interpreter (recommended change):

```python
# Example change in run_cli_command:
import sys
cmd = [sys.executable, '-m', 'chaosmonkey', 'execute', ...]
```

### Method 3: Direct Execution

```bash
cd /Users/kunalsing.thakur/github/hackathon/chaosmonkey/src/chaosmonkey/web
python3 app.py
```

## 📋 Prerequisites

### 1. Install Required Dependencies

```bash
cd /Users/kunalsing.thakur/github/hackathon/chaosmonkey
pip install flask flask-cors requests python-nomad
```

### 2. Set Environment Variables

```bash
export NOMAD_ADDR=http://nomad-dev-fqdn:4646
export NOMAD_TOKEN=your-nomad-token-here
export NOMAD_NAMESPACE=default
```

## 🌐 Access the Dashboard

Once started, open your browser:

```
http://localhost:8080
```

## 🐛 Fixed Issues

### ✅ Issue 1: Total Nodes Loading Slow
**Fixed**: Changed from CLI parsing to direct Nomad API calls
- Now uses `python-nomad` library directly
- Much faster response time
- No CLI subprocess overhead

### ✅ Issue 2: Total Nodes Not Clickable
**Fixed**: The stats are now informational displays
- Shows total nodes count
- Shows ready nodes count
- Shows drained nodes count
- Click on "Nodes" tab in navigation to see full node list

### ✅ Issue 3: Available Chaos Types Showing Blank
**Fixed**: Improved chaos type loading
- Reads templates from `src/chaosmonkey/experiments/templates/`
- Displays icons and descriptions
- Click on chaos type cards to navigate to execute page

### ✅ Issue 4: Drain Not Working Due to Invalid Hex Codes
**Fixed**: Complete node drain implementation
- Now passes full node ID (not truncated with `...`)
- Uses Nomad HTTP API directly
- Proper payload format with `DrainSpec`
- Handles node ID cleaning automatically
- Better error messages

### ✅ Issue 5: No Chaos Types in Execute Tab
**Fixed**: Execute chaos tab now shows:
- All available chaos types in dropdown
- Descriptions for each type
- Proper icons
- Target ID input
- Dry-run checkbox

## 📊 Dashboard Features

### Dashboard Tab
- **Total Nodes**: Click "Nodes" tab to see details
- **Drained Nodes**: Shows count of nodes in drain mode
- **Total Experiments**: Number of chaos experiments run
- **Success Rate**: Percentage of successful experiments
- **Recent Experiments**: Last 5 experiments with status
- **Available Chaos Types**: Click cards to execute chaos

### Nodes Tab
- **Real-time node status**: Updated from Nomad API
- **Node details**: Name, ID, datacenter, resources
- **Drain/Enable buttons**: One-click node operations
- **Full node IDs**: Hover over truncated IDs to see full ID
- **Loading indicators**: Shows spinner during operations

### Execute Chaos Tab
- **Chaos Type Dropdown**: All available types
  - 🔥 CPU Hog
  - 💾 Memory Hog
  - 🐌 Network Latency
  - 📦 Packet Loss
  - 💀 Host Down
  - 💿 Disk I/O
- **Target ID**: Optional service/node identifier
- **Dry Run**: Test mode without actual execution
- **Execution Output**: Real-time results display

### Reports Tab
- **All experiment reports**: Listed newest first
- **Status badges**: Visual status indicators
- **View Details**: Opens multi-format report viewer
  - JSON: Raw data
  - Markdown: Human-readable
  - HTML: Formatted report
- **Direct Links**: Open HTML reports in new tab

## 🔧 Troubleshooting

### Problem: "Command not found: python"
**Solution**: Use `python3` instead
```bash
python3 run_web_ui.py
```

### Problem: "Module not found: flask"
**Solution**: Install dependencies
```bash
pip install flask flask-cors requests
```

### Problem: "No nodes showing"
**Solution**: Check Nomad connection
```bash
# Verify environment variables
echo $NOMAD_ADDR
echo $NOMAD_TOKEN

# Test connection
curl -H "X-Nomad-Token: $NOMAD_TOKEN" $NOMAD_ADDR/v1/nodes
```

### Problem: "403 Permission denied" when draining
**Solution**: Your Nomad token needs elevated permissions

Add this policy:
```hcl
node {
  policy = "write"
}
```

### Problem: "Chaos types not showing in Execute tab"
**Solution**: 
1. Check that templates exist in `src/chaosmonkey/experiments/templates/`
2. Verify files:
   - `generic_cpu_hog.json`
   - `generic_memory_hog.json`
   - `generic_network_latency.json`
   - `generic_packet_loss.json`
   - `generic_host_down.json`
   - `generic_disk_io.json`

### Problem: "Node drain fails with invalid ID"
**Solution**: Fixed in latest code
- Now automatically cleans node IDs
- Handles truncated IDs (`...`)
- Passes full ID to API

## 🎯 Usage Examples

### Example 1: View All Nodes

1. Click "Nodes" tab in navigation
2. Wait for nodes to load (should be fast now!)
3. See full list with status, resources, drain state

### Example 2: Drain a Node

1. Go to "Nodes" tab
2. Find the node you want to drain
3. Click red "Drain" button
4. Confirm the action
5. Watch the spinner while draining
6. Node will show "Drain: Yes" when complete

### Example 3: Execute CPU Hog Chaos

1. Go to "Execute Chaos" tab
2. Select "🔥 CPU Hog" from dropdown
3. Enter target service ID (e.g., `mobi-platform-account-service-job`)
4. Check "Dry Run" for testing
5. Click "Execute Chaos Experiment"
6. View output in the result section

### Example 4: View Experiment Reports

1. Go to "Reports" tab
2. Click "View Details" on any report
3. Switch between JSON/Markdown/HTML tabs
4. Or click "HTML" button to open in new tab

## 📝 Quick Reference

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/discover/clients` | GET | List all nodes |
| `/api/chaos-types` | GET | List chaos types |
| `/api/execute` | POST | Run chaos experiment |
| `/api/node/drain` | POST | Drain a node |
| `/api/node/eligibility` | POST | Enable/disable node |
| `/api/reports` | GET | List all reports |
| `/api/reports/{id}` | GET | Get specific report |

### Environment Variables

| Variable | Required | Example |
|----------|----------|---------|
| `NOMAD_ADDR` | Yes | `http://nomad-dev-fqdn:4646` |
| `NOMAD_TOKEN` | Yes | `your-token-here` |
| `NOMAD_NAMESPACE` | No | `default` |

### Keyboard Shortcuts

- `Ctrl+C` in terminal: Stop the web server
- `F5` in browser: Refresh dashboard
- `Ctrl+R` in browser: Reload page

## 🎨 UI Improvements Summary

1. ✅ **Faster Loading**: Direct API calls instead of CLI
2. ✅ **Better UX**: Loading spinners and progress indicators
3. ✅ **Working Drain**: Proper node ID handling
4. ✅ **Chaos Types**: All types visible and selectable
5. ✅ **Clear Feedback**: Success/error messages with details
6. ✅ **Responsive**: Works on desktop and tablet
7. ✅ **Professional**: Clean, modern Bootstrap design

## 🚦 Status Indicators

### Node Status Colors
- 🟢 **Green**: Ready and healthy
- 🔴 **Red**: Down or unavailable
- 🟡 **Yellow**: Initializing or maintenance

### Drain Status
- 🟢 **No**: Node is eligible for allocations
- 🔴 **Yes**: Node is draining or drained

### Experiment Status
- 🟢 **completed**: Experiment succeeded
- 🔴 **failed**: Experiment failed
- 🟡 **dry-run**: Simulation only

## 📚 Additional Documentation

- Full Guide: `docs/WEB_UI_GUIDE.md`
- Architecture: `docs/architecture.md`
- Node Drain: `docs/NODE_DRAIN.md`
- Reports: `docs/REPORTS_GUIDE.md`

## 💡 Pro Tips

1. **Start with Dry-Run**: Always test chaos experiments in dry-run mode first
2. **Monitor Before Chaos**: Open the Nodes tab before running experiments
3. **Check Reports**: Review experiment reports to understand impact
4. **Use Full Node IDs**: The UI now handles full IDs correctly
5. **Set Permissions**: Ensure your Nomad token has required permissions
6. **Browser Console**: Open DevTools (F12) to see detailed API calls

---

**Need Help?** Check the main documentation or examine the browser console for detailed error messages.
