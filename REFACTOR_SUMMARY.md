# Full Refactor Complete: VM Platform Integration

## Summary

Successfully completed a full refactor and integration of your VM platform scripts into the ChaosMonkey toolkit. Your standalone scripts have been transformed into a unified, extensible platform architecture that seamlessly integrates with the existing chaos engineering framework.

## What Was Built

### 1. **Platform Architecture** ✅

**Created:**
- `src/chaosmonkey/platforms/` - New package for multi-platform support
- `base.py` - Abstract `Platform` interface with normalized `VMInfo` and `VMPowerState` models
- Clean separation of concerns with context manager support

**Key Features:**
- Platform-agnostic interface
- Normalized data models across platforms
- Built-in batch operations with parallel execution
- Thread-safe connection management

### 2. **OLVM/oVirt Integration** ✅

**Refactored from:** `olvm_vm_power_batch.py`

**Created:** `src/chaosmonkey/platforms/olvm/client.py`

**Capabilities:**
- Full OLVM/oVirt SDK integration
- VM discovery with filtering
- Power operations (on, off, reboot, suspend)
- Graceful shutdown with automatic fallback to hard stop
- Batch operations with configurable parallelism
- Comprehensive error handling

**Example:**
```python
from chaosmonkey.platforms.olvm import OLVMPlatform

with OLVMPlatform(url="...", username="...", password="...") as platform:
    vms = platform.discover_vms(name_pattern="web-*")
    platform.power_off("web-01", graceful=True)
```

### 3. **VMware vSphere Integration** ✅

**Refactored from:** `vsphere_vm_power.py`

**Created:** 
- `src/chaosmonkey/platforms/vsphere/client.py` - Main client
- `src/chaosmonkey/platforms/vsphere/discovery.py` - Discovery helpers

**Capabilities:**
- PyVmomi integration for vCenter/ESXi
- VM discovery with datacenter filtering
- Power operations with VMware Tools integration
- Graceful operations with automatic fallback
- Rich VM metadata (tools status, guest OS, resources)
- Batch operations

**Example:**
```python
from chaosmonkey.platforms.vsphere import VSpherePlatform, VSphereDiscovery

with VSpherePlatform(server="...", username="...", password="...") as platform:
    discovery = VSphereDiscovery(platform)
    summary = discovery.get_environment_summary()
    platform.power_off("web-01", graceful=True)
```

### 4. **Dora API Integration** ✅

**Refactored from:** `fetch_vsphere_env_data.py`

**Created:** `src/chaosmonkey/platforms/dora/client.py`

**Capabilities:**
- Complete Dora API client
- Pre-configured 13 environment mappings
- Authentication handling
- Hypervisor and VM discovery
- Flexible host filtering modes

**Environments:**
- Paytv, Oracle-Paytv, Oracle-INT-MSP, Oracle-PSR-Paytv
- Oracle-Paytv-staging, DR-Paytv
- Arvig-Staging, Arvig-Prod
- EPB-Staging, EPB-Prod
- Lumos-Prod, Comporium-Prod, MSG-Prod

**Example:**
```python
from chaosmonkey.platforms.dora import DoraClient

client = DoraClient()
data = client.get_environment_data("EPB-Prod", username="...", password="...")
```

### 5. **Chaos Toolkit Integration** ✅

**Extended:** `src/chaosmonkey/stubs/actions.py`

**New Actions:**
- `vm_power_off()` - Power off a VM
- `vm_power_on()` - Power on a VM
- `vm_reboot()` - Reboot a VM
- `vm_batch_power_off()` - Batch power operations

**New Templates:**
- `olvm_vm_shutdown.json` - OLVM power off
- `vsphere_vm_poweroff.json` - vSphere power off
- `vsphere_vm_reboot.json` - vSphere reboot
- `olvm_vm_batch_shutdown.json` - OLVM batch operations

**Updated:** `src/chaosmonkey/core/experiments.py` - Template registry

