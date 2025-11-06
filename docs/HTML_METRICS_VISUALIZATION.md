# HTML Metrics Visualization Guide

## Overview

ChaosMonkey now generates beautiful, interactive HTML reports with real-time metrics visualization using Chart.js. These reports provide a comprehensive view of your chaos experiments with:

- 📊 **Interactive Line Charts** - CPU and memory usage over time
- 📈 **Combined Metrics View** - See CPU and memory on the same chart
- 🎨 **Professional Design** - Modern, responsive UI with gradient backgrounds
- 📱 **Mobile Friendly** - Responsive design works on all devices
- 🖨️ **Print Ready** - Optimized for printing and PDF export

## Features

### Automatic HTML Generation

HTML reports are **automatically generated** after every experiment that collects metrics:

```bash
chaosmonkey execute --chaos-type cpu-hog --target-id <alloc-id>
```

**Output:**
```
📄 Reports generated:
   - JSON: /path/to/reports/run-abc123.json
   - Markdown: /path/to/reports/run-abc123.md
   - HTML: /path/to/reports/run-abc123.html
```

### Three Chart Types

#### 1. CPU Usage Chart
- **Line chart** showing CPU percentage over time
- Red gradient fill for visual impact
- Tooltips showing exact values
- Y-axis from 0-100%

#### 2. Memory Usage Chart
- **Line chart** showing memory usage in MB
- Blue gradient fill
- Dynamic Y-axis based on usage
- Tooltips with MB values

#### 3. Combined Metrics View
- **Dual-axis chart** showing CPU and memory together
- Left Y-axis for CPU (%)
- Right Y-axis for Memory (MB)
- Easy correlation between metrics

### Metrics Summary Cards

Three interactive cards showing:

#### 🔥 CPU Metrics Card
- Before chaos percentage
- Peak during chaos
- After chaos percentage
- Change during chaos
- Recovery status badge

#### 💾 Memory Metrics Card
- Before chaos (MB)
- Peak during chaos (MB)
- After chaos (MB)
- Change during chaos (MB)
- Recovery status badge

#### 🚦 Status Stability Card
- Before status
- After status
- Stability indicator

## Usage

### View Latest Report

```bash
# Generate HTML report for latest run
chaosmonkey report --format html

# Open in browser automatically
chaosmonkey report --format html --open
```

### View Specific Report

```bash
# Generate HTML for specific run
chaosmonkey report run-abc123 --format html

# Open in browser
chaosmonkey report run-abc123 --format html --open
```

### Save Report to Custom Location

```bash
# Save HTML to specific path
chaosmonkey report --format html --output ~/my-report.html

# Open custom report
open ~/my-report.html
```

## CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--format html` | `-f html` | Generate HTML report with charts |
| `--open` | `-b` | Open HTML report in default browser |
| `--output` | `-o` | Save report to custom path |

## Example Workflow

### 1. Run Experiment with Metrics

```bash
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id my-allocation \
  --duration 60 \
  --metrics-duration 60 \
  --metrics-interval 5
```

### 2. View HTML Report

```bash
# Option 1: Open automatically
chaosmonkey report --format html --open

# Option 2: Get path and open manually
chaosmonkey report --format html
# Then: open /path/to/reports/run-abc123.html
```

### 3. Share Report

The HTML report is a **single file** with no external dependencies (except Chart.js CDN):

```bash
# Copy report
cp reports/run-abc123.html ~/shared-reports/

# Email or share the file
# Recipients can open directly in browser
```

## Report Sections

### 1. Header Section
- **Experiment title** with emoji
- **Chaos type** subtitle
- **Status badge** (completed/failed/aborted)
- Color-coded with gradient background

### 2. Experiment Information
- **Run ID** - Unique identifier
- **Target** - Target allocation/job/node
- **Chaos Type** - Type of chaos experiment
- **Status** - Execution status

### 3. Metrics Timeline (if available)
- **CPU Usage Chart** - Line chart over time
- **Memory Usage Chart** - Line chart over time
- **Combined View** - Dual-axis chart

### 4. Metrics Analysis
- **Three summary cards** with detailed metrics
- **Recovery badges** showing recovery status
- **Color-coded values** (green for good, red for issues)

### 5. Footer
- **Generation timestamp**
- **Run ID reference**
- **ChaosMonkey branding**

## Chart Features

### Interactive Tooltips
- Hover over any point to see exact values
- Formatted with units (%, MB)
- Dark background for readability

### Zoom and Pan
- Click and drag to zoom into specific time ranges
- Double-click to reset zoom
- Pan across the timeline

### Responsive Design
- Charts automatically resize with window
- Mobile-friendly touch interactions
- Maintains aspect ratio

### Print Optimization
- Charts render correctly when printing
- Clean layout without backgrounds
- Page breaks in appropriate places

## Customization

### Color Scheme

The report uses a professional color palette:

