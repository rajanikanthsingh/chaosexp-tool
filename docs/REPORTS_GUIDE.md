# Chaos Experiment Reports Guide

## Overview

Every chaos experiment executed through ChaosMonkey automatically generates two types of reports:
1. **JSON report** (`.json`) - Machine-readable format with full experiment details
2. **Markdown report** (`.md`) - Human-readable format for easy viewing

## Report Location

All reports are stored in the `reports/` directory:

```
chaosmonkey/
└── reports/
    ├── run-d243a2bb.json  ← Full experiment data
    ├── run-d243a2bb.md    ← Human-readable summary
    ├── run-ae636ea9.json
    ├── run-ae636ea9.md
    └── ... (more reports)
```

## Viewing Reports

### Method 1: View Latest Report (Recommended)

```bash
# View the most recent chaos experiment report
chaosmonkey report

# This shows the latest markdown report in your terminal
```

### Method 2: View Specific Report by Run ID

When you execute a chaos experiment, you get a run ID in the output:

```bash
$ chaosmonkey execute --chaos-type cpu-hog --target-id my-service

{
  "run_id": "run-d243a2bb",  ← This is your run ID
  "chaos_type": "cpu-hog",
  ...
}
```

Then view that specific report:

```bash
# View specific report
chaosmonkey report run-d243a2bb
```

### Method 3: View Report in Different Formats

```bash
# View as Markdown (default)
chaosmonkey report run-d243a2bb --format markdown

# View as JSON
chaosmonkey report run-d243a2bb --format json
```

### Method 4: Save Report to File

```bash
# Save markdown report to file
chaosmonkey report run-d243a2bb --output report.md

# Save JSON report to file
chaosmonkey report run-d243a2bb --format json --output report.json
```

### Method 5: View Report Files Directly

```bash
# View markdown report directly
cat reports/run-d243a2bb.md

# View JSON report directly
cat reports/run-d243a2bb.json | jq .

# Open in your editor
code reports/run-d243a2bb.md
```

## Report Contents

### Markdown Report Format

```markdown
# Chaos Run run-d243a2bb

- **Chaos Type:** cpu-hog
- **Target:** mobi-platform-account-service-job
- **Status:** completed

## Experiment Summary
{experiment configuration}

## Results
{execution results}
```

### JSON Report Structure

```json
{
  "experiment": {
    "version": "1.0.0",
    "title": "CPU hog template",
    "description": "...",
    "configuration": {
      "target_id": "mobi-platform-account-service-job",
      "chaos_type": "cpu-hog",
      "duration_seconds": 120
    },
    "method": [...]
  },
  "result": {
    "status": "completed",
    "deviated": false,
    "run": [...]
  }
}
```

## Listing All Reports

### View All Report Files

```bash
# List all markdown reports (sorted by date, newest first)
ls -lht reports/*.md

# List all JSON reports
ls -lht reports/*.json

# Count total reports
ls reports/*.md | wc -l
```

### Find Reports by Chaos Type

```bash
# Find all CPU hog reports
grep -l "cpu-hog" reports/*.md

# Find all memory hog reports
grep -l "memory-hog" reports/*.md

# Find all network latency reports
grep -l "network-latency" reports/*.md
```

### Find Reports by Target Service

```bash
# Find reports for specific service
grep -l "mobi-platform-account-service-job" reports/*.md

# Show matching report names
grep -l "mobi-platform-account-service-job" reports/*.md | \
  xargs -n1 basename
```

## Analyzing Reports

### Extract Key Information

```bash
# Get all run IDs
ls reports/*.md | sed 's/.*run-/run-/' | sed 's/.md//'

# Get chaos types from recent reports
head -20 reports/*.md | grep "Chaos Type:"

# Get execution status
grep "Status:" reports/run-*.md
```

### Parse JSON Reports

```bash
# Get experiment status
cat reports/run-d243a2bb.json | jq '.result.status'

# Get chaos type
cat reports/run-d243a2bb.json | jq '.experiment.configuration.target_id'

# Get experiment duration
cat reports/run-d243a2bb.json | jq '.experiment.configuration.duration_seconds'

# Check if experiment deviated
cat reports/run-d243a2bb.json | jq '.result.deviated'
```

