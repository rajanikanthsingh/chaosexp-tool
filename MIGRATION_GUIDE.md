# Migration Guide: Standalone Scripts → ChaosMonkey Integration

This guide helps you migrate from the standalone VM management scripts to the integrated ChaosMonkey platform.

## Quick Reference

| Old Script | New Command | New Python API |
|------------|-------------|----------------|
| `olvm_vm_power_batch.py --action start` | `chaosmonkey platforms power-on` | `platform.power_on()` |
| `vsphere_vm_power.py --action poweron` | `chaosmonkey platforms power-on` | `platform.power_on()` |
| `fetch_vsphere_env_data.py` | `chaosmonkey platforms dora-discover` | `DoraClient.get_environment_data()` |

## Installation

### Old Way
```bash
pip install ovirtsdk4 pyvmomi requests
python olvm_vm_power_batch.py --help
```

### New Way
```bash
pip install -e '.[platforms]'
chaosmonkey platforms --help
```

## Configuration Migration

### Old Way: Command-line Arguments
```bash
python olvm_vm_power_batch.py \
  --engine-url https://engine.example.com/ovirt-engine/api \
  --username admin@internal \
  --password 'MyPassword123' \
  --action shutdown \
  --vm-name web-01
```

### New Way: Environment Variables + CLI
```bash
# Set once in .env
OLVM_URL=https://engine.example.com/ovirt-engine/api
OLVM_USERNAME=admin@internal
OLVM_PASSWORD=MyPassword123

# Use simple commands
chaosmonkey platforms power-off web-01 --platform olvm
```

### New Way: Configuration File
```yaml
# chaosmonkey.yaml
platforms:
  olvm:
    url: https://engine.example.com/ovirt-engine/api
    username: admin@internal
    password: MyPassword123
```

## Command Migration Examples

### Example 1: OLVM Single VM Shutdown

#### Old
```bash
python olvm_vm_power_batch.py \
  --engine-url https://engine.example.com/ovirt-engine/api \
  --username admin@internal \
  --password 'MyPassword' \
  --action shutdown \
  --vm-name web-01 \
  --force
```

#### New
```bash
chaosmonkey platforms power-off web-01 \
  --platform olvm \
  --force
```

### Example 2: OLVM Batch Operations

#### Old
```bash
python olvm_vm_power_batch.py \
  --engine-url https://engine.example.com/ovirt-engine/api \
  --username admin@internal \
  --password 'MyPassword' \
  --action shutdown \
  --vms "web-01,web-02,web-03" \
  --parallel 3
```

#### New (Python API)
```python
from chaosmonkey.platforms.olvm import OLVMPlatform

with OLVMPlatform(url="...", username="...", password="...") as platform:
    results = platform.batch_power_off(
        ["web-01", "web-02", "web-03"],
        graceful=True,
        parallel=3
    )
    for vm, success in results.items():
        print(f"{vm}: {'✓' if success else '✗'}")
```

### Example 3: vSphere Power Operations

#### Old
```bash
python vsphere_vm_power.py \
  --server vcenter.example.com \
  --user administrator@vsphere.local \
  --password 'MyPassword' \
  --vm MyVM \
  --action shutdown
```

#### New
```bash
chaosmonkey platforms power-off MyVM \
  --platform vsphere \
  --graceful
```

### Example 4: vSphere Discovery

#### Old (Manual scripting)
```python
from pyVim import connect
si = connect.SmartConnect(...)
# Manual discovery code
```

#### New
```bash
# CLI
chaosmonkey platforms discover-vms --platform vsphere --name "web-*"

# Python API
from chaosmonkey.platforms.vsphere import VSpherePlatform
with VSpherePlatform(...) as platform:
    vms = platform.discover_vms(name_pattern="web-*")
```

### Example 5: Dora Environment Discovery

#### Old
```bash
python fetch_vsphere_env_data.py Paytv \
  --username dora \
  --password '%Devops12345678&' \
  --dora-host hostname \
  --out-dir /var/www/cgi-bin/scripts \
  --hostfilter empty
```

#### New
```bash
chaosmonkey platforms dora-discover Paytv \
  --username dora \
  --password '%Devops12345678&' \
  --output environment_data.json
```

## Python API Migration

### Old: Direct SDK Usage

#### OLVM
```python
import ovirtsdk4 as sdk

# Manual connection
conn = sdk.Connection(
    url="https://engine/api",
    username="admin@internal",
    password="password"
)

# Manual VM operations
vms_svc = conn.system_service().vms_service()
matches = vms_svc.list(search="name=web-01")
vm = matches[0]
vm_svc = vms_svc.vm_service(vm.id)
vm_svc.stop()

conn.close()
```

#### New
```python
from chaosmonkey.platforms.olvm import OLVMPlatform

with OLVMPlatform(url="...", username="...", password="...") as platform:
    platform.power_off("web-01")
# Automatically handles connection/disconnection
```

### Old: vSphere Direct SDK

#### Old
```python
from pyVim import connect
from pyVmomi import vim

si = connect.SmartConnect(host="vcenter", user="admin", pwd="pass")
content = si.RetrieveContent()

# Manual VM search
container = content.viewManager.CreateContainerView(...)
for vm in container.view:
    if vm.name == "web-01":
        task = vm.PowerOffVM_Task()
        # Manual task waiting...

connect.Disconnect(si)
```

