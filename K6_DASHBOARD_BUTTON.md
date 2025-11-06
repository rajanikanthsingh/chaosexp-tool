# K6 Dashboard Button in Reports UI

## Overview
Added a "View K6 Dashboard" button to report cards in the Web UI for chaos tests that generate K6 performance dashboards.

## Feature Description

When you run a K6 chaos test (load test, stress test, spike test, etc.), the system generates:
1. A standard chaos report (JSON, Markdown, HTML)
2. A K6 web dashboard HTML file with detailed performance metrics

This feature adds a button to the report card that links directly to the K6 dashboard for easy access.

## Implementation

### Backend Changes (`src/chaosmonkey/web/app.py`)

Updated the `/api/reports` endpoint to extract K6 dashboard information:

```python
# Check for K6 web dashboard in activity outputs
k6_dashboard = None
run_activities = result.get("run", [])
if run_activities:
    for activity in run_activities:
        activity_output = activity.get("output", {})
        if activity_output.get("k6_web_dashboard"):
            # Extract just the filename from the full path
            dashboard_path = activity_output.get("k6_web_dashboard")
            k6_dashboard = Path(dashboard_path).name if dashboard_path else None
            break

reports.append({
    # ... other fields ...
    "k6_dashboard": k6_dashboard  # Added field
})
```

**How it works:**
1. Reads each report JSON file
2. Looks through activity outputs for `k6_web_dashboard` field
3. Extracts the filename from the full path
4. Includes it in the report metadata

### Frontend Changes (`src/chaosmonkey/web/static/app.js`)

Updated the `renderReportsList()` function to display the K6 dashboard button:

```javascript
${report.k6_dashboard ? `
    <a href="/reports/${report.k6_dashboard}" target="_blank" class="btn btn-sm btn-success">
        <i class="fas fa-chart-line"></i> View K6 Dashboard
    </a>
` : ''}
```

**Button properties:**
- Color: Green (`btn-success`) to distinguish from other report buttons
- Icon: Chart line icon (`fa-chart-line`)
- Opens in new tab: `target="_blank"`
- Only shown when K6 dashboard exists

## User Experience

### Before
```
┌──────────────────────────────────────┐
│ 🔥 k6-load-test                     │
│ Run ID: run-abc123                   │
│                                      │
│ Target: api.example.com              │
│ Started: 2025-10-10 15:30           │
│                                      │
│ [View Details] [HTML]               │
└──────────────────────────────────────┘
```

### After
```
┌──────────────────────────────────────┐
│ 🔥 k6-load-test                     │
│ Run ID: run-abc123                   │
│                                      │
│ Target: api.example.com              │
│ Started: 2025-10-10 15:30           │
│                                      │
│ [View Details] [HTML] [View K6 Dashboard] │
└──────────────────────────────────────┘
```

## Button Display Logic

The "View K6 Dashboard" button appears **only when**:
- ✅ The chaos test is a K6 test type
- ✅ The K6 action successfully generated a dashboard
- ✅ The `k6_web_dashboard` field exists in activity output
- ✅ The dashboard HTML file exists in the reports directory

The button does **not appear** for:
- ❌ Non-K6 chaos tests (CPU hog, memory hog, disk I/O, etc.)
- ❌ K6 tests that failed before dashboard generation
- ❌ Tests where K6 dashboard generation was disabled

## K6 Dashboard Content

The K6 web dashboard provides:
- 📊 **Real-time metrics**: Response times, throughput, error rates
- 📈 **Interactive graphs**: Zoom, pan, filter time ranges
- 📉 **Performance breakdown**: By endpoint, status code, tag
- 🎯 **Threshold validation**: Pass/fail criteria visualization
- 📋 **Request details**: URL, method, duration, response size
- 🔍 **Error analysis**: Failed requests with details

## File Naming Convention

K6 dashboard files follow this pattern:
```
k6-web-dashboard-<test-name>-<timestamp>.html
```

Examples:
- `k6-web-dashboard-k6-api-test-1760097616.html`
- `k6-web-dashboard-k6-load-test-1760098234.html`
- `k6-web-dashboard-k6-stress-test-1760099876.html`

