# VM Platform Integration: Multi-Cloud Chaos Engineering Support

## 🎯 Overview

This PR adds comprehensive multi-platform VM support to ChaosMonkey, enabling chaos engineering experiments across OLVM/oVirt, VMware vSphere, and Dora API environments. This extends the existing Nomad-focused chaos toolkit with cloud-agnostic virtual machine power management capabilities.

## 🚀 What's New

### Core Features

- **Multi-Platform VM Support**: Unified interface for OLVM/oVirt and VMware vSphere
- **Dora API Integration**: Centralized VM discovery across 13 pre-configured environments
- **VM Power Management**: Power on/off, graceful shutdown, reboot operations
- **Batch Operations**: Parallel VM power operations with configurable concurrency
- **Platform Orchestrator**: Unified lifecycle management across all platforms
- **Chaos Toolkit Integration**: 4 new VM-specific experiment templates

### New Modules

#### 1. **Platform Package** (`src/chaosmonkey/platforms/`)
   - **Base Interface**: Abstract `Platform` class with standardized VM operations
   - **OLVM Client**: Complete oVirt SDK integration with batch operations
   - **vSphere Client**: PyVmomi integration with graceful shutdown support
   - **vSphere Discovery**: Pre-configured for 13 production environments
   - **Dora Client**: API integration for multi-environment VM discovery

#### 2. **CLI Commands** (`chaosmonkey platforms`)
   ```bash
   chaosmonkey platforms discover-vms --platform vsphere
   chaosmonkey platforms vm-info <vm-name> --platform vsphere
   chaosmonkey platforms power-on <vm-name> --platform vsphere
   chaosmonkey platforms power-off <vm-name> --platform vsphere --graceful
   chaosmonkey platforms reboot <vm-name> --platform vsphere
   chaosmonkey platforms dora-environments
   chaosmonkey platforms dora-discover <environment>
   ```

#### 3. **Chaos Experiment Templates**
   - `olvm_vm_shutdown.json` - OLVM VM graceful shutdown
   - `olvm_vm_batch_shutdown.json` - Batch OLVM VM operations
   - `vsphere_vm_poweroff.json` - vSphere VM power off
   - `vsphere_vm_reboot.json` - vSphere VM reboot

#### 4. **Configuration Extensions**
   - Added `OLVMSettings`, `VSphereSettings`, `DoraSettings`
   - Environment variable support via `.env` file
   - YAML/JSON configuration file support

## 📁 Files Changed

### Added (18 files)
- **Platform Implementations**: 9 new Python modules
- **Experiment Templates**: 4 Chaos Toolkit JSON templates
- **Documentation**: 5 comprehensive guides
- **Configuration**: `.env.platforms.example` template

### Modified (5 files)
- `pyproject.toml` - Added optional dependencies `[olvm]`, `[vsphere]`, `[platforms]`
- `src/chaosmonkey/cli.py` - Added `platforms` command group
- `src/chaosmonkey/config.py` - Extended with platform settings
- `src/chaosmonkey/core/experiments.py` - Added VM experiment templates
- `src/chaosmonkey/stubs/actions.py` - Added VM power action functions

## 📖 Documentation

### New Documentation Files
1. **`HOW_TO_RUN.md`** - Complete project setup and usage guide
2. **`DORA_MODULE_GUIDE.md`** - Comprehensive Dora API documentation
3. **`docs/VM_PLATFORMS_GUIDE.md`** - 400+ line complete platform guide
4. **`VM_PLATFORMS_QUICKSTART.md`** - Quick start guide
5. **`REFACTOR_SUMMARY.md`** - Technical architecture summary
6. **`MIGRATION_GUIDE.md`** - Migration from standalone scripts

## 🔧 Technical Details

### Architecture
- **Abstract Base Class**: `Platform` interface for all implementations
- **Context Manager Protocol**: Automatic connection/disconnection handling
- **Normalized Data Models**: `VMInfo` dataclass, `VMPowerState` enum
- **Configuration System**: Pydantic models with environment variable support
- **Dependency Management**: Optional extras to keep base installation lightweight

### Dependencies
```toml
[project.optional-dependencies]
olvm = ["ovirt-engine-sdk-python>=4.6"]
vsphere = ["pyvmomi>=8.0"]
platforms = ["ovirt-engine-sdk-python>=4.6,<5.0", "pyvmomi>=8.0,<9.0"]
```

### Supported Operations
- **Discovery**: List all VMs with filters (name, datacenter, cluster)
- **Information**: Get detailed VM metadata (state, host, resources)
- **Power On**: Start VMs with wait-for-ready support
- **Power Off**: Graceful shutdown with timeout or hard power off
- **Reboot**: Graceful reboot or hard reset
- **Batch Operations**: Parallel operations with configurable concurrency

## 🌍 Dora Integration

### Supported Environments (13)
- **Paytv**: Paytv, Oracle-Paytv, DR-Paytv
- **Production**: Arvig-Prod, EPB-Prod, Lumos-Prod, Comporium-Prod, MSG-Prod, Liberty-Prod, Midco-Prod
- **Staging**: Arvig-Staging, EPB-Staging, Midco-Staging