## Report Generation Workflow

### During Experiment Execution

```bash
$ chaosmonkey execute --chaos-type cpu-hog --target-id my-service

# 1. Experiment runs
[17:39:40] ✓ Chaos job deployed successfully!

# 2. Report is automatically generated
{
  "run_id": "run-d243a2bb",
  "report_path": "/path/to/reports/run-d243a2bb.md",
  ...
}

# 3. Two files created:
#    - reports/run-d243a2bb.json
#    - reports/run-d243a2bb.md
```

### View Report Immediately After Execution

```bash
# Run experiment and save run ID
RUN_ID=$(chaosmonkey execute --chaos-type cpu-hog --target-id my-service | \
         jq -r '.run_id')

# View the report
chaosmonkey report $RUN_ID

# Or directly
chaosmonkey report $(chaosmonkey execute --chaos-type cpu-hog --target-id my-service | jq -r '.run_id')
```

## Example Reports by Chaos Type

### CPU Hog Report

```bash
# View recent CPU hog report
chaosmonkey report | grep -A 20 "cpu-hog"
```

Expected content:
- Chaos Type: cpu-hog
- Target: service name
- CPU workers: 8
- Duration: 120 seconds
- Node: target node name
- Status: completed

### Memory Hog Report

```bash
# View recent memory hog report
chaosmonkey report | grep -A 20 "memory-hog"
```

Expected content:
- Chaos Type: memory-hog
- Target: service name
- Memory: 2048 MB
- Workers: 2
- Duration: 120 seconds
- Status: completed

### Network Latency Report

```bash
# View recent network latency report
grep -l "network-latency" reports/*.md | head -1 | xargs cat
```

Expected content:
- Chaos Type: network-latency
- Target: service name
- Latency: 250ms
- Duration: 120 seconds
- Tool: Pumba
- Status: completed

### Disk I/O Report

```bash
# View recent disk I/O report
grep -l "disk-io" reports/*.md | head -1 | xargs cat
```

Expected content:
- Chaos Type: disk-io
- Target: service name
- I/O Workers: 4
- Write Size: 1024 MB
- Duration: 120 seconds
- Status: completed

## Creating Custom Report Summaries

### Generate Summary of All Recent Experiments

```bash
#!/bin/bash
# File: chaos-summary.sh

echo "=== Chaos Experiment Summary ==="
echo ""

for report in $(ls -t reports/*.md | head -10); do
    echo "Report: $(basename $report)"
    grep "Chaos Type:" $report
    grep "Target:" $report
    grep "Status:" $report
    echo "---"
done
```

Run it:
```bash
bash chaos-summary.sh
```

### Export Reports to CSV

```bash
#!/bin/bash
# File: export-reports.sh

echo "run_id,chaos_type,target,status,report_path"

for json in reports/*.json; do
    run_id=$(basename $json .json)
    chaos_type=$(jq -r '.experiment.configuration.target_kind // "unknown"' $json)
    target=$(jq -r '.experiment.configuration.target_id // "unknown"' $json)
    status=$(jq -r '.result.status // "unknown"' $json)
    
    echo "$run_id,$chaos_type,$target,$status,$json"
done
```

Run it:
```bash
bash export-reports.sh > chaos-experiments.csv
```

## Sharing Reports

### Share Markdown Report

```bash
# Copy to clipboard (macOS)
cat reports/run-d243a2bb.md | pbcopy

# Upload to GitHub Gist
gh gist create reports/run-d243a2bb.md --desc "Chaos Experiment Report"

# Send via email
cat reports/run-d243a2bb.md | mail -s "Chaos Experiment Report" team@example.com
```

### Share JSON Report

```bash
# Pretty print and save
cat reports/run-d243a2bb.json | jq . > report-pretty.json

# Share specific sections
cat reports/run-d243a2bb.json | jq '.result' > experiment-results.json
```

