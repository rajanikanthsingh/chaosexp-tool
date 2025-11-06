# Dora VM Status Update Fix

## Problem
After stopping/rebooting a Dora VM, the UI continued to show the old "poweredOn" status instead of reflecting the actual VM state.

## Root Cause
1. **No direct Dora API for power management**: Dora is a read-only inventory system that fetches data from vCenter
2. **Delayed vCenter updates**: After a VM power operation via vSphere/OLVM, vCenter takes time to reflect the change
3. **Short refresh delay**: The UI was only waiting 2 seconds before refreshing, which wasn't enough time for Dora to fetch updated status from vCenter

## Solutions Implemented

### 1. Fixed OLVM Method Name (`app.py`)
**Issue**: Code was calling `poweroff()` but OLVM client uses `power_off()`

**Fix**: Updated method mapping in `/api/dora/vm-power`:
```python
action_map = {
    'start': 'power_on',
    'stop': 'power_off',  # Changed from 'poweroff'
    'reboot': 'reboot'
}
```

### 2. Added User Feedback (`app.py`)
**Issue**: Users didn't know that status updates might be delayed

**Fix**: Added note in API response:
```python
return jsonify({
    "success": True,
    "message": f"VM '{vm_name}' {action} successful via vSphere",
    "platform": "vsphere",
    "vm_name": vm_name,
    "action": action,
    "note": "Note: VM status in Dora may take 30-60 seconds to reflect the change"
})
```

### 3. Implemented Status Polling (`app.js`)
**Issue**: Single refresh after 2 seconds wasn't enough time for status update

**Fix**: Implemented intelligent polling mechanism:
- Initial 5-second delay before first refresh
- Polls every 5 seconds for up to 50 seconds
- Silent background refreshes (doesn't disrupt UI)
- Shows "Waiting for status update..." message
- Automatic final refresh after max attempts

```javascript
// Poll for status update (Dora may take time to refresh from vCenter)
button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Waiting for status update...';
let attempts = 0;
const maxAttempts = 10; // Try for ~50 seconds (10 * 5s)

const pollStatus = async () => {
    attempts++;
    await loadNodes(true); // Silent reload
    
    if (attempts < maxAttempts) {
        // Continue polling every 5 seconds
        setTimeout(pollStatus, 5000);
    } else {
        // Final reload after max attempts
        await loadNodes();
    }
};

// Start polling after initial delay
setTimeout(pollStatus, 5000);
```

## Benefits
1. **Accurate Status**: UI now shows correct VM status after power operations
2. **Better UX**: Users are informed about potential delays and see polling progress
3. **Automatic Updates**: No need to manually refresh - status updates automatically
4. **Resilient**: Polls multiple times to handle varying vCenter/Dora refresh times

## Testing
To test the fix:
1. Select a Dora VM in the UI
2. Perform a power operation (Stop/Start/Reboot)
3. Observe the "Waiting for status update..." message
4. Watch as the UI automatically refreshes in the background
5. Verify that the VM status eventually updates correctly

## Configuration Requirements
For power operations to work, ensure `chaosmonkey.yaml` has vSphere or OLVM credentials:

```yaml
platforms:
  vsphere:
    server: "vcenter.example.com"
    username: "admin@vsphere.local"
    password: "password"
    insecure: true
  
  # OR
  
  olvm:
    url: "https://olvm.example.com/ovirt-engine/api"
    username: "admin@internal"
    password: "password"
    insecure: true
```

## Future Enhancements
1. Add WebSocket support for real-time status updates
2. Cache VM status with TTL to reduce Dora API calls
3. Add retry logic for failed power operations
4. Implement batch power operations for multiple VMs