### Dora Features
- Centralized VM/hypervisor discovery without direct vCenter access
- Multi-environment inventory reporting
- Pre-chaos validation of target VMs
- Integration with direct vSphere connections for validation

## 🧪 Testing

### Manual Testing
```bash
# Install with platform support
pip install -e '.[platforms]'

# Configure credentials
cp .env.platforms.example .env
# Edit .env with your credentials

# Test discovery
chaosmonkey platforms discover-vms --platform vsphere

# Test power operations
chaosmonkey platforms vm-info test-vm-01 --platform vsphere
chaosmonkey platforms power-off test-vm-01 --platform vsphere --graceful

# Test Dora
chaosmonkey platforms dora-environments
chaosmonkey platforms dora-discover "Paytv"
```

### Python API Testing
```python
from chaosmonkey.config import load_settings
from chaosmonkey.core.platform_orchestrator import PlatformOrchestrator

settings = load_settings(None)
orchestrator = PlatformOrchestrator(settings)

# Discover VMs
vms = orchestrator.discover_vms("vsphere")
print(f"Found {len(vms)} VMs")

# Power operations
orchestrator.power_off_vm("vsphere", "test-vm", graceful=True)
orchestrator.power_on_vm("vsphere", "test-vm")
```

## ✅ Checklist

- [x] Added platform abstraction layer with base interface
- [x] Implemented OLVM/oVirt platform client
- [x] Implemented VMware vSphere platform client
- [x] Implemented Dora API client
- [x] Added platform orchestrator for unified management
- [x] Extended CLI with `platforms` command group
- [x] Created 4 Chaos Toolkit experiment templates
- [x] Extended configuration system with platform settings
- [x] Added optional dependencies to pyproject.toml
- [x] Created comprehensive documentation (5 guides)
- [x] Added configuration template (.env.platforms.example)
- [x] Tested CLI commands manually
- [x] Tested Python API programmatically

## 🎓 Usage Examples

### CLI Usage
```bash
# Discover all VMs
chaosmonkey platforms discover-vms --platform vsphere

# Get VM details
chaosmonkey platforms vm-info web-01 --platform vsphere

# Graceful shutdown
chaosmonkey platforms power-off web-01 --platform vsphere --graceful --timeout 300

# Discover via Dora
chaosmonkey platforms dora-discover "EPB-Prod" --output inventory.json
```

### Python Usage
```python
from chaosmonkey.platforms.vsphere import VSpherePlatform

# Using context manager
with VSpherePlatform(server="vcenter.example.com", 
                     username="admin", 
                     password="secret") as platform:
    # Discover VMs
    vms = platform.discover_vms(name_pattern="web-*")
    
    # Power operations
    platform.power_off("web-01", graceful=True)
    platform.power_on("web-01")
```

### Chaos Experiment
```bash
# Run VM power off experiment
chaosmonkey execute \
  --chaos-type vsphere-vm-poweroff \
  --override vm_name=web-01 \
  --override graceful=true
```

## 🔒 Security Considerations

- Credentials stored in `.env` file (not committed to git)
- Support for insecure SSL connections (useful for testing)
- Environment variable isolation per platform
- No hardcoded credentials in codebase

## 📊 Impact

### Benefits
- **Unified Interface**: Single API for multiple VM platforms
- **Extensible**: Easy to add new platform implementations
- **Production-Ready**: Graceful operations with timeout handling
- **Well-Documented**: 5 comprehensive guides covering all aspects
- **Backwards Compatible**: Doesn't affect existing Nomad functionality

### Backwards Compatibility
- ✅ All existing Nomad features unchanged
- ✅ New dependencies are optional extras
- ✅ Base installation remains lightweight
- ✅ Existing CLI commands unaffected

## 🚦 Breaking Changes

**None** - This is purely additive functionality with optional dependencies.

## 📝 Migration Notes

For users migrating from standalone scripts (olvm_vm_power_batch.py, vsphere_vm_power.py, fetch_vsphere_env_data.py), see `MIGRATION_GUIDE.md` for detailed migration instructions.

## 🔮 Future Enhancements

Potential future additions:
- [ ] AWS EC2 platform support
- [ ] Azure VM platform support
- [ ] Google Cloud Platform support
- [ ] Kubernetes pod chaos operations
- [ ] Advanced scheduling for chaos experiments
- [ ] Web UI for VM power management
- [ ] Metrics collection and reporting
- [ ] Integration tests with mock platforms

## 📚 Related Issues

Closes #N/A (this adds new functionality requested offline)

## 👥 Reviewers

@xperi-tmis/team

---

## 💡 How to Review

1. **Check Documentation**: Start with `HOW_TO_RUN.md` for overview
2. **Review Architecture**: See `REFACTOR_SUMMARY.md` for technical details
3. **Test Locally**: Follow installation steps in `HOW_TO_RUN.md`
4. **Try Examples**: Use sample code from `VM_PLATFORMS_QUICKSTART.md`
5. **Validate Dora**: Check `DORA_MODULE_GUIDE.md` for Dora-specific features

---

**Ready to merge** ✨
