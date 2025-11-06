# VM Platform Integration - Quick Start

## Overview

ChaosMonkey now supports VM-based chaos experiments across multiple virtualization platforms:

- ✅ **OLVM/oVirt** - Red Hat Virtualization
- ✅ **VMware vSphere** - vCenter and ESXi
- ✅ **Dora API** - Centralized vSphere inventory

## Installation

```bash
# Install with all platform support
pip install -e '.[platforms]'

# Or install specific platforms
pip install -e '.[olvm]'     # OLVM only
pip install -e '.[vsphere]'  # vSphere only
```

## Quick Start

### 1. Configure Credentials

Create `.env` file:

```bash
# vSphere
VSPHERE_SERVER=vcenter.example.com
VSPHERE_USERNAME=administrator@vsphere.local
VSPHERE_PASSWORD=your_password

# OLVM
OLVM_URL=https://engine.example.com/ovirt-engine/api
OLVM_USERNAME=admin@internal
OLVM_PASSWORD=your_password
```

### 2. Discover VMs

```bash
# List VMs on vSphere
chaosmonkey platforms discover-vms --platform vsphere

# List VMs on OLVM
chaosmonkey platforms discover-vms --platform olvm --name "web-*"
```

### 3. Run Chaos Experiments

```bash
# Power off a VM (with graceful shutdown)
chaosmonkey platforms power-off web-01 --platform vsphere --graceful

# Reboot a VM
chaosmonkey platforms reboot web-01 --platform vsphere

# Power on a VM
chaosmonkey platforms power-on web-01 --platform vsphere
```

### 4. Execute Templated Experiments

```bash
chaosmonkey execute \
  --chaos-type vsphere-vm-poweroff \
  --override vm_name=web-01 \
  --override vsphere_server=vcenter.example.com
```

## Available Commands

### Discovery
- `platforms discover-vms` - Discover VMs on a platform
- `platforms vm-info` - Get detailed VM information
- `platforms dora-environments` - List Dora environments
- `platforms dora-discover` - Discover environment via Dora

### Power Operations
- `platforms power-on` - Power on a VM
- `platforms power-off` - Power off a VM
- `platforms reboot` - Reboot a VM

## Chaos Experiment Templates

- `olvm-vm-shutdown` - Power off VM on OLVM
- `vsphere-vm-poweroff` - Power off VM on vSphere
- `vsphere-vm-reboot` - Reboot VM on vSphere
- `olvm-vm-batch-shutdown` - Batch power off on OLVM

## Examples

### Example 1: Simulate VM Failure

```bash
# Power off a VM forcefully
chaosmonkey platforms power-off database-01 \
  --platform vsphere \
  --force \
  --timeout 60
```

### Example 2: Discover Production VMs

```bash
# Discover VMs in Production datacenter
chaosmonkey platforms discover-vms \
  --platform vsphere \
  --datacenter Production \
  --name "prod-*"
```

### Example 3: Dora Environment Discovery

```bash
# List available environments
chaosmonkey platforms dora-environments

# Discover specific environment
chaosmonkey platforms dora-discover "EPB-Prod" \
  --output environment_data.json
```

### Example 4: Custom Experiment

Create `vm_chaos.json`:

```json
{
  "version": "1.0.0",
  "title": "Database VM Failure Test",
  "method": [
    {
      "type": "action",
      "name": "Power off database VM",
      "provider": {
        "type": "python",
        "module": "chaosmonkey.stubs.actions",
        "func": "vm_power_off",
        "arguments": {
          "vm_name": "db-01",
          "platform_type": "vsphere",
          "graceful": false,
          "server": "${VSPHERE_SERVER}",
          "username": "${VSPHERE_USERNAME}",
          "password": "${VSPHERE_PASSWORD}"
        }
      }
    }
  ],
  "rollbacks": [
    {
      "type": "action",
      "name": "Restore VM",
      "provider": {
        "type": "python",
        "module": "chaosmonkey.stubs.actions",
        "func": "vm_power_on",
        "arguments": {
          "vm_name": "db-01",
          "platform_type": "vsphere",
          "server": "${VSPHERE_SERVER}",
          "username": "${VSPHERE_USERNAME}",
          "password": "${VSPHERE_PASSWORD}"
        }
      }
    }
  ]
}
```