### 6. **Configuration System** ✅

**Extended:** `src/chaosmonkey/config.py`

**New Settings Classes:**
- `OLVMSettings` - OLVM configuration
- `VSphereSettings` - vSphere configuration
- `DoraSettings` - Dora API configuration
- `PlatformSettings` - Aggregate platform config

**Supports:**
- Environment variables (`.env` file)
- YAML/JSON configuration files
- Runtime configuration

**Created:** `.env.platforms.example` - Configuration template

### 7. **Platform Orchestrator** ✅

**Created:** `src/chaosmonkey/core/platform_orchestrator.py`

**Features:**
- Unified interface for all platforms
- Client lifecycle management
- Discovery operations
- Power operations
- Dora integration
- Configuration-driven client creation

**Example:**
```python
from chaosmonkey.core.platform_orchestrator import PlatformOrchestrator

orchestrator = PlatformOrchestrator(settings)
vms = orchestrator.discover_vms("vsphere", name_pattern="web-*")
orchestrator.power_off_vm("vsphere", "web-01", graceful=True)
```

### 8. **CLI Commands** ✅

**Extended:** `src/chaosmonkey/cli.py`

**New Command Group:** `chaosmonkey platforms`

**Commands:**
```bash
# Discovery
chaosmonkey platforms discover-vms --platform vsphere
chaosmonkey platforms vm-info web-01 --platform vsphere
chaosmonkey platforms dora-environments
chaosmonkey platforms dora-discover EPB-Prod

# Power Operations
chaosmonkey platforms power-on web-01 --platform vsphere
chaosmonkey platforms power-off web-01 --platform vsphere --graceful
chaosmonkey platforms reboot web-01 --platform vsphere
```

### 9. **Dependencies** ✅

**Updated:** `pyproject.toml`

**New Optional Dependencies:**
```toml
[project.optional-dependencies]
olvm = ["ovirt-engine-sdk-python>=4.6,<5.0"]
vsphere = ["pyvmomi>=8.0,<9.0"]
platforms = [both]
```

**Installation:**
```bash
pip install -e '.[platforms]'  # Install all
pip install -e '.[olvm]'       # OLVM only
pip install -e '.[vsphere]'    # vSphere only
```

### 10. **Documentation** ✅

**Created:**
- `docs/VM_PLATFORMS_GUIDE.md` - Comprehensive 400+ line guide
- `VM_PLATFORMS_QUICKSTART.md` - Quick start guide
- `.env.platforms.example` - Configuration example

**Covers:**
- Architecture overview
- Installation instructions
- Configuration guide
- CLI usage examples
- Python API examples
- Troubleshooting
- Security best practices

## Project Structure

```
src/chaosmonkey/
├── platforms/                          # NEW: Multi-platform support
│   ├── __init__.py
│   ├── base.py                         # Platform interface & models
│   ├── olvm/
│   │   ├── __init__.py
│   │   └── client.py                   # OLVM implementation
│   ├── vsphere/
│   │   ├── __init__.py
│   │   ├── client.py                   # vSphere implementation
│   │   └── discovery.py                # Discovery helpers
│   └── dora/
│       ├── __init__.py
│       └── client.py                   # Dora API client
├── core/
│   ├── platform_orchestrator.py        # NEW: Platform orchestrator
│   ├── experiments.py                  # UPDATED: New templates
│   └── orchestrator.py                 # Existing Nomad orchestrator
├── experiments/templates/
│   ├── olvm_vm_shutdown.json           # NEW
│   ├── vsphere_vm_poweroff.json        # NEW
│   ├── vsphere_vm_reboot.json          # NEW
│   └── olvm_vm_batch_shutdown.json     # NEW
├── stubs/
│   └── actions.py                      # UPDATED: VM actions
├── config.py                           # UPDATED: Platform config
└── cli.py                              # UPDATED: Platform commands

docs/
├── VM_PLATFORMS_GUIDE.md               # NEW: Complete guide
└── ... (existing docs)

VM_PLATFORMS_QUICKSTART.md              # NEW: Quick start
.env.platforms.example                  # NEW: Config template
pyproject.toml                          # UPDATED: Dependencies
```

