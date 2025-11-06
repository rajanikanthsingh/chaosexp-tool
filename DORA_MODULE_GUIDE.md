# Dora Module Complete Guide

## Overview

The Dora module provides centralized VM and hypervisor discovery across multiple vSphere environments through the Dora API. This eliminates the need for direct vCenter credentials and provides a unified inventory system.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [CLI Usage](#cli-usage)
- [Python API](#python-api)
- [Available Environments](#available-environments)
- [Use Cases](#use-cases)
- [Advanced Examples](#advanced-examples)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Configure Environment

Create or update `.env` file:

```bash
DORA_HOST=hostname
DORA_API_PORT=8000
DORA_AUTH_PORT=51051
DORA_USERNAME=your_username
DORA_PASSWORD=your_password
```

### 2. List Available Environments

```bash
chaosmonkey platforms dora-environments
```

**Output:**
```
Available Dora Environments:
  • Paytv
  • Oracle-Paytv
  • DR-Paytv
  • Arvig-Staging
  • Arvig-Prod
  • EPB-Staging
  • EPB-Prod
  • Lumos-Prod
  • Comporium-Prod
  • MSG-Prod
  • Liberty-Prod
  • Midco-Staging
  • Midco-Prod

Total: 13 environments
```

### 3. Discover an Environment

```bash
chaosmonkey platforms dora-discover "Paytv" \
  --username your_username \
  --password your_password
```

**Output:**
```json
{
  "environment": "Paytv",
  "timestamp": "2025-10-09T10:30:00Z",
  "hypervisors": [
    {
      "name": "esx-01.paytv.com",
      "ip_address": "10.1.1.10",
      "type": "vmware-esxi",
      "status": "connected"
    }
  ],
  "vms": [
    {
      "name": "web-server-01",
      "hypervisor": "esx-01.paytv.com",
      "power_state": "poweredOn",
      "cpu_count": 4,
      "memory_mb": 8192
    }
  ]
}
```

---

## Configuration

### Method 1: Environment Variables (Recommended)

Create `.env` file:

```bash
# Dora Configuration
DORA_HOST=hostname
DORA_API_PORT=8000
DORA_AUTH_PORT=51051
DORA_USERNAME=your_username
DORA_PASSWORD=your_password
```

### Method 2: Configuration File

Add to `config.yaml`:

```yaml
platforms:
  dora:
    host: hostname
    api_port: 8000
    auth_port: 51051
    username: your_username
    password: your_password
```

### Method 3: Programmatic Configuration

```python
from chaosmonkey.platforms.dora import DoraClient

client = DoraClient(
    dora_host="hostname",
    api_port=8000,
    auth_port=51051
)

# Pass credentials when calling
data = client.get_environment_data(
    environment="Paytv",
    username="your_username",
    password="your_password"
)
```

---

## CLI Usage

### List Environments

```bash
# List all available environments
chaosmonkey platforms dora-environments
```

### Discover Environment

```bash
# Basic discovery
chaosmonkey platforms dora-discover "Paytv" \
  --username admin \
  --password secret

# Save to file
chaosmonkey platforms dora-discover "EPB-Prod" \
  --username admin \
  --password secret \
  --output epb_production.json

# Pretty print with jq (if installed)
chaosmonkey platforms dora-discover "Paytv" \
  --username admin \
  --password secret | jq '.'

# Using environment variables (cleaner)
export DORA_USERNAME=admin
export DORA_PASSWORD=secret
chaosmonkey platforms dora-discover "Lumos-Prod"

# Discover multiple environments
for env in "Paytv" "Oracle-Paytv" "DR-Paytv"; do
  chaosmonkey platforms dora-discover "$env" \
    --output "${env}_data.json"
done
```

---

## Python API

### Basic Usage

```python
from chaosmonkey.platforms.dora import DoraClient

# Create client
client = DoraClient(
    dora_host="hostname",
    api_port=8000,
    auth_port=51051
)

# List environments
environments = DoraClient.list_environments()
print(f"Available: {len(environments)} environments")

# Discover specific environment
data = client.get_environment_data(
    environment="Paytv",
    username="admin",
    password="secret"
)

print(f"Hypervisors: {len(data['hypervisors'])}")
print(f"VMs: {len(data['vms'])}")
```

### Using Configuration

```python
from chaosmonkey.config import load_settings
from chaosmonkey.platforms.dora import DoraClient

# Load from .env file
settings = load_settings(None)

# Create client from settings
client = DoraClient(
    dora_host=settings.platforms.dora.host,
    api_port=settings.platforms.dora.api_port,
    auth_port=settings.platforms.dora.auth_port
)

# Use credentials from settings
data = client.get_environment_data(
    environment="EPB-Prod",
    username=settings.platforms.dora.username,
    password=settings.platforms.dora.password
)
```

### Accessing Data

```python
data = client.get_environment_data("Paytv", username, password)

# Access hypervisors
for hypervisor in data['hypervisors']:
    print(f"Hypervisor: {hypervisor['name']}")
    print(f"  IP: {hypervisor['ip_address']}")
    print(f"  Type: {hypervisor['type']}")
    print(f"  Status: {hypervisor['status']}")

# Access VMs
for vm in data['vms']:
    print(f"VM: {vm['name']}")
    print(f"  Host: {vm['hypervisor']}")
    print(f"  State: {vm['power_state']}")
    print(f"  CPUs: {vm['cpu_count']}")
    print(f"  Memory: {vm['memory_mb']}MB")
```

---

## Available Environments

### Full Environment List

| Environment | Purpose | Region |
|------------|---------|--------|
| **Paytv** | Main Paytv environment | Primary |
| **Oracle-Paytv** | Oracle integration | Primary |
| **DR-Paytv** | Disaster recovery | DR Site |
| **Arvig-Staging** | Arvig staging/testing | Staging |
| **Arvig-Prod** | Arvig production | Production |
| **EPB-Staging** | EPB staging/testing | Staging |
| **EPB-Prod** | EPB production | Production |
| **Lumos-Prod** | Lumos production | Production |
| **Comporium-Prod** | Comporium production | Production |
| **MSG-Prod** | MSG production | Production |
| **Liberty-Prod** | Liberty production | Production |
| **Midco-Staging** | Midco staging/testing | Staging |
| **Midco-Prod** | Midco production | Production |

### Environment Grouping

```python
from chaosmonkey.platforms.dora import DoraClient

# Production environments
production_envs = [
    "Arvig-Prod", "EPB-Prod", "Lumos-Prod", 
    "Comporium-Prod", "MSG-Prod", "Liberty-Prod", "Midco-Prod"
]

# Staging environments
staging_envs = ["Arvig-Staging", "EPB-Staging", "Midco-Staging"]

# Paytv environments
paytv_envs = ["Paytv", "Oracle-Paytv", "DR-Paytv"]
```

---

## Use Cases

### Use Case 1: VM Inventory Report

Generate CSV inventory across all environments:

```python
from chaosmonkey.platforms.dora import DoraClient
import csv
from datetime import datetime

client = DoraClient(
    dora_host="hostname",
    api_port=8000,
    auth_port=51051
)

username = "admin"
password = "secret"

# CSV output
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_file = f"vm_inventory_{timestamp}.csv"

with open(csv_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Environment', 'VM Name', 'Hypervisor', 'Power State', 'CPUs', 'Memory (GB)'])
    
    for env in DoraClient.list_environments():
        try:
            data = client.get_environment_data(env, username, password)
            for vm in data['vms']:
                writer.writerow([
                    env,
                    vm.get('name', 'N/A'),
                    vm.get('hypervisor', 'N/A'),
                    vm.get('power_state', 'N/A'),
                    vm.get('cpu_count', 0),
                    vm.get('memory_mb', 0) / 1024
                ])
            print(f"✓ {env}: {len(data['vms'])} VMs")
        except Exception as e:
            print(f"✗ {env}: {e}")

print(f"\n✓ Report saved to {csv_file}")
```

### Use Case 2: Pre-Chaos Validation

Validate target VM exists before running chaos experiment:

```python
from chaosmonkey.platforms.dora import DoraClient

def validate_vm_exists(environment, vm_name, username, password):
    """Validate VM exists in environment before chaos experiment."""
    
    client = DoraClient(
        dora_host="hostname",
        api_port=8000,
        auth_port=51051
    )
    
    # Discover environment
    data = client.get_environment_data(environment, username, password)
    
    # Check if VM exists
    vm_names = [vm['name'] for vm in data['vms']]
    
    if vm_name in vm_names:
        # Find VM details
        vm_info = next(vm for vm in data['vms'] if vm['name'] == vm_name)
        print(f"✓ VM found: {vm_name}")
        print(f"  Host: {vm_info['hypervisor']}")
        print(f"  State: {vm_info['power_state']}")
        return True
    else:
        print(f"✗ VM not found: {vm_name}")
        print(f"  Available VMs: {len(vm_names)}")
        return False

# Example usage
if validate_vm_exists("EPB-Staging", "web-server-01", "admin", "secret"):
    print("\nProceeding with chaos experiment...")
    # Run chaos experiment
else:
    print("\nAborting: Target VM not found!")
```

### Use Case 3: Multi-Environment Discovery

Discover and compare resources across environments:

```python
from chaosmonkey.platforms.dora import DoraClient
from collections import defaultdict

client = DoraClient(
    dora_host="hostname",
    api_port=8000,
    auth_port=51051
)

username = "admin"
password = "secret"

# Production environments
prod_envs = ["Arvig-Prod", "EPB-Prod", "Lumos-Prod", "Comporium-Prod"]

results = {}
for env in prod_envs:
    try:
        data = client.get_environment_data(env, username, password)
        
        # Calculate statistics
        total_vms = len(data['vms'])
        powered_on = sum(1 for vm in data['vms'] if vm['power_state'] == 'poweredOn')
        total_cpu = sum(vm.get('cpu_count', 0) for vm in data['vms'])
        total_memory_gb = sum(vm.get('memory_mb', 0) for vm in data['vms']) / 1024
        
        results[env] = {
            'total_vms': total_vms,
            'powered_on': powered_on,
            'total_cpu': total_cpu,
            'total_memory_gb': total_memory_gb
        }
        
        print(f"{env}:")
        print(f"  VMs: {total_vms} (Powered On: {powered_on})")
        print(f"  CPUs: {total_cpu}")
        print(f"  Memory: {total_memory_gb:.1f} GB")
        print()
        
    except Exception as e:
        print(f"{env}: Error - {e}\n")

# Summary
print("="*60)
total_vms_all = sum(r['total_vms'] for r in results.values())
total_cpu_all = sum(r['total_cpu'] for r in results.values())
total_memory_all = sum(r['total_memory_gb'] for r in results.values())

print(f"Total across {len(results)} environments:")
print(f"  VMs: {total_vms_all}")
print(f"  CPUs: {total_cpu_all}")
print(f"  Memory: {total_memory_all:.1f} GB")
```

### Use Case 4: Compare Dora vs Direct vSphere

Validate Dora data against direct vSphere connection:

```python
from chaosmonkey.platforms.dora import DoraClient
from chaosmonkey.platforms.vsphere import VSpherePlatform
from chaosmonkey.config import load_settings

settings = load_settings(None)

# Get data from Dora
dora_client = DoraClient(
    dora_host=settings.platforms.dora.host,
    api_port=settings.platforms.dora.api_port,
    auth_port=settings.platforms.dora.auth_port
)

print("Fetching data from Dora...")
dora_data = dora_client.get_environment_data(
    environment="EPB-Prod",
    username=settings.platforms.dora.username,
    password=settings.platforms.dora.password
)

dora_vm_names = {vm['name'] for vm in dora_data['vms']}
print(f"Dora: {len(dora_vm_names)} VMs")

# Get data from vSphere
print("\nConnecting to vSphere...")
with VSpherePlatform(
    server=settings.platforms.vsphere.server,
    username=settings.platforms.vsphere.username,
    password=settings.platforms.vsphere.password,
    insecure=True
) as vsphere:
    vsphere_vms = vsphere.discover_vms()
    vsphere_vm_names = {vm.name for vm in vsphere_vms}
    print(f"vSphere: {len(vsphere_vm_names)} VMs")

# Compare
common = dora_vm_names & vsphere_vm_names
only_dora = dora_vm_names - vsphere_vm_names
only_vsphere = vsphere_vm_names - dora_vm_names

print(f"\nComparison:")
print(f"  Common VMs: {len(common)}")
print(f"  Only in Dora: {len(only_dora)}")
print(f"  Only in vSphere: {len(only_vsphere)}")

if only_dora:
    print(f"\n  VMs only in Dora (first 5):")
    for vm in list(only_dora)[:5]:
        print(f"    - {vm}")

if only_vsphere:
    print(f"\n  VMs only in vSphere (first 5):")
    for vm in list(only_vsphere)[:5]:
        print(f"    - {vm}")

# Accuracy percentage
accuracy = len(common) / len(dora_vm_names | vsphere_vm_names) * 100
print(f"\nData accuracy: {accuracy:.1f}%")
```

### Use Case 5: Automated Daily Inventory

Create daily inventory snapshots:

```python
#!/usr/bin/env python3
"""Daily Dora inventory snapshot."""

from chaosmonkey.platforms.dora import DoraClient
from chaosmonkey.config import load_settings
import json
from datetime import datetime
from pathlib import Path

def create_daily_snapshot():
    """Create daily inventory snapshot from Dora."""
    
    settings = load_settings(None)
    client = DoraClient(
        dora_host=settings.platforms.dora.host,
        api_port=settings.platforms.dora.api_port,
        auth_port=settings.platforms.dora.auth_port
    )
    
    username = settings.platforms.dora.username
    password = settings.platforms.dora.password
    
    # Create snapshots directory
    snapshot_dir = Path("snapshots")
    snapshot_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d')
    
    # Discover all environments
    all_data = {}
    
    for env in DoraClient.list_environments():
        try:
            print(f"Discovering {env}...")
            data = client.get_environment_data(env, username, password)
            all_data[env] = {
                'timestamp': datetime.now().isoformat(),
                'hypervisors': data['hypervisors'],
                'vms': data['vms'],
                'summary': {
                    'total_vms': len(data['vms']),
                    'powered_on': sum(1 for vm in data['vms'] if vm['power_state'] == 'poweredOn'),
                    'hypervisors': len(data['hypervisors'])
                }
            }
            print(f"  ✓ {len(data['vms'])} VMs, {len(data['hypervisors'])} hypervisors")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_data[env] = {'error': str(e)}
    
    # Save snapshot
    snapshot_file = snapshot_dir / f"dora_snapshot_{timestamp}.json"
    with open(snapshot_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\n✓ Snapshot saved to {snapshot_file}")
    
    # Create summary
    total_vms = sum(
        data['summary']['total_vms'] 
        for data in all_data.values() 
        if 'summary' in data
    )
    
    print(f"\nSummary:")
    print(f"  Environments: {len(all_data)}")
    print(f"  Total VMs: {total_vms}")

if __name__ == "__main__":
    create_daily_snapshot()
```

Run it daily with cron:
```bash
# Add to crontab
0 2 * * * cd /path/to/chaosmonkey && python3 daily_dora_snapshot.py
```

---

## Advanced Examples

### Example 1: Filter VMs by Criteria

```python
from chaosmonkey.platforms.dora import DoraClient

client = DoraClient(
    dora_host="hostname",
    api_port=8000,
    auth_port=51051
)

data = client.get_environment_data("Paytv", "admin", "secret")

# Find all powered-on VMs
powered_on = [vm for vm in data['vms'] if vm['power_state'] == 'poweredOn']
print(f"Powered On VMs: {len(powered_on)}")

# Find VMs with high memory
high_memory = [vm for vm in data['vms'] if vm.get('memory_mb', 0) >= 16384]
print(f"VMs with ≥16GB RAM: {len(high_memory)}")

# Find VMs by name pattern
web_servers = [vm for vm in data['vms'] if 'web' in vm['name'].lower()]
print(f"Web Servers: {len(web_servers)}")

# Group by hypervisor
from collections import defaultdict
by_host = defaultdict(list)
for vm in data['vms']:
    by_host[vm['hypervisor']].append(vm)

print(f"\nVMs per hypervisor:")
for host, vms in by_host.items():
    print(f"  {host}: {len(vms)} VMs")
```

### Example 2: Environment Health Check

```python
from chaosmonkey.platforms.dora import DoraClient

def check_environment_health(environment, username, password):
    """Check health of a Dora environment."""
    
    client = DoraClient(
        dora_host="hostname",
        api_port=8000,
        auth_port=51051
    )
    
    data = client.get_environment_data(environment, username, password)
    
    total_vms = len(data['vms'])
    powered_on = sum(1 for vm in data['vms'] if vm['power_state'] == 'poweredOn')
    powered_off = total_vms - powered_on
    
    hypervisors = len(data['hypervisors'])
    connected_hosts = sum(
        1 for h in data['hypervisors'] 
        if h.get('status') == 'connected'
    )
    
    print(f"Environment Health: {environment}")
    print("="*60)
    print(f"Hypervisors:")
    print(f"  Total: {hypervisors}")
    print(f"  Connected: {connected_hosts}")
    print(f"  Issues: {hypervisors - connected_hosts}")
    
    print(f"\nVirtual Machines:")
    print(f"  Total: {total_vms}")
    print(f"  Powered On: {powered_on} ({powered_on/total_vms*100:.1f}%)")
    print(f"  Powered Off: {powered_off} ({powered_off/total_vms*100:.1f}%)")
    
    # Check for issues
    issues = []
    if connected_hosts < hypervisors:
        issues.append(f"{hypervisors - connected_hosts} hypervisor(s) not connected")
    if powered_off > total_vms * 0.5:
        issues.append(f"More than 50% of VMs are powered off")
    
    if issues:
        print(f"\n⚠️  Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\n✓ No issues found")
    
    return len(issues) == 0

# Check multiple environments
for env in ["Arvig-Prod", "EPB-Prod", "Lumos-Prod"]:
    check_environment_health(env, "admin", "secret")
    print("\n")
```

### Example 3: Export to Excel

```python
from chaosmonkey.platforms.dora import DoraClient
import pandas as pd
from datetime import datetime

client = DoraClient(
    dora_host="hostname",
    api_port=8000,
    auth_port=51051
)

# Discover multiple environments
environments = ["Paytv", "Arvig-Prod", "EPB-Prod"]
all_vms = []

for env in environments:
    try:
        data = client.get_environment_data(env, "admin", "secret")
        for vm in data['vms']:
            all_vms.append({
                'Environment': env,
                'VM Name': vm.get('name', 'N/A'),
                'Hypervisor': vm.get('hypervisor', 'N/A'),
                'Power State': vm.get('power_state', 'N/A'),
                'CPUs': vm.get('cpu_count', 0),
                'Memory (GB)': vm.get('memory_mb', 0) / 1024,
                'Guest OS': vm.get('guest_os', 'N/A')
            })
        print(f"✓ {env}: {len(data['vms'])} VMs")
    except Exception as e:
        print(f"✗ {env}: {e}")

# Create DataFrame
df = pd.DataFrame(all_vms)

# Save to Excel
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
excel_file = f"vm_inventory_{timestamp}.xlsx"

with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
    # All VMs sheet
    df.to_excel(writer, sheet_name='All VMs', index=False)
    
    # Per-environment sheets
    for env in environments:
        env_df = df[df['Environment'] == env]
        env_df.to_excel(writer, sheet_name=env, index=False)
    
    # Summary sheet
    summary = df.groupby('Environment').agg({
        'VM Name': 'count',
        'CPUs': 'sum',
        'Memory (GB)': 'sum'
    }).rename(columns={'VM Name': 'Total VMs'})
    summary.to_excel(writer, sheet_name='Summary')

print(f"\n✓ Excel report saved to {excel_file}")
```

---

## Troubleshooting

### Issue: Connection Timeout

```python
# Test Dora connectivity
python -c "
from chaosmonkey.platforms.dora import DoraClient
client = DoraClient('hostname', 8000, 51051)
print('Client created successfully')
"
```

### Issue: Authentication Failed

```bash
# Verify credentials
export DORA_USERNAME=your_username
export DORA_PASSWORD=your_password

# Test authentication
chaosmonkey platforms dora-discover "Paytv"
```

### Issue: Environment Not Found

```python
# List available environments
from chaosmonkey.platforms.dora import DoraClient
envs = DoraClient.list_environments()
print("Available environments:")
for env in envs:
    print(f"  - {env}")
```

### Issue: Empty Results

```python
# Check if data is returned
from chaosmonkey.platforms.dora import DoraClient

client = DoraClient(
    dora_host="hostname",
    api_port=8000,
    auth_port=51051
)

data = client.get_environment_data("Paytv", "user", "pass")
print(f"Hypervisors: {len(data.get('hypervisors', []))}")
print(f"VMs: {len(data.get('vms', []))}")
print(f"Raw data keys: {list(data.keys())}")
```

---

## Integration with Chaos Experiments

### Pre-Chaos VM Validation

```python
from chaosmonkey.platforms.dora import DoraClient

def pre_chaos_validation(environment, vm_name, username, password):
    """Validate VM exists before running chaos experiment."""
    client = DoraClient(
        dora_host="hostname",
        api_port=8000,
        auth_port=51051
    )
    
    data = client.get_environment_data(environment, username, password)
    vm_names = [vm['name'] for vm in data['vms']]
    
    if vm_name not in vm_names:
        raise ValueError(f"VM '{vm_name}' not found in {environment}")
    
    vm_info = next(vm for vm in data['vms'] if vm['name'] == vm_name)
    
    if vm_info['power_state'] != 'poweredOn':
        raise ValueError(f"VM '{vm_name}' is not powered on")
    
    print(f"✓ VM '{vm_name}' validated for chaos experiment")
    return vm_info

# Use in chaos experiment
try:
    vm_info = pre_chaos_validation("EPB-Staging", "test-vm-01", "admin", "secret")
    # Proceed with chaos experiment
    print("Proceeding with chaos experiment...")
except ValueError as e:
    print(f"Validation failed: {e}")
```

---

## Best Practices

1. **Use Environment Variables**: Store credentials in `.env` file, not in code
2. **Validate Before Chaos**: Always verify VM exists before running experiments
3. **Cache Results**: Save discovery results to avoid repeated API calls
4. **Handle Errors**: Always wrap API calls in try-except blocks
5. **Rate Limiting**: Don't query too frequently; implement delays if needed
6. **Log Activities**: Keep audit trail of all Dora API calls

---

## Quick Reference Card

```bash
# Common Commands
chaosmonkey platforms dora-environments              # List environments
chaosmonkey platforms dora-discover "Paytv"         # Discover environment
chaosmonkey platforms dora-discover "EPB-Prod" --output data.json  # Save output

# Python Quick Start
from chaosmonkey.platforms.dora import DoraClient
client = DoraClient("hostname", 8000, 51051)
envs = DoraClient.list_environments()
data = client.get_environment_data("Paytv", "user", "pass")

# Configuration
echo "DORA_HOST=hostname" >> .env
echo "DORA_USERNAME=admin" >> .env
echo "DORA_PASSWORD=secret" >> .env
```

---

## Need Help?

- Check `HOW_TO_RUN.md` for general project usage
- See `docs/VM_PLATFORMS_GUIDE.md` for complete platform documentation
- Review `VM_PLATFORMS_QUICKSTART.md` for quick start guide
