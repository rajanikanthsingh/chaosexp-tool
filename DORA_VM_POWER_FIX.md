# Dora VM Power Actions Fix

## Issues Fixed

### 1. Reports Showing Null Values ✅
**Problem:** Reports were showing null values for run_id, chaos_type, target, started, and completed times.

**Root Cause:** The report data structure is nested (inside `experiment` and `result` objects), but the web UI was trying to read top-level fields.

**Fix:** Updated `list_reports()` function in `src/chaosmonkey/web/app.py` to correctly extract data from the nested structure:
- `run_id`: From filename
- `chaos_type`: From `experiment.tags[0]`
- `status`: From `result.status`
- `started_at`: From `result.start`
- `completed_at`: From `result.end`
- `target_id`: From `experiment.configuration.target_id`

### 2. Dora VM Start/Reboot/Stop Buttons Not Showing ✅
**Problem:** The Start/Reboot/Stop action buttons were not appearing for Dora VMs.

**Root Cause:** The frontend code was checking `vm.source === 'dora'` to determine if action buttons should be shown, but Dora VMs weren't being marked with this property.

**Fix:** Updated `src/chaosmonkey/web/static/app.js` to:
1. Add `source: 'dora'` property to all Dora VMs when loading
2. Normalize the power state field (`vm.powerState` from `vm.power`)
3. Ensure `isRunning`/`isStopped` state detection works for Dora VMs

### 3. OLVM Method Name Mismatch ✅
**Problem:** Error "OLVMPlatform' object has no attribute 'poweroff'"

**Root Cause:** The endpoint was calling `poweroff` (no underscore) but OLVM platform uses `power_off` (with underscore).

**Fix:** Updated `action_map` in `/api/dora/vm-power` endpoint to use correct method name: `'stop': 'power_off'`

### 4. VM Power Action Errors - Configuration Required ⚠️
**Current Error:** "Failed to stop VM on all platforms. Errors: vSphere: Failed to connect to vSphere: [Errno 8] nodename nor servname provided, or not known"

**Root Cause:** vSphere and OLVM platforms are not configured in `chaosmonkey.yaml`.

**Solution Required:** Add platform configuration to `chaosmonkey.yaml`

## Configuration Needed

To enable VM power actions (Start/Reboot/Stop), you need to add vSphere or OLVM credentials to your `chaosmonkey.yaml`:

```yaml
chaos:
  experiments_path: experiments
  reports_path: reports
  dry_run: false

platforms:
  vsphere:
    server: "vcenter.example.com"  # Your vCenter server hostname/IP
    username: "administrator@vsphere.local"  # vSphere username
    password: "your-password"  # vSphere password
    insecure: true  # Set to false in production with proper SSL certs
    
  # Alternative: Use OLVM/oVirt instead of vSphere
  olvm:
    url: "https://engine.example.com/ovirt-engine/api"
    username: "admin@internal"
    password: "your-password"
    insecure: true
```

### For Dora Environment (OracleQA vCenter)

Based on the Dora configuration in `src/chaosmonkey/platforms/dora/client.py`, the Dev1 environment uses:
- vCenter: `OracleQA`
- Pattern Path: `ORA-DEV`
- Host Filter: `dev1`

You need to configure the vSphere server for OracleQA:

```yaml
platforms:
  vsphere:
    server: "oracleqa-vcenter.example.com"  # Replace with actual OracleQA vCenter hostname
    username: "your-username"
    password: "your-password"
    insecure: true
```

## How It Works

1. **Discovery:** Dora API is used to discover VMs (read-only inventory system)
2. **Power Actions:** When you click Start/Reboot/Stop:
   - Frontend sends request to `/api/dora/vm-power`
   - Backend tries vSphere platform first (if configured)
   - If vSphere fails or not configured, falls back to OLVM
   - The platform connects to the actual hypervisor to perform the action

## Testing

After adding the platform configuration:

1. Restart the web UI:
   ```bash
   python run_web_ui.py
   ```

2. Navigate to the Dora VMs section
3. Try the Start/Reboot/Stop buttons on a VM
4. You should see success messages like: "VM 'hostname' reboot successful via vSphere"

## Error Handling

The endpoint now provides better error messages:
- **No platform configured:** "No virtualization platform configured. Please configure vSphere or OLVM credentials in chaosmonkey.yaml"
- **Connection issues:** Shows specific platform errors
- **VM not found:** "VM 'name' not found" from the platform
- **Invalid action:** "Invalid action: {action}. Must be 'start', 'reboot', or 'stop'"

## Summary of Changes

### Files Modified:
1. `src/chaosmonkey/web/app.py`:
   - Fixed `list_reports()` to correctly extract nested report data
   - Fixed `dora_vm_power_action()` method name from `poweroff` to `power_off`
   - Added configuration validation before attempting platform connections

2. `src/chaosmonkey/web/static/app.js`:
   - Added `source: 'dora'` property to Dora VMs
   - Normalized `powerState` field for Dora VMs
   - Ensured action buttons are shown for Dora VMs

### Next Steps:
1. ✅ Add vSphere/OLVM configuration to `chaosmonkey.yaml`
2. ✅ Restart the web UI
3. ✅ Test VM power actions

## Dependencies

Make sure you have the platform-specific Python packages installed:

```bash
# For vSphere support
pip install pyvmomi

# For OLVM support
pip install ovirt-engine-sdk-python

# Or install all platform extras
pip install -e ".[platforms]"
```