## Key Design Patterns

### 1. **Abstract Base Class Pattern**
All platforms implement the `Platform` interface, ensuring consistent behavior.

### 2. **Context Manager Pattern**
Platforms support `with` statements for automatic resource management:
```python
with VSpherePlatform(...) as platform:
    platform.power_off("vm-01")
# Automatically disconnects
```

### 3. **Factory Pattern**
`PlatformOrchestrator` creates platform clients based on configuration.

### 4. **Strategy Pattern**
Platform-specific implementations while maintaining unified interface.

### 5. **Lazy Initialization**
Clients are created on first use, not at startup.

## Usage Examples

### Example 1: Discover and Power Off VMs

```bash
# Discover VMs
chaosmonkey platforms discover-vms --platform vsphere --name "web-*"

# Power off specific VM
chaosmonkey platforms power-off web-01 --platform vsphere --graceful
```

### Example 2: Chaos Experiment

```bash
chaosmonkey execute \
  --chaos-type vsphere-vm-poweroff \
  --override vm_name=database-01 \
  --override vsphere_server=vcenter.example.com
```

### Example 3: Python API

```python
from chaosmonkey.config import load_settings
from chaosmonkey.core.platform_orchestrator import PlatformOrchestrator

settings = load_settings(None)
orchestrator = PlatformOrchestrator(settings)

# Discover
vms = orchestrator.discover_vms("vsphere", datacenter="Production")

# Execute chaos
orchestrator.power_off_vm("vsphere", "web-01", graceful=False)
```

### Example 4: Batch Operations

```python
from chaosmonkey.platforms.olvm import OLVMPlatform

with OLVMPlatform(...) as platform:
    results = platform.batch_power_off(
        ["vm-01", "vm-02", "vm-03"],
        graceful=True,
        parallel=3
    )
```

## Testing the Integration

### 1. Install Dependencies

```bash
cd /Users/inderdeep.sidhu/PycharmProjects/chaosmonkey

# Install with platform support
pip install -e '.[platforms]'
```

### 2. Configure Credentials

```bash
# Copy example config
cp .env.platforms.example .env

# Edit with your credentials
nano .env
```

### 3. Test Discovery

```bash
# Test vSphere discovery
chaosmonkey platforms discover-vms --platform vsphere

# Test OLVM discovery
chaosmonkey platforms discover-vms --platform olvm

# Test Dora
chaosmonkey platforms dora-environments
```

### 4. Test Power Operations

```bash
# Get VM info
chaosmonkey platforms vm-info test-vm --platform vsphere

# Power operations (use test VM!)
chaosmonkey platforms power-off test-vm --platform vsphere --graceful
chaosmonkey platforms power-on test-vm --platform vsphere
```

## Migration from Original Scripts

### Before (olvm_vm_power_batch.py):
```bash
python olvm_vm_power_batch.py \
  --engine-url https://engine/api \
  --username admin@internal \
  --password pass \
  --action shutdown \
  --vms "vm1,vm2,vm3"
```

### After (Integrated):
```bash
# CLI
chaosmonkey platforms power-off vm1 --platform olvm --graceful

# Or as chaos experiment
chaosmonkey execute --chaos-type olvm-vm-shutdown \
  --override vm_name=vm1
```

### Before (vsphere_vm_power.py):
```bash
python vsphere_vm_power.py \
  --server vcenter.example.com \
  --user admin@vsphere.local \
  --password pass \
  --vm MyVM \
  --action shutdown
```

### After (Integrated):
```bash
# CLI
chaosmonkey platforms power-off MyVM --platform vsphere

# Or Python API
from chaosmonkey.platforms.vsphere import VSpherePlatform
with VSpherePlatform(...) as p:
    p.power_off("MyVM")
```