| Element | Color | Purpose |
|---------|-------|---------|
| Header | Purple gradient | Eye-catching header |
| CPU Chart | Red (#ef4444) | Critical resource |
| Memory Chart | Blue (#3b82f6) | Important resource |
| Success Badge | Green (#10b981) | Recovery success |
| Warning Badge | Yellow (#f59e0b) | Needs attention |

### Chart Configuration

Charts are configured with:
- **Smooth curves** (tension: 0.4)
- **Point highlights** on hover
- **Grid lines** for easy reading
- **Legend** at top
- **Responsive** sizing

## Technical Details

### Dependencies

The HTML report uses:
- **Chart.js 4.4.0** - From CDN (no local install needed)
- **Pure CSS** - No external CSS frameworks
- **Vanilla JavaScript** - No jQuery or other libraries

### Browser Support

Works in all modern browsers:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### File Size

- **HTML file**: ~50-100 KB (with metrics)
- **No images** or external assets
- **Single file** - easy to share

### Offline Viewing

Charts require internet for Chart.js CDN. For offline viewing:

1. Download Chart.js: https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
2. Save as `chart.js` in same directory
3. Update HTML to use local file:
   ```html
   <script src="./chart.js"></script>
   ```

## Example Screenshots

### CPU Usage Chart
```
┌─────────────────────────────────────────┐
│ CPU Usage Over Time                     │
├─────────────────────────────────────────┤
│ 100% ┤                                  │
│  80% ┤      ╭───────╮                   │
│  60% ┤    ╭─╯       ╰─╮                 │
│  40% ┤  ╭─╯           ╰─╮               │
│  20% ┤╭─╯               ╰─╮             │
│   0% ┴──────────────────────            │
│     Before→During→After                 │
└─────────────────────────────────────────┘
```

### Metrics Summary Card
```
┌─────────────────────────────────────┐
│ 🔥 CPU Metrics                      │
├─────────────────────────────────────┤
│ Before Chaos      │ 15.23%          │
│ Peak During Chaos │ 98.45%          │
│ After Chaos       │ 16.10%          │
│ Change During     │ +83.22%         │
│ Recovery Status   │ ✅ Recovered     │
└─────────────────────────────────────┘
```

## Troubleshooting

### Charts Not Displaying

**Problem:** Charts show as blank

**Solutions:**
1. Check internet connection (Chart.js needs CDN)
2. Verify no browser extensions blocking scripts
3. Check browser console for errors
4. Try different browser

### Report Shows "No Metrics"

**Problem:** HTML report says "No metrics data available"

**Causes:**
- Metrics collection disabled (`--no-metrics`)
- Dry-run mode active
- Metrics collection failed

**Solution:** Run experiment with metrics enabled:
```bash
chaosmonkey execute --chaos-type cpu-hog --target-id <id> --collect-metrics
```

### Charts Look Wrong

**Problem:** Charts are distorted or incorrectly sized

**Solution:**
- Clear browser cache
- Ensure window is fully loaded before viewing
- Try refreshing the page
- Check browser console for errors

### Can't Open in Browser

**Problem:** `--open` flag doesn't work

**Solutions:**
1. Manually open the file:
   ```bash
   open reports/run-abc123.html  # macOS
   xdg-open reports/run-abc123.html  # Linux
   start reports/run-abc123.html  # Windows
   ```

2. Get the full path:
   ```bash
   chaosmonkey report --format html | grep "View the report"
   ```

## Best Practices

### ✅ DO

- Use HTML format for visual analysis
- Open reports in browser for interactivity
- Share HTML reports with team members
- Archive important reports
- Use `--open` flag for quick viewing

### ❌ DON'T

- Don't edit HTML manually (regenerate instead)
- Don't rely on HTML for automation (use JSON)
- Don't assume offline viewing will work
- Don't forget to collect metrics

## Integration with CI/CD

### Archive Reports

```bash
# In your CI pipeline
chaosmonkey execute --chaos-type cpu-hog --target-id $TARGET_ID
chaosmonkey report --format html --output chaos-report-${BUILD_ID}.html

# Upload as artifact
# GitLab: artifacts: paths: [chaos-report-*.html]
# GitHub Actions: uses: actions/upload-artifact
# Jenkins: archiveArtifacts 'chaos-report-*.html'
```

### Email Reports

```bash
# Generate report
chaosmonkey report --format html --output /tmp/report.html

# Email with attachment
mail -s "Chaos Report" -a /tmp/report.html team@example.com < /dev/null
```

### Slack Notifications

```bash
# Generate report and get URL
REPORT_PATH=$(chaosmonkey report --format html | grep -oE '/.*\.html')

# Upload to file server
scp $REPORT_PATH server:/var/www/reports/

# Post to Slack
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Chaos report: https://reports.company.com/..."}' \
  $SLACK_WEBHOOK_URL
```

## Future Enhancements

Planned improvements for HTML reports:

- [ ] Dark mode toggle
- [ ] Export charts as images
- [ ] Compare multiple experiments
- [ ] Real-time metrics streaming
- [ ] Custom chart types (bar, pie)
- [ ] Metric thresholds/SLOs
- [ ] Annotations on timeline
- [ ] Zoom controls
- [ ] Download data as CSV

## See Also

- [Metrics Collection Guide](METRICS_COLLECTION.md)
- [Metrics Quick Start](METRICS_QUICKSTART.md)
- [Reports Guide](REPORTS_GUIDE.md)
- [CLI Reference](../README.md)

---

**Happy Visualizing! 📊✨**
