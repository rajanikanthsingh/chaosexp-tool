# VM Platform Integration Guide

This guide covers the VM platform integration for ChaosMonkey, enabling chaos experiments on OLVM/oVirt and VMware vSphere environments.

## Overview

ChaosMonkey now supports VM-based chaos experiments across multiple virtualization platforms:

- **OLVM/oVirt**: Red Hat Virtualization and oVirt-based environments
- **VMware vSphere**: vCenter and ESXi environments
- **Dora API**: Centralized vSphere inventory and management

## Architecture

### Platform Abstraction Layer

All platform integrations implement a common `Platform` interface:

```python
from chaosmonkey.platforms import Platform, VMInfo, VMPowerState
```

Key methods:
- `connect()` / `disconnect()`: Connection management
- `discover_vms()`: VM discovery with filtering
- `get_vm()`: Get detailed VM information
- `power_on()` / `power_off()` / `reboot()`: Power operations
- `batch_*()`: Parallel operations on multiple VMs

### Modules

```
src/chaosmonkey/platforms/
├── base.py                    # Platform interface and VMInfo model
├── olvm/
│   └── client.py              # OLVM implementation
├── vsphere/
│   ├── client.py              # vSphere implementation
│   └── discovery.py           # vSphere discovery helpers
└── dora/
    └── client.py              # Dora API client
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# OLVM Configuration
OLVM_URL=https://engine.example.com/ovirt-engine/api
OLVM_USERNAME=admin@internal
OLVM_PASSWORD=your_password
OLVM_CA_FILE=/path/to/ca.pem
OLVM_INSECURE=false

# vSphere Configuration
VSPHERE_SERVER=vcenter.example.com
VSPHERE_USERNAME=administrator@vsphere.local
VSPHERE_PASSWORD=your_password
VSPHERE_PORT=443
VSPHERE_INSECURE=true

# Dora API Configuration
DORA_HOST=hostname
DORA_API_PORT=8000
DORA_AUTH_PORT=51051
DORA_USERNAME=your_username
DORA_PASSWORD=your_password
```

### Configuration File

Create `chaosmonkey.yaml`:

```yaml
platforms:
  olvm:
    url: https://engine.example.com/ovirt-engine/api
    username: admin@internal
    password: your_password
    insecure: false
  
  vsphere:
    server: vcenter.example.com
    username: administrator@vsphere.local
    password: your_password
    insecure: true
  
  dora:
    host: hostname
    api_port: 8000
    auth_port: 51051
    username: your_username
    password: your_password
```

## Installation

### Install Platform Dependencies

```bash
# For OLVM support
pip install 'chaosmonkey-cli[olvm]'

# For vSphere support
pip install 'chaosmonkey-cli[vsphere]'

# For both platforms
pip install 'chaosmonkey-cli[platforms]'
```

Or install manually:

```bash
pip install ovirt-engine-sdk-python  # OLVM
pip install pyvmomi                   # vSphere
```

## CLI Commands

### Discover VMs

List VMs on a platform:

```bash
# Discover all VMs on OLVM
chaosmonkey platforms discover-vms --platform olvm

# Discover VMs matching pattern on vSphere
chaosmonkey platforms discover-vms --platform vsphere --name "web-*"

# Filter by datacenter
chaosmonkey platforms discover-vms --platform vsphere --datacenter Production
```

### Get VM Information

Get detailed info about a specific VM:

```bash
chaosmonkey platforms vm-info web-01 --platform vsphere
```

Output:
```
VM Information: web-01
  Platform:     vsphere
  ID:           vm-123
  Power State:  powered_on
  Host:         esx-01.example.com
  Datacenter:   Production
  Cluster:      Web-Cluster
  CPUs:         4
  Memory:       8192MB
  Guest OS:     Ubuntu Linux (64-bit)
  Tools Status: toolsOk
```

### Power Operations

```bash
# Power on a VM
chaosmonkey platforms power-on web-01 --platform vsphere

# Graceful shutdown
chaosmonkey platforms power-off web-01 --platform vsphere --graceful

# Force power off
chaosmonkey platforms power-off web-01 --platform vsphere --force

# Reboot VM
chaosmonkey platforms reboot web-01 --platform vsphere --graceful
```

### Dora Integration

List available environments:

```bash
chaosmonkey platforms dora-environments
```

Discover environment:

```bash
# Discover and display
chaosmonkey platforms dora-discover Paytv

# Save to file
chaosmonkey platforms dora-discover "EPB-Prod" \
  --username myuser --password mypass \
  --output environment_data.json
```

Available Dora environments:
- Paytv
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

## Chaos Experiments

### Available Experiment Templates

- **olvm-vm-shutdown**: Power off VM on OLVM
- **vsphere-vm-poweroff**: Power off VM on vSphere
- **vsphere-vm-reboot**: Reboot VM on vSphere
- **olvm-vm-batch-shutdown**: Power off multiple VMs in parallel

### Execute VM Chaos Experiment

Create an experiment file or use templates:

```bash
# Power off a VM using template
chaosmonkey execute \
  --chaos-type vsphere-vm-poweroff \
  --override vm_name=web-01 \
  --override vsphere_server=vcenter.example.com \
  --override vsphere_username=admin@vsphere.local \
  --override vsphere_password=secret \
  --override graceful=true
```

