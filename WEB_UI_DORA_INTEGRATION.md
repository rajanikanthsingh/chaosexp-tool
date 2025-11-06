# Web UI Dora Integration - Implementation Summary

## Overview

The ChaosMonkey web UI has been extended to support VM management through the Dora API, providing a unified interface to manage both Nomad nodes and VMs across multiple environments.

## Changes Made

### 1. Backend (Flask) - `src/chaosmonkey/web/app.py`

#### New Endpoints

**Dora Discovery Endpoint:**
```python
@app.route("/api/discover/dora")
def discover_dora():
```
- Fetches VM data from Dora API based on selected environment
- Returns transformed VM data in UI-friendly format
- Query parameter: `environment` (default: "Paytv")
- Response includes: name, id, power_state, hypervisor, cpu, memory, guest_os, datacenter

**Dora Environments Endpoint:**
```python
@app.route("/api/dora/environments")
def list_dora_environments():
```
- Lists all 13 available Dora environments
- Returns: Paytv, Oracle-Paytv, DR-Paytv, Arvig-Staging/Prod, EPB-Staging/Prod, Lumos-Prod, Comporium-Prod, MSG-Prod, Liberty-Prod, Midco-Staging/Prod

**VM Power Management Endpoints:**

1. **Power On:** `POST /api/vm/power-on`
   - Tries vSphere first, falls back to OLVM
   - Body: `{vm_name, timeout}`
   - Returns: `{success, message, platform}`

2. **Power Off:** `POST /api/vm/power-off`
   - Tries vSphere first, falls back to OLVM
   - Body: `{vm_name, graceful, timeout}`
   - Supports graceful shutdown (default: true)
   - Returns: `{success, message, platform}`

3. **Reboot:** `POST /api/vm/reboot`
   - Tries vSphere first, falls back to OLVM
   - Body: `{vm_name, graceful, timeout}`
   - Supports graceful reboot (default: true)
   - Returns: `{success, message, platform}`

**Error Handling:**
- All VM power endpoints attempt both platforms and aggregate errors
- Returns detailed error messages including which platform failed and why

### 2. Frontend (HTML) - `src/chaosmonkey/web/templates/index.html`

#### Updated Nodes Tab Structure

**Before:**
```html
<h2>Nomad Client Nodes</h2>
<button onclick="refreshNodes()">Refresh</button>
```

**After:**
```html
<h2>Nodes & VMs</h2>
<div class="d-flex gap-3 align-items-center mb-3">
    <!-- Source Selector -->
    <select id="source-select" onchange="changeNodeSource()">
        <option value="nomad">Nomad Client Nodes</option>
        <option value="dora">Dora VMs</option>
    </select>
    
    <!-- Environment Selector (shown when Dora is selected) -->
    <div id="dora-environment-container" style="display:none;">
        <select id="dora-environment-select" onchange="loadNodes()">
            <!-- Dynamically populated -->
        </select>
    </div>
    
    <button onclick="refreshNodes()">Refresh</button>
</div>
```

### 3. Frontend (JavaScript) - `src/chaosmonkey/web/static/app.js`

#### New Global State Variables
```javascript
let currentNodeSource = 'nomad'; // 'nomad' or 'dora'
let doraEnvironments = [];
let currentDoraEnvironment = 'Paytv';
```

#### Modified Functions

**`loadNodes(silent = false)`**
- Now handles both Nomad and Dora sources
- Routes to appropriate API based on `currentNodeSource`
- For Dora: includes environment parameter

**`renderNodesTable(data)`**
- Renders Nomad nodes table (original behavior)
- Columns: Name, Status, Datacenter, CPU, Memory, Drain, Allocations, Actions
- Actions: Enable/Drain buttons

#### New Functions

**`renderDoraTable(data)`**
- Renders VM table for Dora source
- Columns: Name, Power State, Hypervisor, CPU, Memory, Guest OS, Actions
- **Removed columns:** Drain, Allocations (not applicable to VMs)
- Actions: Start, Reboot, Stop buttons
- Dynamic button states based on VM power state:
  - Start: Disabled if VM is powered on
  - Reboot: Disabled if VM is powered off
  - Stop: Disabled if VM is powered off

**`loadDoraEnvironments()`**
- Fetches available Dora environments on page load
- Populates environment dropdown
- Called during `DOMContentLoaded`

**`changeNodeSource()`**
- Handles source dropdown change
- Shows/hides Dora environment selector
- Triggers `loadNodes()` to refresh data

**`vmPowerAction(vmName, action)`**
- Handles Start/Reboot/Stop button clicks
- Shows confirmation dialog
- Updates button state during operation (spinner)
- Calls appropriate backend API endpoint
- Shows success/error notification
- Refreshes table after 2 seconds to show updated state
- Restores button state after completion

