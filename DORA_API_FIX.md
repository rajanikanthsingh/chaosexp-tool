# Dora API Response Structure - Fix Summary

## Issue
The web UI was showing error: `'str' object has no attribute 'get'` when trying to load Dora VMs.

## Root Cause
The Dora API returns data in a specific nested structure that wasn't being parsed correctly:

```json
{
  "environment": "Dev",
  "hypervisors": {
    "items": [...]  // Array of hypervisor objects
  },
  "vms": {
    "items": [...]  // Array of VM objects
  }
}
```

The code was expecting `data['vms']` to be a list, but it's actually a dictionary with an `items` key.

## VM Object Structure
Each VM in the `items` array has these fields:
```json
{
  "name": "hostname",
  "path": "/ORA-DEV/ORA-DEV/...",
  "host": "/ORA-DEV/host/ORA-DEV/hostname",
  "os": "AlmaLinux:8.10",
  "cpus": 16,
  "memMb": 65536,
  "state": "poweredOn",
  "managedObjRef": "...",
  "cpuUsagePerc": 4,
  "memUsagePerc": 5.0
}
```

## Field Mapping
| UI Field | Dora API Field | Notes |
|----------|----------------|-------|
| name | `name` | Direct mapping |
| id | `managedObjRef` or `name` | Use managedObjRef if available |
| power_state | `state` | e.g., "poweredOn", "poweredOff" |
| hypervisor | `host` | Extract last part of path |
| cpu | `cpus` | Convert to string |
| memory | `memMb` | Convert to GB (divide by 1024) |
| guest_os | `os` | e.g., "AlmaLinux:8.10" |
| datacenter | (parameter) | From environment name |

## Fix Applied

### Before (Incorrect)
```python
vms_data = data.get('vms', [])
for vm in vms_data:
    # This failed because vms_data was a dict, not a list
    vm.get("name")
```

### After (Correct)
```python
vms_data = data.get('vms', {})

# Extract items array from dict
if isinstance(vms_data, dict) and 'items' in vms_data:
    vm_list = vms_data['items']
elif isinstance(vms_data, list):
    vm_list = vms_data
else:
    vm_list = []

# Transform each VM
for vm in vm_list:
    if isinstance(vm, dict):
        # Extract host name from path
        host_path = vm.get("host", "N/A")
        host_name = host_path.split('/')[-1] if '/' in host_path else host_path
        
        # Get memory in GB
        mem_mb = vm.get('memMb', 0)
        memory_str = f"{mem_mb / 1024:.1f} GB" if mem_mb else "N/A"
        
        vms.append({
            "name": vm.get("name", "N/A"),
            "id": vm.get("managedObjRef", vm.get("name", "N/A")),
            "power_state": vm.get("state", "unknown"),
            "hypervisor": host_name,
            "cpu": str(vm.get("cpus", 0)),
            "memory": memory_str,
            "guest_os": vm.get("os", "N/A"),
            "datacenter": environment
        })
```

## Changes Made

### 1. Flask Endpoint (`src/chaosmonkey/web/app.py`)
- ✅ Fixed VM extraction to use `vms['items']`
- ✅ Updated field mappings to match Dora API
- ✅ Added host path parsing (extract hostname from full path)
- ✅ Fixed memory conversion (memMb → GB)
- ✅ Changed default environment to "Dev"
- ✅ Added debug mode (`?debug=true`)

### 2. JavaScript (`src/chaosmonkey/web/static/app.js`)
- ✅ Changed default environment from "Paytv" to "Dev"

### 3. Debug Tools
- ✅ Created `test_dora_response.py` for testing
- ✅ Added detailed error logging

## Available Dora Environments
Based on the updated `dora/client.py`:
- Dev
- Oracle-Paytv
- Oracle-INT-MSP
- Oracle-PSR-Paytv
- Oracle-Paytv-staging
- DR-Paytv
- Arvig-Staging
- Arvig-Prod
- EPB-Staging
- EPB-Prod
- Lumos-Prod
- Comporium-Prod
- MSG-Prod

## Testing

### 1. Test via Script
```bash
python3 test_dora_response.py > response.tmp
```

### 2. Test via Web UI
1. Start web UI: `python3 run_web_ui.py`
2. Navigate to Nodes tab
3. Select "Dora VMs" from dropdown
4. Select "Dev" environment
5. Should now see VMs listed!

### 3. Test Debug Endpoint
```bash
curl "http://localhost:8080/api/discover/dora?environment=Dev&debug=true"
```

## Sample Output
When working correctly, the UI should show:

| Name | Power State | Hypervisor | CPU | Memory | Guest OS | Actions |
|------|-------------|------------|-----|--------|----------|---------|
| hostname | poweredOn | hostname | 16 | 64.0 GB | AlmaLinux:8.10 | [Start][Reboot][Stop] |
| biehd01p2.hostname | poweredOn | hostname | 16 | 64.0 GB | AlmaLinux:8.10 | [Start][Reboot][Stop] |

## Verification Checklist
- [x] Parse `vms['items']` correctly
- [x] Map Dora fields to UI fields
- [x] Extract hostname from full path
- [x] Convert memory MB to GB
- [x] Handle power states correctly
- [x] Default to "Dev" environment
- [x] Add error handling and logging
- [x] Test with actual Dora API

## Next Steps
1. Restart the web UI: `python3 run_web_ui.py`
2. Refresh the Nodes tab in your browser
3. Select "Dora VMs" and "Dev" environment
4. You should now see the VMs!

---

**Status:** ✅ **FIXED**
**Date:** October 10, 2025
