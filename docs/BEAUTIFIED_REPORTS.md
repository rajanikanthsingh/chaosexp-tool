# 🎨 Beautified Reports Documentation

## Overview

The ChaosMonkey CLI now generates **beautiful, professional reports** in multiple formats with enhanced readability and visual appeal.

## Available Report Formats

### 1. 📄 Markdown Reports (Enhanced)

**Features:**
- ✅ Clean, structured layout with emojis
- ✅ Status badges with colored indicators
- ✅ Organized tables for configuration and results
- ✅ Highlighted recovery commands
- ✅ Timeline information (start/end/duration)
- ✅ Activity-specific output formatting

**Usage:**
```bash
# Generate markdown report (default)
chaosmonkey report run-026dc6aa

# Or explicitly specify format
chaosmonkey report run-026dc6aa --format markdown

# Save to file
chaosmonkey report run-026dc6aa -o my-report.md
```

**Example Output:**

```markdown
# 💥 Chaos Engineering Report

## 📋 Experiment Information

| Property | Value |
|----------|-------|
| **Run ID** | `run-026dc6aa` |
| **Chaos Type** | host-down, node-drain |
| **Target** | `mobi-platform-account-service-job` |
| **Status** | ✅ **COMPLETED** |
| **Started** | 2025-10-09 13:33:03 UTC |
| **Completed** | 2025-10-09 13:33:09 UTC |
| **Duration** | 6.18s |
```

### 2. 🌐 HTML Reports (NEW!)

**Features:**
- 🎨 Modern, responsive design with gradient backgrounds
- 🎯 Interactive tables with hover effects
- 📊 Visual status badges with color coding
- 📱 Mobile-friendly responsive layout
- 💫 Professional card-based layout
- 🖥️ Syntax-highlighted code blocks
- 🎭 Emoji icons for better visual hierarchy

**Usage:**
```bash
# Generate HTML report
chaosmonkey report run-026dc6aa --format html

# Save to custom location
chaosmonkey report run-026dc6aa --format html -o /path/to/report.html
```

**Visual Features:**

1. **Header Section**
   - Gradient purple background
   - Large title with chaos type
   - Status badge (green for success, red for failure)

2. **Information Cards**
   - Grid layout with rounded corners
   - Gradient backgrounds
   - Easy-to-scan key metrics
   - Color-coded left borders

3. **Configuration Tables**
   - Purple header bars
   - Hover effects on rows
   - Clean, professional styling
   - Responsive design

4. **Activity Cards**
   - White cards with soft shadows
   - Status badges (green/red)
   - Detailed output tables
   - Code blocks with dark theme

5. **Recovery Commands**
   - Dark terminal-style code blocks
   - Copy-friendly formatting
   - Highlighted with 🔧 emoji

6. **Summary Section**
   - Alert boxes (success/warning)
   - Platform information cards
   - Generated timestamp

**Opening HTML Reports:**

```bash
# Mac
open reports/run-026dc6aa.html

# Linux
xdg-open reports/run-026dc6aa.html

# Windows
start reports/run-026dc6aa.html
```

### 3. 📋 JSON Reports (Raw Data)

**Features:**
- Complete experiment data
- Machine-readable format
- Ideal for automation and analysis

**Usage:**
```bash
# Generate JSON report
chaosmonkey report run-026dc6aa --format json

# Pipe to jq for pretty printing
chaosmonkey report run-026dc6aa --format json | jq .
```

## Report Enhancements

### Status Indicators