## Benefits of the Refactor

### ✅ **Code Reusability**
- Shared platform interface
- Common VMInfo model
- Reusable batch operations

### ✅ **Maintainability**
- Centralized configuration
- Single source of truth
- Consistent error handling

### ✅ **Extensibility**
- Easy to add new platforms
- Plugin architecture
- Template-based experiments

### ✅ **Integration**
- Works with Chaos Toolkit
- CLI commands
- Python API
- Web UI ready (future)

### ✅ **Testing**
- Isolated platform implementations
- Mockable interfaces
- Unit test friendly

### ✅ **Security**
- Environment-based credentials
- No hardcoded secrets
- Optional TLS verification

## Next Steps

### Immediate Actions:

1. **Install and test:**
   ```bash
   pip install -e '.[platforms]'
   chaosmonkey platforms discover-vms --platform vsphere
   ```

2. **Configure your environments:**
   - Copy `.env.platforms.example` to `.env`
   - Add your credentials
   - Test connections

3. **Run your first experiment:**
   ```bash
   chaosmonkey execute --chaos-type vsphere-vm-poweroff \
     --override vm_name=test-vm
   ```

### Future Enhancements:

- [ ] Add web UI integration for VM operations
- [ ] Implement VM snapshot support
- [ ] Add resource monitoring during experiments
- [ ] Create more experiment templates
- [ ] Add Proxmox/OpenStack support
- [ ] Implement VM tagging/labeling
- [ ] Add cost estimation for chaos experiments
- [ ] Create experiment scheduler

## Files Changed/Created

**Created (13 files):**
1. `src/chaosmonkey/platforms/__init__.py`
2. `src/chaosmonkey/platforms/base.py`
3. `src/chaosmonkey/platforms/olvm/__init__.py`
4. `src/chaosmonkey/platforms/olvm/client.py`
5. `src/chaosmonkey/platforms/vsphere/__init__.py`
6. `src/chaosmonkey/platforms/vsphere/client.py`
7. `src/chaosmonkey/platforms/vsphere/discovery.py`
8. `src/chaosmonkey/platforms/dora/__init__.py`
9. `src/chaosmonkey/platforms/dora/client.py`
10. `src/chaosmonkey/core/platform_orchestrator.py`
11. `src/chaosmonkey/experiments/templates/olvm_vm_shutdown.json`
12. `src/chaosmonkey/experiments/templates/vsphere_vm_poweroff.json`
13. `src/chaosmonkey/experiments/templates/vsphere_vm_reboot.json`
14. `src/chaosmonkey/experiments/templates/olvm_vm_batch_shutdown.json`
15. `.env.platforms.example`
16. `docs/VM_PLATFORMS_GUIDE.md`
17. `VM_PLATFORMS_QUICKSTART.md`

**Modified (4 files):**
1. `src/chaosmonkey/stubs/actions.py` - Added VM actions
2. `src/chaosmonkey/core/experiments.py` - Added templates
3. `src/chaosmonkey/config.py` - Added platform config
4. `src/chaosmonkey/cli.py` - Added platform commands
5. `pyproject.toml` - Added dependencies

## Conclusion

Your standalone VM management scripts have been successfully transformed into a robust, enterprise-ready platform integration within the ChaosMonkey chaos engineering toolkit. The refactored code maintains all original functionality while adding:

- ✨ **Unified interface** across platforms
- ✨ **Enhanced error handling** and logging
- ✨ **Batch operations** with parallelism
- ✨ **CLI commands** for easy access
- ✨ **Chaos experiments** integration
- ✨ **Configuration management** system
- ✨ **Comprehensive documentation**

The architecture is extensible, maintainable, and follows industry best practices for chaos engineering tools.

**Ready to cause some (controlled) chaos! 🐵💥**