## Integrating with CI/CD

### Store Reports in Artifacts

```yaml
# GitHub Actions
- name: Run Chaos Experiment
  run: |
    chaosmonkey execute --chaos-type cpu-hog --target-id my-service
    
- name: Upload Reports
  uses: actions/upload-artifact@v3
  with:
    name: chaos-reports
    path: reports/*.md
```

### Compare Reports Over Time

```bash
# Create trend report
for report in $(ls -t reports/*.json | head -30); do
    echo "$(basename $report): $(jq -r '.result.status' $report)"
done
```

## Troubleshooting Reports

### No Reports Found

```bash
# Check if reports directory exists
ls -la reports/

# Verify experiments were executed
chaosmonkey chaos-jobs

# Check if reports are being generated
chaosmonkey execute --chaos-type cpu-hog --target-id test-service --dry-run
```

### Report Not Found

```bash
# List available run IDs
ls reports/*.md | sed 's/.*run-//' | sed 's/.md//'

# View latest report instead
chaosmonkey report
```

### Corrupted Report

```bash
# Check JSON validity
cat reports/run-d243a2bb.json | jq . >/dev/null && echo "Valid JSON" || echo "Invalid JSON"

# Re-generate from experiment
# (Not currently supported, but you can re-run the experiment)
```

## Best Practices

### 1. Review Reports After Each Experiment

```bash
# Immediately after running chaos
chaosmonkey execute --chaos-type cpu-hog --target-id my-service
chaosmonkey report  # Review results
```

### 2. Archive Important Reports

```bash
# Create archive directory
mkdir -p reports/archive/2025-10

# Move completed experiments
mv reports/run-d243a2bb.* reports/archive/2025-10/
```

### 3. Clean Up Old Reports

```bash
# Keep only last 50 reports
ls -t reports/*.md | tail -n +51 | xargs rm
ls -t reports/*.json | tail -n +51 | xargs rm
```

### 4. Create Report Index

```bash
# Generate index of all experiments
echo "# Chaos Experiment Index" > EXPERIMENTS.md
echo "" >> EXPERIMENTS.md

for report in $(ls -t reports/*.md); do
    echo "## $(basename $report .md)" >> EXPERIMENTS.md
    head -10 $report >> EXPERIMENTS.md
    echo "" >> EXPERIMENTS.md
done
```

## Quick Reference

```bash
# View latest report
chaosmonkey report

# View specific report
chaosmonkey report run-d243a2bb

# View as JSON
chaosmonkey report run-d243a2bb --format json

# Save report
chaosmonkey report run-d243a2bb --output my-report.md

# List all reports
ls -lht reports/*.md

# Find reports by type
grep -l "cpu-hog" reports/*.md

# Get report details
cat reports/run-d243a2bb.json | jq '.result.status'
```

## Example: Complete Workflow

```bash
# 1. Run chaos experiment
RUN_ID=$(chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id mobi-platform-account-service-job | \
  jq -r '.run_id')

echo "Experiment started: $RUN_ID"

# 2. Wait for completion (chaos runs for 120 seconds)
sleep 130

# 3. View the report
chaosmonkey report $RUN_ID

# 4. Save report for sharing
chaosmonkey report $RUN_ID --output reports/archive/cpu-test-$(date +%Y%m%d).md

# 5. Extract key findings
cat reports/$RUN_ID.json | jq '{
  chaos_type: .experiment.configuration.target_kind,
  target: .experiment.configuration.target_id,
  status: .result.status,
  duration: .experiment.configuration.duration_seconds
}'

echo "✅ Chaos experiment complete! Report saved."
```

---

**Pro Tip**: Create an alias for quick report access:

```bash
# Add to ~/.zshrc or ~/.bashrc
alias chaos-latest='chaosmonkey report'
alias chaos-reports='ls -lht reports/*.md | head -10'
alias chaos-status='grep "Status:" reports/*.md | tail -10'
```

Now you can simply run:
```bash
chaos-latest      # View latest report
chaos-reports     # List recent reports
chaos-status      # Check experiment statuses
```
