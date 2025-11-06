# UI Status Update Fix

## Problem
After performing VM power operations (stop/start/reboot), the UI continued to show stale status (e.g., "poweredOn" even after stopping the VM).

## Root Causes Identified

### 1. Missing Reports Data Structure Handling
- The `/api/reports` endpoint was looking for top-level fields (`run_id`, `chaos_type`, `status`)
- Actual report JSON had nested structure with `experiment` and `result` objects
- This caused "null" values in the reports UI

### 2. Dora Status Caching/Refresh Delay
- After power operations, Dora service took time to refresh data from vCenter
- Browser was potentially caching the `/api/discover/clients` responses
- No real-time status verification after power actions

### 3. OLVM Method Name Mismatch
- Code was calling `poweroff` but OLVM platform has `power_off` (with underscore)

## Solutions Implemented

### 1. Fixed Reports Data Extraction (`/api/reports` endpoint)
**File**: `src/chaosmonkey/web/app.py`

Updated `list_reports()` function to correctly extract fields from nested structure:
```python
# Extract from nested structure
run_id = filename.stem.replace('run-', '')
chaos_type = data.get("experiment", {}).get("tags", ["unknown"])[0] if data.get("experiment", {}).get("tags") else "unknown"
status = data.get("result", {}).get("status", "unknown")
started_at = data.get("result", {}).get("start")
completed_at = data.get("result", {}).get("end")
target_id = data.get("experiment", {}).get("configuration", {}).get("target_id", "N/A")
```

### 2. Added Real-Time VM Status Endpoint
**File**: `src/chaosmonkey/web/app.py`

Created new `/api/dora/vm-status` endpoint that:
- Bypasses Dora cache
- Fetches status directly from vSphere in real-time
- Returns normalized status format (`poweredOn`/`poweredOff`)

```python
@app.route("/api/dora/vm-status", methods=["POST"])
def get_dora_vm_status():
    """Get real-time VM status directly from vSphere (bypasses Dora cache)."""
    # ... fetches status directly from vSphere using pyvmomi
```

### 3. Implemented Smart Status Polling
**File**: `src/chaosmonkey/web/static/app.js`

After power operations:
1. Shows "Verifying status..." indicator
2. Polls the new `/api/dora/vm-status` endpoint every 3 seconds
3. Checks if actual status matches expected status:
   - `start` → expects `poweredOn`
   - `stop` → expects `poweredOff`
   - `reboot` → expects `poweredOn`
4. Stops polling once status is confirmed (up to 10 attempts = 30 seconds)
5. Reloads the VM table with confirmed status

### 4. Added Cache-Busting for Dora Requests
**File**: `src/chaosmonkey/web/static/app.js`

Added timestamp parameter to prevent browser caching:
```javascript
const timestamp = new Date().getTime();
url = `/api/discover/clients?source=dora&environment=${environment}&_t=${timestamp}`;
```

### 5. Fixed OLVM Method Name
**File**: `src/chaosmonkey/web/app.py`

Updated action mapping:
```python
action_map = {
    'start': 'power_on',
    'stop': 'power_off',  # Changed from 'poweroff'
    'reboot': 'reboot'
}
```

## Testing

To verify the fixes:

1. **Test Reports Display**:
   - Navigate to Reports section
   - Verify all fields show correctly (not null)

2. **Test VM Power Operations**:
   - Select a Dora VM
   - Click "Stop" button
   - Observe "Verifying status..." message
   - Status should update to "poweredOff" within 3-30 seconds

3. **Test Status Refresh**:
   - After power operation, check if VM status updates automatically
   - Verify no need to manually refresh the page

## Configuration Requirements

For VM power operations to work, ensure `chaosmonkey.yaml` has vSphere credentials:

```yaml
platforms:
  vsphere:
    host: "your-vcenter-server.example.com"
    username: "your-username"
    password: "your-password"
    insecure: true  # Set to false in production with valid SSL certs
```

## Files Modified

1. `/src/chaosmonkey/web/app.py`:
   - Fixed `list_reports()` function
   - Added `/api/dora/vm-status` endpoint
   - Fixed OLVM method name in `/api/dora/vm-power`

2. `/src/chaosmonkey/web/static/app.js`:
   - Updated `performVMAction()` to poll real-time status
   - Added cache-busting timestamp to `loadNodes()`

## Expected Behavior

### Before Fix:
- Reports showed "null" for all fields
- VM status remained "poweredOn" even after stopping
- Required manual page refresh to see updated status

### After Fix:
- Reports display all fields correctly
- VM status updates automatically after power operations
- Real-time verification with visual feedback
- No manual refresh needed

## Notes

- Status verification now uses direct vSphere queries (fast)
- Falls back to Dora if vSphere unavailable
- Polling stops automatically once status is confirmed
- Maximum wait time: 30 seconds (10 attempts × 3 seconds)