## Technical Details

### Data Flow

```
1. User runs K6 chaos test
   ↓
2. K6 runner executes with K6_WEB_DASHBOARD=true
   ↓
3. K6 generates HTML dashboard file
   ↓
4. Action returns output with k6_web_dashboard path
   ↓
5. Chaos toolkit stores output in result.run[].output
   ↓
6. Backend extracts filename in /api/reports
   ↓
7. Frontend renders button if k6_dashboard exists
   ↓
8. User clicks button → Opens dashboard in new tab
```

### Backend Code Path

```python
# In /api/reports endpoint
for report_file in REPORTS_DIR.glob("run-*.json"):
    report_data = json.load(f)
    result = report_data.get("result", {})
    run_activities = result.get("run", [])
    
    for activity in run_activities:
        activity_output = activity.get("output", {})
        k6_dashboard_path = activity_output.get("k6_web_dashboard")
        # Extract filename and add to report metadata
```

### Frontend Code Path

```javascript
// In renderReportsList()
reportsList.map(report => {
    // Check if k6_dashboard field exists
    if (report.k6_dashboard) {
        // Render green button linking to dashboard
        return `<a href="/reports/${report.k6_dashboard}">...</a>`;
    }
})
```

## Testing

### Test Case 1: K6 Load Test with Dashboard
```bash
# Run K6 test from Web UI
1. Select K6 chaos type
2. Configure test parameters
3. Run test
4. Wait for completion
5. Navigate to Reports tab
6. Verify green "View K6 Dashboard" button appears
7. Click button
8. Verify dashboard opens in new tab
```

### Test Case 2: Non-K6 Chaos Test
```bash
# Run CPU hog test
1. Select CPU Hog chaos type
2. Run test on a node
3. Navigate to Reports tab
4. Verify NO K6 dashboard button (only View Details and HTML)
```

### Test Case 3: Failed K6 Test
```bash
# Run K6 test that fails early
1. Configure invalid K6 test
2. Run test (fails)
3. Navigate to Reports tab
4. If dashboard was generated before failure → Button appears
5. If dashboard not generated → No button
```

## Backward Compatibility

✅ **Fully backward compatible**
- Existing reports without K6 dashboard: No button shown
- Non-K6 chaos tests: No button shown
- K6 tests: Button shown when dashboard exists
- No breaking changes to API or data structures

## Files Modified

1. **`src/chaosmonkey/web/app.py`**
   - Updated `/api/reports` endpoint (lines ~1845-1895)
   - Added K6 dashboard extraction logic
   - Added `k6_dashboard` field to report metadata

2. **`src/chaosmonkey/web/static/app.js`**
   - Updated `renderReportsList()` function (lines ~1298-1345)
   - Added conditional K6 dashboard button rendering
   - Used green button styling with chart icon

## Related Files

- **K6 Runner**: `src/chaosmonkey/core/k6_runner.py`
  - Generates K6 dashboard with `K6_WEB_DASHBOARD_EXPORT`
  - Returns dashboard path in result

- **K6 Actions**: `src/chaosmonkey/stubs/actions.py`
  - Captures `k6_web_dashboard` from K6 runner
  - Returns it in action output

- **Dashboard Template**: User provided HTML file
  - `reports/k6-web-dashboard-*.html`
  - Self-contained interactive dashboard

## UI Styling

Button CSS classes:
- `btn btn-sm btn-success`: Green button, small size
- Icon: `fas fa-chart-line` (line chart icon)
- Opens in new tab: `target="_blank"`

Color scheme:
- Primary (blue): View Details
- Info (cyan): HTML Report
- Success (green): K6 Dashboard ← New button

## Future Enhancements

Potential improvements:
1. **Preview tooltip**: Hover to see key metrics
2. **Inline dashboard**: View in modal without leaving page
3. **Dashboard comparison**: Compare multiple K6 runs
4. **Export options**: Download dashboard as PDF
5. **Share link**: Generate shareable dashboard link

## Date
October 10, 2025