Execute:

```bash
chaosmonkey execute --experiment vm_chaos.json
```

## Python API

```python
from chaosmonkey.platforms.vsphere import VSpherePlatform

# Connect and discover
with VSpherePlatform(
    server="vcenter.example.com",
    username="admin@vsphere.local",
    password="password"
) as platform:
    # Discover VMs
    vms = platform.discover_vms(name_pattern="web-*")
    
    # Power operations
    platform.power_off("web-01", graceful=True)
    platform.power_on("web-01")
    
    # Batch operations
    results = platform.batch_power_off(
        ["web-01", "web-02", "web-03"],
        graceful=True,
        parallel=3
    )
```

## Documentation

- **[VM Platforms Guide](docs/VM_PLATFORMS_GUIDE.md)** - Complete guide
- **[Architecture](docs/ARCHITECTURE_AND_IMPLEMENTATION.md)** - System design
- **[Main README](README.md)** - General documentation

## Supported Dora Environments

- Paytv
- Oracle-Paytv
- Oracle-INT-MSP
- Oracle-PSR-Paytv
- Oracle-Paytv-staging
- DR-Paytv
- Arvig-Staging / Arvig-Prod
- EPB-Staging / EPB-Prod
- Lumos-Prod
- Comporium-Prod
- MSG-Prod

## Security Notes

⚠️ **Important Security Practices:**

1. Never commit credentials to version control
2. Use `.env` files (already in `.gitignore`)
3. For production, use proper CA certificates (set `insecure=false`)
4. Create service accounts with minimal required permissions
5. Regularly rotate credentials

## Troubleshooting

### Connection Issues

**vSphere:**
```bash
# Test connection
python -c "from chaosmonkey.platforms.vsphere import VSpherePlatform; \
p = VSpherePlatform('vcenter.example.com', 'user', 'pass'); \
p.connect(); print('OK'); p.disconnect()"
```

**OLVM:**
```bash
# Test connection
python -c "from chaosmonkey.platforms.olvm import OLVMPlatform; \
p = OLVMPlatform('https://engine/api', 'admin@internal', 'pass'); \
p.connect(); print('OK'); p.disconnect()"
```

### Common Errors

| Error | Solution |
|-------|----------|
| `Import "ovirtsdk4" could not be resolved` | Run `pip install ovirt-engine-sdk-python` |
| `Import "pyVmomi" could not be resolved` | Run `pip install pyvmomi` |
| `OLVM configuration incomplete` | Set OLVM_URL, OLVM_USERNAME, OLVM_PASSWORD |
| `Invalid vSphere login credentials` | Check username format: `user@domain` |

## What's New

### v0.2.0 - VM Platform Support

**New Features:**
- ✨ Multi-platform virtualization support (OLVM, vSphere)
- ✨ VM discovery with filtering
- ✨ Power operations (on, off, reboot, suspend)
- ✨ Batch operations with parallel execution
- ✨ Dora API integration for environment discovery
- ✨ 4 new chaos experiment templates
- ✨ CLI commands for platform operations
- ✨ Comprehensive Python API

**Architecture:**
- 🏗️ Abstract `Platform` interface
- 🏗️ Platform-specific implementations
- 🏗️ PlatformOrchestrator for unified management
- 🏗️ Extended configuration system

## Contributing

Contributions welcome! Areas for improvement:

- [ ] Additional platform support (Proxmox, OpenStack, etc.)
- [ ] More chaos experiment templates
- [ ] Web UI integration for VM operations
- [ ] Enhanced Dora API features
- [ ] Performance optimizations
- [ ] Additional test coverage

## License

Apache-2.0