### Custom Experiment Example

Create `vm_shutdown_experiment.json`:

```json
{
  "version": "1.0.0",
  "title": "Web Server VM Failure",
  "description": "Simulate web server VM failure and verify failover",
  "steady-state-hypothesis": {
    "title": "Web service is accessible",
    "probes": [
      {
        "type": "probe",
        "name": "web-service-health",
        "tolerance": 200,
        "provider": {
          "type": "http",
          "url": "https://myapp.example.com/health"
        }
      }
    ]
  },
  "method": [
    {
      "type": "action",
      "name": "Power off web VM",
      "provider": {
        "type": "python",
        "module": "chaosmonkey.stubs.actions",
        "func": "vm_power_off",
        "arguments": {
          "vm_name": "web-01",
          "platform_type": "vsphere",
          "graceful": false,
          "timeout": 300,
          "server": "${VSPHERE_SERVER}",
          "username": "${VSPHERE_USERNAME}",
          "password": "${VSPHERE_PASSWORD}",
          "insecure": true
        }
      }
    },
    {
      "type": "probe",
      "name": "wait-for-failover",
      "provider": {
        "type": "python",
        "module": "time",
        "func": "sleep",
        "arguments": {
          "seconds": 30
        }
      }
    }
  ],
  "rollbacks": [
    {
      "type": "action",
      "name": "Restore web VM",
      "provider": {
        "type": "python",
        "module": "chaosmonkey.stubs.actions",
        "func": "vm_power_on",
        "arguments": {
          "vm_name": "web-01",
          "platform_type": "vsphere",
          "server": "${VSPHERE_SERVER}",
          "username": "${VSPHERE_USERNAME}",
          "password": "${VSPHERE_PASSWORD}",
          "insecure": true
        }
      }
    }
  ]
}
```

Execute:

```bash
chaosmonkey execute --experiment vm_shutdown_experiment.json
```

## Python API Usage

### Direct Platform Usage

```python
from chaosmonkey.platforms.vsphere import VSpherePlatform

# Create and use platform client
with VSpherePlatform(
    server="vcenter.example.com",
    username="admin@vsphere.local",
    password="password",
    insecure=True
) as platform:
    # Discover VMs
    vms = platform.discover_vms(name_pattern="web-")
    
    for vm in vms:
        print(f"{vm.name}: {vm.power_state.value}")
    
    # Power operations
    platform.power_off("web-01", graceful=True)
    platform.power_on("web-01")
```

### Using Platform Orchestrator

```python
from chaosmonkey.config import load_settings
from chaosmonkey.core.platform_orchestrator import PlatformOrchestrator

# Load configuration
settings = load_settings(None)
orchestrator = PlatformOrchestrator(settings)

# Discover VMs
vms = orchestrator.discover_vms("vsphere", name_pattern="web-*")

# Power operations
orchestrator.power_off_vm("vsphere", "web-01", graceful=True)
```

### Batch Operations

```python
from chaosmonkey.platforms.olvm import OLVMPlatform

with OLVMPlatform(
    url="https://engine.example.com/ovirt-engine/api",
    username="admin@internal",
    password="password"
) as platform:
    # Power off multiple VMs in parallel
    results = platform.batch_power_off(
        vm_names=["web-01", "web-02", "web-03"],
        graceful=True,
        parallel=3,
        timeout=300
    )
    
    for vm_name, success in results.items():
        print(f"{vm_name}: {'✓' if success else '✗'}")
```

## Troubleshooting

### Common Issues

**OLVM connection fails:**
```
RuntimeError: Failed to connect to OLVM engine
```
- Check OLVM_URL is correct
- Verify credentials
- Check CA certificate if using secure connection

**vSphere authentication error:**
```
RuntimeError: Invalid vSphere login credentials
```
- Verify VSPHERE_USERNAME format (e.g., administrator@vsphere.local)
- Check password
- Ensure user has required permissions

**Dora authentication fails:**
```
RuntimeError: Dora authentication failed
```
- Check DORA_HOST is reachable
- Verify credentials
- Check firewall rules for ports 8000 and 51051

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Connection

Test platform connectivity:

```python
from chaosmonkey.platforms.vsphere import VSpherePlatform

try:
    platform = VSpherePlatform(
        server="vcenter.example.com",
        username="admin@vsphere.local",
        password="password"
    )
    platform.connect()
    print("✓ Connected successfully")
    platform.disconnect()
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

## Security Best Practices

1. **Use Environment Variables**: Never hardcode credentials in code or config files
2. **Use CA Certificates**: For production, always use proper TLS with CA verification
3. **Limit Permissions**: Create dedicated service accounts with minimal required permissions
4. **Rotate Credentials**: Regularly rotate passwords and tokens
5. **Audit Logging**: Enable audit logging on platforms to track chaos operations

## Next Steps

- See [CHAOS_EXPERIMENTS.md](./CHAOS_EXPERIMENTS.md) for experiment design patterns
- Review [ARCHITECTURE.md](./ARCHITECTURE.md) for system architecture
- Check [API_REFERENCE.md](./API_REFERENCE.md) for complete API documentation