#### New
```python
from chaosmonkey.platforms.vsphere import VSpherePlatform

with VSpherePlatform(server="vcenter", username="admin", password="pass") as platform:
    platform.power_off("web-01")
# Handles all complexity
```

## Feature Comparison

| Feature | Old Scripts | New Integration |
|---------|-------------|-----------------|
| VM Discovery | Manual | ✅ Built-in with filtering |
| Power Operations | ✅ Yes | ✅ Yes (enhanced) |
| Batch Operations | ✅ OLVM only | ✅ Both platforms |
| Error Handling | Basic | ✅ Comprehensive |
| Retry Logic | Manual | ✅ Built-in |
| Logging | Print statements | ✅ Rich logging |
| Configuration | CLI args | ✅ Env vars + config files |
| CLI Interface | Separate scripts | ✅ Unified `chaosmonkey` command |
| Python API | Raw SDK | ✅ Clean, unified API |
| Chaos Experiments | ❌ No | ✅ Full integration |
| Context Managers | ❌ No | ✅ Yes |
| Type Hints | Partial | ✅ Full |
| Documentation | Docstrings | ✅ Comprehensive docs |

## New Capabilities

### 1. Unified Discovery
```bash
# Discover across platforms with consistent output
chaosmonkey platforms discover-vms --platform vsphere
chaosmonkey platforms discover-vms --platform olvm
```

### 2. Detailed VM Information
```bash
chaosmonkey platforms vm-info web-01 --platform vsphere
```

Output:
```
VM Information: web-01
  Platform:     vsphere
  Power State:  powered_on
  Host:         esx-01.example.com
  CPUs:         4
  Memory:       8192MB
  Guest OS:     Ubuntu Linux (64-bit)
```

### 3. Chaos Experiments
```bash
# Execute templated experiments
chaosmonkey execute --chaos-type vsphere-vm-poweroff \
  --override vm_name=web-01
```

### 4. Web UI Integration (Future)
The new architecture supports future web UI integration for visual chaos management.

### 5. Automated Rollbacks
```json
{
  "method": [{"type": "action", "provider": {...}}],
  "rollbacks": [{"type": "action", "provider": {...}}]
}
```

## Breaking Changes

### 1. Import Paths Changed

#### Old
```python
# Direct SDK imports
import ovirtsdk4 as sdk
from pyVmomi import vim
```

#### New
```python
# Use ChaosMonkey platforms
from chaosmonkey.platforms.olvm import OLVMPlatform
from chaosmonkey.platforms.vsphere import VSpherePlatform
```

### 2. Configuration Method

#### Old
All configuration via command-line arguments

#### New
Prefer environment variables or config files, with CLI overrides

### 3. Error Handling

#### Old
```python
try:
    vm_svc.stop()
except Exception as e:
    print(f"Error: {e}")
```

#### New
```python
try:
    platform.power_off("vm-01")
except RuntimeError as e:
    # More specific exceptions
    logger.error(f"Power off failed: {e}")
```

## Migration Checklist

- [ ] Install new dependencies: `pip install -e '.[platforms]'`
- [ ] Create `.env` file from `.env.platforms.example`
- [ ] Test connection: `chaosmonkey platforms discover-vms --platform vsphere`
- [ ] Update automation scripts to use new CLI commands
- [ ] Migrate Python code to use new API
- [ ] Update documentation references
- [ ] Test chaos experiments
- [ ] Remove old standalone scripts (optional)

## Troubleshooting Migration

### Issue: Import errors

**Old scripts work, new integration doesn't**

```bash
# Solution: Install platform dependencies
pip install -e '.[platforms]'
```

### Issue: Authentication fails

**Credentials worked before, fail now**

```bash
# Check environment variables are loaded
python -c "import os; print(os.getenv('VSPHERE_SERVER'))"

# Or use .env file
cat .env | grep VSPHERE
```

### Issue: VM not found

**VM found in old script, not in new**

```python
# Check discovery works
vms = platform.discover_vms()
print([vm.name for vm in vms])
```

### Issue: Timeout errors

**Operations were working, now timeout**

```bash
# Increase timeout
chaosmonkey platforms power-off vm-01 --platform vsphere --timeout 600
```

## Support

For issues during migration:

1. Check documentation: `docs/VM_PLATFORMS_GUIDE.md`
2. Review examples: `VM_PLATFORMS_QUICKSTART.md`
3. Test connections with individual Python scripts
4. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## Keeping Old Scripts (Optional)

If you want to keep old scripts for backup:

```bash
mkdir -p scripts/legacy
mv olvm_vm_power_batch.py scripts/legacy/
mv vsphere_vm_power.py scripts/legacy/
mv fetch_vsphere_env_data.py scripts/legacy/
```

The new integration provides all functionality plus more!

## Benefits of Migration

✅ **Less code to maintain** - Unified interface  
✅ **Better error handling** - Comprehensive exception handling  
✅ **Easier configuration** - Environment variables & config files  
✅ **More features** - Chaos experiments, batch ops, discovery  
✅ **Better testing** - Unit test friendly architecture  
✅ **Future-proof** - Easy to extend with new platforms  
✅ **Documentation** - Comprehensive guides and examples  

---

**Ready to migrate? Start with `pip install -e '.[platforms]'`!**