**`showNotification(type, message)`**
- Displays Bootstrap alert at top of page
- Auto-dismisses after 5 seconds
- Types: 'success' (green) or 'error' (red)

**`refreshNodes()`**
- Updated to handle both sources
- Nomad: Force refresh with `?refresh=true`
- Dora: Reload data (no caching)

### 4. Styling (CSS) - `src/chaosmonkey/web/static/style.css`

#### New Styles
```css
/* VM Power Actions */
.btn-group .btn { margin: 0 !important; }
.btn-group-sm .btn { padding: 0.25rem 0.5rem; }

/* Dora environment selector */
#dora-environment-container { transition: all 0.3s ease; }

/* Source/environment dropdowns */
#source-select, #dora-environment-select { min-width: 200px; }

/* VM power state indicators */
.text-success, .text-danger, .text-warning { font-weight: 600; }

/* Notifications */
.position-fixed { z-index: 9999; }

/* Button loading state */
.btn:disabled { cursor: not-allowed; opacity: 0.65; }

/* Action button spacing */
.node-actions .btn-group { display: flex; gap: 2px; }
```

## User Workflow

### Viewing Nomad Nodes (Default)
1. Navigate to "Nodes" tab
2. Source selector shows "Nomad Client Nodes" (default)
3. Table displays with columns: Name, Status, Datacenter, CPU, Memory, Drain, Allocations, Actions
4. Actions available: Enable/Drain

### Viewing Dora VMs
1. Navigate to "Nodes" tab
2. Select "Dora VMs" from source dropdown
3. Environment selector appears (default: "Paytv")
4. Select desired environment from dropdown
5. Table displays with columns: Name, Power State, Hypervisor, CPU, Memory, Guest OS, Actions
6. Actions available: Start, Reboot, Stop (conditionally enabled)

### Managing VMs
1. Select Dora source and environment
2. Locate target VM in table
3. Click action button:
   - **Start:** Powers on the VM
   - **Reboot:** Gracefully reboots the VM
   - **Stop:** Gracefully shuts down the VM
4. Confirm action in dialog
5. Button shows spinner during operation
6. Notification appears with result
7. Table refreshes after 2 seconds

## Technical Details

### Power Operation Flow
1. User clicks Start/Reboot/Stop button
2. Confirmation dialog appears
3. Button disabled with spinner
4. JavaScript sends POST request to `/api/vm/{action}`
5. Backend tries vSphere platform first
6. If vSphere fails, tries OLVM platform
7. Returns success with platform used, or error with details
8. Frontend shows notification
9. Table reloads after delay
10. Button restored to original state

### Platform Fallback Logic
```python
try:
    # Try vSphere
    with VSpherePlatform(...) as platform:
        platform.power_on(vm_name)
        return success
except:
    # Try OLVM
    with OLVMPlatform(...) as platform:
        platform.power_on(vm_name)
        return success
```

### Error Handling
- **Platform not available:** "Dora platform not available: {error}"
- **VM not found:** Error from platform (VM not found)
- **Operation failed:** Aggregate errors from both platforms
- **Timeout:** Configurable timeout (default: 300 seconds)
- **Network errors:** Caught and displayed to user

## Configuration Requirements

### Environment Variables
Required for Dora integration:
```bash
# Dora API
DORA_HOST=hostname
DORA_API_PORT=8000
DORA_AUTH_PORT=51051
DORA_USERNAME=your_username
DORA_PASSWORD=your_password

# vSphere (for VM operations)
VSPHERE_SERVER=vcenter.example.com
VSPHERE_USERNAME=administrator@vsphere.local
VSPHERE_PASSWORD=your_password
VSPHERE_INSECURE=true

# OLVM (optional, for fallback)
OLVM_URL=https://engine.example.com/ovirt-engine/api
OLVM_USERNAME=admin@internal
OLVM_PASSWORD=your_password
OLVM_INSECURE=false
```

## Dependencies

### Python Packages
Required for VM operations:
```bash
pip install flask flask-cors
pip install -e '.[platforms]'  # Includes pyvmomi and ovirt-engine-sdk-python
```

### Browser Requirements
- Modern browser with JavaScript enabled
- Bootstrap 5.3.0 (loaded from CDN)
- Font Awesome 6.4.0 (loaded from CDN)

## Testing