| Status | Emoji | Color (HTML) |
|--------|-------|--------------|
| Completed/Succeeded | ✅ | Green (#10b981) |
| Failed | ❌ | Red (#ef4444) |
| Aborted | ⚠️ | Orange (#f59e0b) |
| Interrupted | 🛑 | Dark Red (#dc2626) |
| Unknown | ❓ | Gray (#6b7280) |

### Chaos Type Icons

| Chaos Type | Emoji |
|------------|-------|
| CPU Hog | 🔥 |
| Memory Hog | 💾 |
| Network Latency | 🌐 |
| Packet Loss | 📡 |
| Disk I/O | 💿 |
| Host Down | 💥 |
| Node Drain | 🔌 |

### Section Icons

| Section | Icon |
|---------|------|
| Experiment Info | 📋 |
| Configuration | ⚙️ |
| Execution Results | 🎯 |
| Rollbacks | 🔄 |
| Steady State | 📊 |
| Summary | 📝 |

## Specialized Output Formatting

### Node Drain (Host-Down) Reports

For `host-down` chaos experiments, reports include specialized formatting:

**Markdown:**
```markdown
### Activity 1: Drain node hosting service

**Status:** ✅ succeeded

**Duration:** 6.16s

**Output:**

| Property | Value |
|----------|-------|
| 🖥️ **Node Name** | `hostname` |
| 🆔 **Node ID** | `538b4367-c20d-cdc7-2a73-6e59e245d5dc` |
| 📍 **Datacenter** | `dev1` |
| ⏱️ **Drain Deadline** | 120s |
| 📦 **Affected Allocations** | 1 |
| 🚦 **Scheduling** | ineligible |

> ℹ️ Node hostname is draining. 1 allocation(s) will migrate.

**🔧 Recovery Command:**

\`\`\`bash
nomad node eligibility -enable 538b4367-c20d-cdc7-2a73-6e59e245d5dc
\`\`\`
```

**HTML:** Similar structure with enhanced visual styling

## Report Generation Flow

```
┌─────────────────────────────────────────────────────┐
│ 1. RUN CHAOS EXPERIMENT                             │
├─────────────────────────────────────────────────────┤
│ $ chaosmonkey execute host-down \                   │
│     --target mobi-platform-account-service-job      │
│                                                     │
│ Output: run-026dc6aa                                │
└─────────────────────────────────────────────────────┘
                     ⬇️
┌─────────────────────────────────────────────────────┐
│ 2. JSON REPORT CREATED AUTOMATICALLY                │
├─────────────────────────────────────────────────────┤
│ Location: reports/run-026dc6aa.json                 │
│                                                     │
│ Contains:                                           │
│ • Full experiment definition                        │
│ • Complete result data                              │
│ • Timestamps and metadata                           │
│ • All activity outputs                              │
└─────────────────────────────────────────────────────┘
                     ⬇️
┌─────────────────────────────────────────────────────┐
│ 3. GENERATE FORMATTED REPORTS (On-Demand)           │
├─────────────────────────────────────────────────────┤
│ $ chaosmonkey report run-026dc6aa --format markdown │
│ $ chaosmonkey report run-026dc6aa --format html     │
│                                                     │
│ Cached in:                                          │
│ • reports/run-026dc6aa.md                           │
│ • reports/run-026dc6aa.html                         │
└─────────────────────────────────────────────────────┘
                     ⬇️
┌─────────────────────────────────────────────────────┐
│ 4. VIEW REPORTS                                     │
├─────────────────────────────────────────────────────┤
│ Markdown: View in VS Code, GitHub, etc.            │
│ HTML: Open in browser for best experience           │
│ JSON: Process with jq or other tools                │
└─────────────────────────────────────────────────────┘
```

## Comparison: Before vs After

### Before (Old Format)

```markdown
# Chaos Run run-026dc6aa

- **Chaos Type:** host-down, node-drain
- **Target:** unknown
- **Status:** completed

## Experiment Summary
\`\`\`json
{
  "version": "1.0.0",
  "title": "Host down template",
  ...
}
\`\`\`

## Result
\`\`\`json
{
  "status": "completed",
  ...
}
\`\`\`
```

**Issues:**
- ❌ Hard to read (walls of JSON)
- ❌ No visual hierarchy
- ❌ Missing key metrics at a glance
- ❌ No recovery information highlighted
- ❌ No timeline visualization

### After (New Format)

```markdown
# 💥 Chaos Engineering Report

## 📋 Experiment Information

| Property | Value |
|----------|-------|
| **Run ID** | `run-026dc6aa` |
| **Chaos Type** | host-down, node-drain |
| **Target** | `mobi-platform-account-service-job` |
| **Status** | ✅ **COMPLETED** |
| **Started** | 2025-10-09 13:33:03 UTC |
| **Completed** | 2025-10-09 13:33:09 UTC |
| **Duration** | 6.18s |

## ⚙️ Configuration Parameters

[Clean table with all parameters]

## 🎯 Execution Results

### Activity 1: Drain node hosting service

**Status:** ✅ succeeded
**Duration:** 6.16s

[Specialized formatting for node drain output]

**🔧 Recovery Command:**
\`\`\`bash
nomad node eligibility -enable 538b4367-...
\`\`\`

---

## 📝 Summary

✅ **System remained within expected steady state**
```

**Improvements:**
- ✅ Visual hierarchy with emojis and sections
- ✅ Key metrics in tables (easy to scan)
- ✅ Timeline information (start/end/duration)
- ✅ Recovery commands highlighted
- ✅ Specialized formatting for different chaos types
- ✅ Clear success/failure indicators

## Report Storage

All reports are stored in the `reports/` directory:

```
reports/
├── run-026dc6aa.json        # Raw experiment data
├── run-026dc6aa.md          # Beautified markdown (cached)
├── run-026dc6aa.html        # Beautiful HTML report (cached)
├── run-2ebf6313.json
├── run-2ebf6313.md
├── run-2ebf6313.html
└── ...
```

**Note:** `.md` and `.html` files are generated on-demand and cached. Delete them to regenerate with the latest format.

## CLI Commands Summary

```bash
# List all available reports
ls -1 reports/*.json | sed 's/.json$//' | xargs -n1 basename

# Generate markdown report (default)
chaosmonkey report <run-id>

# Generate HTML report
chaosmonkey report <run-id> --format html

# Generate JSON report (raw data)
chaosmonkey report <run-id> --format json

# Save to custom location
chaosmonkey report <run-id> --format html -o my-custom-report.html

# View latest report
chaosmonkey report --format html

# Regenerate all reports (delete cached versions)
rm reports/*.md reports/*.html
```

## Best Practices

### For Team Sharing

1. **Use HTML reports for presentations**
   - Professional appearance
   - Easy to share via email or Slack
   - No dependencies required

2. **Use Markdown for documentation**
   - Easy to read in GitHub/GitLab
   - Can be embedded in wiki pages
   - Version control friendly

3. **Use JSON for automation**
   - Parse with scripts
   - Integration with monitoring tools
   - Custom analysis and reporting

### For Archival

- Keep all `.json` files (source of truth)
- Generate `.html` for important experiments
- Commit markdown reports to git for history

### For Analysis

```bash
# Find all failed experiments
for file in reports/*.json; do
  if jq -e '.result.status == "failed"' "$file" > /dev/null; then
    echo "Failed: $(basename $file .json)"
  fi
done

# Generate HTML report for failed experiments
for file in reports/*.json; do
  if jq -e '.result.status == "failed"' "$file" > /dev/null; then
    run_id=$(basename $file .json)
    chaosmonkey report "$run_id" --format html
  fi
done
```

## Customization

The report templates can be customized by editing:

- **Markdown:** `src/chaosmonkey/core/orchestrator.py` - `_render_markdown_summary()`
- **HTML:** `src/chaosmonkey/core/report_html.py` - `generate_html_report()`

## Screenshots

### HTML Report Preview

**Header:**
- Gradient purple background with white text
- Large chaos type emoji (💥)
- Status badge in green/red

**Information Cards:**
- Clean grid layout
- Rounded corners with shadows
- Color-coded left borders

**Configuration Table:**
- Purple header row
- Alternating row colors on hover
- Professional styling

**Activity Cards:**
- White background with border
- Status badge (green for success)
- Detailed tables for outputs
- Dark code blocks for commands

**Footer:**
- Light gray background
- ChaosMonkey branding
- Timestamp

---

**Generated by ChaosMonkey CLI v1.0.0**

## See Also

- [Reports Guide](./REPORTS_GUIDE.md) - How to access and view reports
- [Host-Down Strategy](./HOST_DOWN_STRATEGY.md) - Node drain implementation details
- [Architecture](./architecture.md) - Overall system architecture
