# Reports Tab Sorting Fix

## Issue
Reports in the Web UI were not sorted by time. They appeared in alphabetical order by filename (run-id), which is a random hex string and doesn't correlate with creation time.

## Solution
Updated the `/api/reports` endpoint in `src/chaosmonkey/web/app.py` to sort reports by their `started_at` timestamp in descending order (latest first).

## Changes Made

### Before
```python
for report_file in sorted(REPORTS_DIR.glob("run-*.json"), reverse=True):
    # ... process reports ...
    
return jsonify({"reports": reports})
```
- Reports sorted alphabetically by filename
- Random hex IDs don't reflect chronological order
- Latest reports could appear anywhere in the list

### After
```python
for report_file in REPORTS_DIR.glob("run-*.json"):
    # ... process reports ...
    
# Sort reports by started_at timestamp, latest first (descending order)
# Handle None values by putting them at the end
reports.sort(
    key=lambda r: r.get("started_at") or "", 
    reverse=True
)

return jsonify({"reports": reports})
```
- Reports sorted by actual execution timestamp
- Latest experiments appear at the top
- Handles missing timestamps gracefully (puts them at the end)

## How It Works

1. **Read all reports** - No initial sorting of files
2. **Parse JSON data** - Extract `started_at` timestamp from each report
3. **Sort in-memory** - Sort the reports list by `started_at` timestamp
4. **Reverse order** - Use `reverse=True` to show latest first
5. **Handle None** - Empty string fallback ensures reports without timestamps go to the end

## Sorting Key
```python
key=lambda r: r.get("started_at") or ""
```
- Uses ISO 8601 timestamps (e.g., `"2025-10-10T15:30:45.123456+00:00"`)
- ISO format naturally sorts chronologically
- Empty string fallback for reports missing timestamps

## Testing

### Before Fix
```
Reports list:
- run-abc123 (Oct 10, 14:30) ← Random order
- run-xyz789 (Oct 10, 15:45)
- run-def456 (Oct 10, 14:00)
```

### After Fix
```
Reports list:
- run-xyz789 (Oct 10, 15:45) ← Latest first
- run-abc123 (Oct 10, 14:30)
- run-def456 (Oct 10, 14:00)
```

## Verification Steps

1. **Restart Web UI:**
   ```bash
   python3 run_web_ui.py
   ```

2. **Navigate to Reports tab** in the browser

3. **Run a new chaos experiment**

4. **Refresh Reports tab** - New report should appear at the top

5. **Check order** - Reports should be in reverse chronological order

## Files Modified

- `src/chaosmonkey/web/app.py` (lines 1845-1884)
  - Updated `list_reports()` function
  - Added sorting by `started_at` timestamp
  - Maintained all existing functionality

## Backward Compatibility

✅ **Fully backward compatible**
- No API changes
- No database schema changes
- No frontend changes required
- Existing reports display correctly

## Performance Impact

⚡ **Minimal impact**
- Sorting happens in-memory after file I/O
- Typical report counts: 10-100 reports
- Python's Timsort: O(n log n) - extremely fast for small datasets
- No noticeable delay in API response

## Edge Cases Handled

1. **Missing timestamps** - Sorted to end with empty string fallback
2. **Malformed timestamps** - String comparison still works
3. **Empty reports directory** - Returns empty list (no errors)
4. **Concurrent access** - No race conditions (read-only operation)

## Date
October 10, 2025