### Manual Testing Checklist
- [ ] Nomad source loads correctly
- [ ] Dora source dropdown appears
- [ ] Dora environments load in dropdown
- [ ] Switching sources updates table
- [ ] Changing environment refreshes VMs
- [ ] VM table shows correct columns
- [ ] Power state displays correctly
- [ ] Start button works (powers on VM)
- [ ] Stop button works (shuts down VM)
- [ ] Reboot button works (reboots VM)
- [ ] Button states update correctly
- [ ] Notifications display properly
- [ ] Error messages are clear
- [ ] Table refreshes after operations
- [ ] Auto-refresh works for both sources

### API Testing
```bash
# Test Dora discovery
curl http://localhost:8080/api/discover/dora?environment=Paytv

# Test environments list
curl http://localhost:8080/api/dora/environments

# Test VM power on
curl -X POST http://localhost:8080/api/vm/power-on \
  -H "Content-Type: application/json" \
  -d '{"vm_name": "test-vm-01", "timeout": 300}'

# Test VM power off
curl -X POST http://localhost:8080/api/vm/power-off \
  -H "Content-Type: application/json" \
  -d '{"vm_name": "test-vm-01", "graceful": true, "timeout": 300}'

# Test VM reboot
curl -X POST http://localhost:8080/api/vm/reboot \
  -H "Content-Type: application/json" \
  -d '{"vm_name": "test-vm-01", "graceful": true, "timeout": 300}'
```

## Screenshots / UI Layout

### Nomad View
```
[Source: Nomad Client Nodes ▼]  [Refresh]

Name       | Status | DC    | CPU  | Memory | Drain | Allocs | Actions
-----------|--------|-------|------|--------|-------|--------|----------
node-01    | ready  | dc1   | 4000 | 8.0 GB | No    | 5      | [Drain]
node-02    | ready  | dc1   | 4000 | 8.0 GB | Yes   | 0      | [Enable]
```

### Dora View
```
[Source: Dora VMs ▼]  [Environment: Paytv ▼]  [Refresh]

Name       | State      | Hypervisor | CPU | Memory | Guest OS    | Actions
-----------|------------|------------|-----|--------|-------------|------------------------
web-01     | poweredOn  | esx-01     | 4   | 8.0 GB | Ubuntu 20.04| [Start][Reboot][Stop]
web-02     | poweredOff | esx-02     | 4   | 8.0 GB | Ubuntu 20.04| [Start][Reboot][Stop]
                                                                      ✓      ✗       ✗
```

## Future Enhancements

### Potential Improvements
1. **Bulk Operations:** Select multiple VMs and perform batch power operations
2. **VM Details Modal:** Show detailed VM information (snapshots, networks, disks)
3. **Power Scheduling:** Schedule power on/off at specific times
4. **VM Filtering:** Filter VMs by name, state, hypervisor
5. **VM Search:** Quick search box for large environments
6. **Power History:** Track VM power operation history
7. **Favorites:** Mark frequently accessed VMs
8. **Custom Actions:** Add custom VM operations (snapshot, clone)
9. **Real-time Updates:** WebSocket for live VM state changes
10. **Platform Selection:** Allow user to choose vSphere or OLVM explicitly

### Known Limitations
1. No real-time power state updates (requires manual refresh)
2. No validation if VM exists before power operation
3. Limited error context (shows aggregate errors)
4. No progress indication for long-running operations
5. No rollback mechanism if operation fails midway
6. Environment list is static (hardcoded in Dora client)

## Troubleshooting

### VM Power Operations Fail
1. Check `.env` file has correct credentials
2. Verify vSphere/OLVM connectivity
3. Check VM name is correct (case-sensitive)
4. Review backend logs for detailed errors
5. Test platform connection via CLI:
   ```bash
   chaosmonkey platforms vm-info <vm-name> --platform vsphere
   ```

### Dora Environment Shows No VMs
1. Verify Dora API credentials
2. Check environment name spelling
3. Ensure Dora API is accessible
4. Test via CLI:
   ```bash
   chaosmonkey platforms dora-discover "Paytv"
   ```

### UI Not Loading/Updating
1. Check browser console for JavaScript errors
2. Verify Flask backend is running
3. Check CORS is enabled
4. Clear browser cache
5. Test API endpoints directly

## Files Modified

1. `src/chaosmonkey/web/app.py` - Added 4 new endpoints
2. `src/chaosmonkey/web/templates/index.html` - Updated Nodes tab HTML
3. `src/chaosmonkey/web/static/app.js` - Added 6 new functions, modified 2
4. `src/chaosmonkey/web/static/style.css` - Added VM action styles

## Lines of Code
- **Backend:** ~250 lines added
- **Frontend HTML:** ~30 lines modified
- **Frontend JavaScript:** ~200 lines added
- **CSS:** ~50 lines added
- **Total:** ~530 lines

---

**Completed:** October 10, 2025
**Version:** 1.0
**Status:** ✅ Ready for Testing
