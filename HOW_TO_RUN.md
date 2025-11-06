# How to Run ChaosMonkey with VM Platform Support

## Initial Setup

### 1. Install the Project

```bash
cd /Users/inderdeep.sidhu/PycharmProjects/chaosmonkey

# Create/activate virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install with VM platform support
pip install -e '.[platforms]'
```

This installs ChaosMonkey with OLVM and vSphere support.

### 2. Configure Credentials

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.platforms.example .env

# Edit with your actual credentials
nano .env
```

Example `.env` file:

```bash
# OLVM/oVirt Configuration
OLVM_URL=https://your-engine.example.com/ovirt-engine/api
OLVM_USERNAME=admin@internal
OLVM_PASSWORD=your_olvm_password
OLVM_INSECURE=false  # Set to true for self-signed certs

# VMware vSphere Configuration
VSPHERE_SERVER=vcenter.example.com
VSPHERE_USERNAME=administrator@vsphere.local
VSPHERE_PASSWORD=your_vsphere_password
VSPHERE_PORT=443
VSPHERE_INSECURE=true  # Set to false for production with valid certs

# Dora API Configuration (if using Dora)
DORA_HOST=hostname
DORA_API_PORT=8000
DORA_AUTH_PORT=51051
DORA_USERNAME=your_dora_username
DORA_PASSWORD=your_dora_password
```

### 3. Verify Installation

```bash
# Check if CLI is installed
chaosmonkey --help

# Check platform commands
chaosmonkey platforms --help
```

---

## Using the New VM Platform Features

### A. CLI Commands (Easiest Way)

#### 1. **Discover VMs**

```bash
# Discover all VMs on vSphere
chaosmonkey platforms discover-vms --platform vsphere

# Discover VMs with name filter
chaosmonkey platforms discover-vms --platform vsphere --name "web-*"

# Discover VMs in specific datacenter
chaosmonkey platforms discover-vms --platform vsphere --datacenter "Production"

# Discover on OLVM
chaosmonkey platforms discover-vms --platform olvm
```

**Example Output:**
```
Discovering VMs on vsphere...
✓ Discovered 15 VMs

┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━┳━━━━━━━━━━━━━┓
┃ Name        ┃ Power State  ┃ Host              ┃ Datacenter ┃ CPU ┃ Memory (GB) ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━╇━━━━━━━━━━━━━┩
│ web-01      │ powered_on   │ esx-01.example.com│ Production │ 4   │ 8.0         │
│ web-02      │ powered_off  │ esx-02.example.com│ Production │ 4   │ 8.0         │
└─────────────┴──────────────┴───────────────────┴────────────┴─────┴─────────────┘

Total: 15 VMs
```

#### 2. **Get VM Information**

```bash
# Get detailed info about a specific VM
chaosmonkey platforms vm-info web-01 --platform vsphere
```

**Example Output:**
```
VM Information: web-01
  Platform:     vsphere
  ID:           vm-1234
  Power State:  powered_on
  Host:         esx-01.example.com
  Datacenter:   Production
  Cluster:      Web-Cluster
  CPUs:         4
  Memory:       8192MB
  Guest OS:     Ubuntu Linux (64-bit)
  Tools Status: toolsOk
```

#### 3. **Power Operations**

```bash
# Power on a VM
chaosmonkey platforms power-on web-01 --platform vsphere

# Graceful shutdown (try guest shutdown first)
chaosmonkey platforms power-off web-01 --platform vsphere --graceful

# Force power off (immediate)
chaosmonkey platforms power-off web-01 --platform vsphere --force

# Reboot a VM (graceful)
chaosmonkey platforms reboot web-01 --platform vsphere --graceful

# Force reboot (hard reset)
chaosmonkey platforms reboot web-01 --platform vsphere --force

# With custom timeout
chaosmonkey platforms power-off web-01 --platform vsphere --timeout 600
```

#### 4. **Dora Integration**

```bash
# List available Dora environments
chaosmonkey platforms dora-environments

# Discover a specific environment
chaosmonkey platforms dora-discover "Paytv" \
  --username your_username \
  --password your_password

# Save output to file
chaosmonkey platforms dora-discover "EPB-Prod" \
  --output environment_data.json
```

---

### B. Python API (For Scripting)

#### 1. **Direct Platform Usage**

Create a Python script `test_vsphere.py`:

```python
from chaosmonkey.platforms.vsphere import VSpherePlatform

# Method 1: Using context manager (recommended)
with VSpherePlatform(
    server="vcenter.example.com",
    username="administrator@vsphere.local",
    password="your_password",
    insecure=True
) as platform:
    # Discover VMs
    print("Discovering VMs...")
    vms = platform.discover_vms(name_pattern="web-")
    
    for vm in vms:
        print(f"  {vm.name}: {vm.power_state.value} on {vm.host}")
    
    # Get specific VM info
    vm = platform.get_vm("web-01")
    print(f"\nVM Details:")
    print(f"  Name: {vm.name}")
    print(f"  State: {vm.power_state.value}")
    print(f"  CPUs: {vm.cpu_count}")
    print(f"  Memory: {vm.memory_mb}MB")
    
    # Power operations
    print("\nPowering off web-01...")
    platform.power_off("web-01", graceful=True, timeout=300)
    print("Done!")
```

Run it:
```bash
python test_vsphere.py
```

#### 2. **Using Platform Orchestrator** (Recommended)

Create `test_orchestrator.py`:

```python
from chaosmonkey.config import load_settings
from chaosmonkey.core.platform_orchestrator import PlatformOrchestrator

# Load configuration from .env
settings = load_settings(None)
orchestrator = PlatformOrchestrator(settings)

# Discover VMs
print("Discovering VMs on vSphere...")
vms = orchestrator.discover_vms("vsphere", name_pattern="web-*")

for vm in vms:
    print(f"  {vm.name}: {vm.power_state.value}")

# Power operations
print("\nPowering off web-01...")
success = orchestrator.power_off_vm("vsphere", "web-01", graceful=True)

if success:
    print("✓ Successfully powered off")
else:
    print("✗ Failed to power off")

# Power back on
print("\nPowering on web-01...")
orchestrator.power_on_vm("vsphere", "web-01")
print("✓ Powered on")
```

Run it:
```bash
python test_orchestrator.py
```

#### 3. **OLVM Example**

Create `test_olvm.py`:

```python
from chaosmonkey.platforms.olvm import OLVMPlatform

with OLVMPlatform(
    url="https://engine.example.com/ovirt-engine/api",
    username="admin@internal",
    password="your_password",
    insecure=False
) as platform:
    # Discover VMs
    vms = platform.discover_vms(name_pattern="web-*")
    
    for vm in vms:
        print(f"{vm.name}: {vm.power_state.value}")
    
    # Power operations
    platform.power_off("web-01", graceful=True)
    platform.power_on("web-01")
```

#### 4. **Batch Operations**

Create `test_batch.py`:

```python
from chaosmonkey.platforms.vsphere import VSpherePlatform

with VSpherePlatform(...) as platform:
    # Power off multiple VMs in parallel
    vm_list = ["web-01", "web-02", "web-03"]
    
    print(f"Powering off {len(vm_list)} VMs in parallel...")
    results = platform.batch_power_off(
        vm_names=vm_list,
        graceful=True,
        parallel=3,  # Max 3 concurrent operations
        timeout=300
    )
    
    # Check results
    for vm_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {vm_name}")
    
    success_count = sum(1 for s in results.values() if s)
    print(f"\nCompleted: {success_count}/{len(vm_list)} successful")
```

#### 5. **Dora API Usage** (Advanced Discovery)

The Dora module allows you to discover VMs and hypervisors from the Dora API across multiple pre-configured environments.

##### A. Basic Dora Usage

Create `test_dora.py`:

```python
from chaosmonkey.platforms.dora import DoraClient

# Create client with default configuration
client = DoraClient(
    dora_host="hostname",  # Default Dora host
    api_port=8000,
    auth_port=51051
)

# List available environments
print("Available Dora environments:")
for env in DoraClient.list_environments():
    print(f"  - {env}")

# Discover specific environment
print("\nDiscovering Paytv environment...")
data = client.get_environment_data(
    environment="Paytv",
    username="your_username",
    password="your_password"
)

print(f"\nDiscovered:")
print(f"  Hypervisors: {len(data['hypervisors'])}")
print(f"  VMs: {len(data['vms'])}")

# Save to file
import json
with open("paytv_environment.json", "w") as f:
    json.dump(data, f, indent=2)
print("\n✓ Saved to paytv_environment.json")
```

##### B. Using Dora with Environment Variables

Configure `.env`:

```bash
# Add to your .env file
DORA_HOST=hostname
DORA_API_PORT=8000
DORA_AUTH_PORT=51051
DORA_USERNAME=your_username
DORA_PASSWORD=your_password
```

Create `test_dora_config.py`:

```python
from chaosmonkey.config import load_settings
from chaosmonkey.platforms.dora import DoraClient

# Load settings from .env
settings = load_settings(None)

# Create client from settings
client = DoraClient(
    dora_host=settings.platforms.dora.host,
    api_port=settings.platforms.dora.api_port,
    auth_port=settings.platforms.dora.auth_port
)

# Get credentials from settings
username = settings.platforms.dora.username
password = settings.platforms.dora.password

# Discover environment
data = client.get_environment_data(
    environment="EPB-Prod",
    username=username,
    password=password
)

print(f"Environment: EPB-Prod")
print(f"Hypervisors: {len(data['hypervisors'])}")
print(f"VMs: {len(data['vms'])}")
```

##### C. Available Dora Environments

The Dora module includes 13 pre-configured environments:

```python
from chaosmonkey.platforms.dora import DoraClient

# List all available environments
environments = DoraClient.list_environments()

# Available environments:
# - Paytv
# - Oracle-Paytv
# - DR-Paytv
# - Arvig-Staging
# - Arvig-Prod
# - EPB-Staging
# - EPB-Prod
# - Lumos-Prod
# - Comporium-Prod
# - MSG-Prod
# - Liberty-Prod
# - Midco-Staging
# - Midco-Prod

print("Available environments:")
for env in environments:
    print(f"  • {env}")
```

##### D. Comprehensive Dora Discovery Script

Create `comprehensive_dora_discovery.py`:

```python
from chaosmonkey.platforms.dora import DoraClient
from chaosmonkey.config import load_settings
import json
from datetime import datetime

def discover_all_environments():
    """Discover and analyze all Dora environments."""
    
    settings = load_settings(None)
    client = DoraClient(
        dora_host=settings.platforms.dora.host,
        api_port=settings.platforms.dora.api_port,
        auth_port=settings.platforms.dora.auth_port
    )
    
    username = settings.platforms.dora.username
    password = settings.platforms.dora.password
    
    environments = DoraClient.list_environments()
    results = {}
    
    print(f"Discovering {len(environments)} environments...\n")
    
    for env_name in environments:
        print(f"Discovering {env_name}...")
        
        try:
            data = client.get_environment_data(
                environment=env_name,
                username=username,
                password=password
            )
            
            hypervisors = data.get('hypervisors', [])
            vms = data.get('vms', [])
            
            results[env_name] = {
                'status': 'success',
                'hypervisors_count': len(hypervisors),
                'vms_count': len(vms),
                'hypervisors': hypervisors,
                'vms': vms
            }
            
            print(f"  ✓ {len(hypervisors)} hypervisors, {len(vms)} VMs")
            
        except Exception as e:
            results[env_name] = {
                'status': 'failed',
                'error': str(e)
            }
            print(f"  ✗ Failed: {e}")
    
    # Save complete results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"dora_discovery_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Complete results saved to {output_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_hypervisors = 0
    total_vms = 0
    successful = 0
    
    for env_name, data in results.items():
        if data['status'] == 'success':
            successful += 1
            total_hypervisors += data['hypervisors_count']
            total_vms += data['vms_count']
            print(f"{env_name:20} {data['hypervisors_count']:3} hypervisors, {data['vms_count']:4} VMs")
    
    print("="*60)
    print(f"Total: {successful}/{len(environments)} environments")
    print(f"       {total_hypervisors} hypervisors")
    print(f"       {total_vms} VMs")

if __name__ == "__main__":
    discover_all_environments()
```

Run it:
```bash
python comprehensive_dora_discovery.py
```

##### E. Analyzing Dora Discovery Results

Create `analyze_dora_results.py`:

```python
from chaosmonkey.platforms.dora import DoraClient
import json

# Discover environment
client = DoraClient(
    dora_host="hostname",
    api_port=8000,
    auth_port=51051
)

data = client.get_environment_data(
    environment="Paytv",
    username="your_username",
    password="your_password"
)

# Analyze hypervisors
print("HYPERVISORS:")
print("="*60)
for hypervisor in data['hypervisors']:
    print(f"\nName: {hypervisor.get('name', 'N/A')}")
    print(f"  IP: {hypervisor.get('ip_address', 'N/A')}")
    print(f"  Type: {hypervisor.get('type', 'N/A')}")
    print(f"  Status: {hypervisor.get('status', 'N/A')}")

# Analyze VMs
print("\n\nVIRTUAL MACHINES:")
print("="*60)

# Group by hypervisor
from collections import defaultdict
vms_by_host = defaultdict(list)

for vm in data['vms']:
    host = vm.get('hypervisor', 'Unknown')
    vms_by_host[host].append(vm)

for host, vms in vms_by_host.items():
    print(f"\n{host}: {len(vms)} VMs")
    for vm in vms[:5]:  # Show first 5 VMs per host
        print(f"  • {vm.get('name', 'N/A')} - {vm.get('power_state', 'N/A')}")
    
    if len(vms) > 5:
        print(f"  ... and {len(vms) - 5} more")

# Statistics
total_vms = len(data['vms'])
powered_on = sum(1 for vm in data['vms'] if vm.get('power_state') == 'poweredOn')
powered_off = total_vms - powered_on

print("\n\nSTATISTICS:")
print("="*60)
print(f"Total VMs: {total_vms}")
print(f"Powered On: {powered_on} ({powered_on/total_vms*100:.1f}%)")
print(f"Powered Off: {powered_off} ({powered_off/total_vms*100:.1f}%)")
```

##### F. Using Dora via CLI

```bash
# List all available Dora environments
chaosmonkey platforms dora-environments

# Discover specific environment
chaosmonkey platforms dora-discover "Paytv" \
  --username your_username \
  --password your_password

# Discover with custom output file
chaosmonkey platforms dora-discover "EPB-Prod" \
  --username your_username \
  --password your_password \
  --output epb_production.json

# Discover using environment variables (no need for --username/--password)
export DORA_USERNAME=your_username
export DORA_PASSWORD=your_password
chaosmonkey platforms dora-discover "Arvig-Prod"

# View results nicely formatted
chaosmonkey platforms dora-discover "Lumos-Prod" | python -m json.tool
```

##### G. Integration with vSphere Discovery

Create `dora_to_vsphere.py` to map Dora data to vSphere:

```python
from chaosmonkey.platforms.dora import DoraClient
from chaosmonkey.platforms.vsphere import VSpherePlatform
from chaosmonkey.config import load_settings

settings = load_settings(None)

# Get environment data from Dora
dora_client = DoraClient(
    dora_host=settings.platforms.dora.host,
    api_port=settings.platforms.dora.api_port,
    auth_port=settings.platforms.dora.auth_port
)

dora_data = dora_client.get_environment_data(
    environment="EPB-Prod",
    username=settings.platforms.dora.username,
    password=settings.platforms.dora.password
)

print(f"Dora discovered {len(dora_data['vms'])} VMs")

# Now verify with vSphere direct connection
with VSpherePlatform(
    server=settings.platforms.vsphere.server,
    username=settings.platforms.vsphere.username,
    password=settings.platforms.vsphere.password,
    insecure=True
) as vsphere:
    vsphere_vms = vsphere.discover_vms()
    print(f"vSphere discovered {len(vsphere_vms)} VMs")
    
    # Compare VM names
    dora_vm_names = {vm['name'] for vm in dora_data['vms']}
    vsphere_vm_names = {vm.name for vm in vsphere_vms}
    
    # Find differences
    only_in_dora = dora_vm_names - vsphere_vm_names
    only_in_vsphere = vsphere_vm_names - dora_vm_names
    
    print(f"\nComparison:")
    print(f"  Common VMs: {len(dora_vm_names & vsphere_vm_names)}")
    print(f"  Only in Dora: {len(only_in_dora)}")
    print(f"  Only in vSphere: {len(only_in_vsphere)}")
    
    if only_in_dora:
        print(f"\n  VMs only in Dora (first 5):")
        for vm in list(only_in_dora)[:5]:
            print(f"    - {vm}")
```

##### H. Dora Module Use Cases

**Use Case 1: Multi-Environment Discovery**
```python
# Discover all production environments
prod_environments = ["Arvig-Prod", "EPB-Prod", "Lumos-Prod", 
                     "Comporium-Prod", "MSG-Prod", "Liberty-Prod", "Midco-Prod"]

client = DoraClient(...)
for env in prod_environments:
    data = client.get_environment_data(env, username, password)
    print(f"{env}: {len(data['vms'])} VMs")
```

**Use Case 2: Automated Inventory Reports**
```python
# Generate inventory report from Dora
data = client.get_environment_data("Paytv", username, password)

with open("vm_inventory.csv", "w") as f:
    f.write("VM Name,Hypervisor,Power State,Environment\n")
    for vm in data['vms']:
        f.write(f"{vm['name']},{vm['hypervisor']},{vm['power_state']},Paytv\n")
```

**Use Case 3: Pre-Chaos Validation**
```python
# Before running chaos experiments, validate environment state
dora_data = client.get_environment_data("EPB-Staging", username, password)

# Check if target VM exists
target_vm = "web-server-01"
vm_exists = any(vm['name'] == target_vm for vm in dora_data['vms'])

if not vm_exists:
    print(f"✗ VM {target_vm} not found in Dora inventory!")
else:
    print(f"✓ VM {target_vm} found, proceeding with chaos experiment")
```

---

### D. Combining Multiple Platforms

#### Example: Cross-Platform Discovery

Create `multi_platform_discovery.py`:

```python
from chaosmonkey.config import load_settings
from chaosmonkey.core.platform_orchestrator import PlatformOrchestrator
from chaosmonkey.platforms.dora import DoraClient

settings = load_settings(None)
orchestrator = PlatformOrchestrator(settings)

print("="*60)
print("MULTI-PLATFORM DISCOVERY")
print("="*60)

# 1. Discover via vSphere
print("\n1. vSphere Discovery:")
vsphere_vms = orchestrator.discover_vms("vsphere")
print(f"   Found {len(vsphere_vms)} VMs")

# 2. Discover via OLVM
print("\n2. OLVM Discovery:")
olvm_vms = orchestrator.discover_vms("olvm")
print(f"   Found {len(olvm_vms)} VMs")

# 3. Discover via Dora
print("\n3. Dora Discovery (Paytv):")
dora_client = DoraClient(
    dora_host=settings.platforms.dora.host,
    api_port=settings.platforms.dora.api_port,
    auth_port=settings.platforms.dora.auth_port
)
dora_data = dora_client.get_environment_data(
    "Paytv",
    settings.platforms.dora.username,
    settings.platforms.dora.password
)
print(f"   Found {len(dora_data['vms'])} VMs")

# Summary
print("\n" + "="*60)
print(f"Total VMs across all platforms: {len(vsphere_vms) + len(olvm_vms) + len(dora_data['vms'])}")
print("="*60)
```

---

### C. Chaos Experiments (Advanced)

#### 1. **Using Built-in Templates**

```bash
# Execute vSphere VM power off experiment
chaosmonkey execute \
  --chaos-type vsphere-vm-poweroff \
  --override vm_name=web-01 \
  --override vsphere_server=vcenter.example.com \
  --override vsphere_username=administrator@vsphere.local \
  --override vsphere_password=your_password \
  --override graceful=true

# Or use environment variables (cleaner)
chaosmonkey execute --chaos-type vsphere-vm-poweroff --override vm_name=web-01

# Execute OLVM VM shutdown
chaosmonkey execute --chaos-type olvm-vm-shutdown --override vm_name=web-01

# Execute VM reboot
chaosmonkey execute --chaos-type vsphere-vm-reboot --override vm_name=web-01
```

#### 2. **Create Custom Experiment**

Create `my_vm_chaos.json`:

```json
{
  "version": "1.0.0",
  "title": "Web Server VM Failure",
  "description": "Test application resilience to VM failure",
  "steady-state-hypothesis": {
    "title": "Application is healthy",
    "probes": [
      {
        "type": "probe",
        "name": "check-web-service",
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
      "name": "Power off web server VM",
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
      "name": "wait-30-seconds",
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
      "name": "Restore web server VM",
      "provider": {
        "type": "python",
        "module": "chaosmonkey.stubs.actions",
        "func": "vm_power_on",
        "arguments": {
          "vm_name": "web-01",
          "platform_type": "vsphere",
          "timeout": 300,
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
chaosmonkey execute --experiment my_vm_chaos.json
```

---

## Complete Working Examples

### Example 1: Test vSphere Connection

```bash
# Create test script
cat > test_connection.py << 'EOF'
from chaosmonkey.platforms.vsphere import VSpherePlatform
import os

server = os.getenv('VSPHERE_SERVER')
username = os.getenv('VSPHERE_USERNAME')
password = os.getenv('VSPHERE_PASSWORD')

print(f"Testing connection to {server}...")

try:
    platform = VSpherePlatform(
        server=server,
        username=username,
        password=password,
        insecure=True
    )
    platform.connect()
    print("✓ Connected successfully!")
    
    # Quick discovery
    vms = platform.discover_vms()
    print(f"✓ Found {len(vms)} VMs")
    
    platform.disconnect()
    print("✓ Disconnected")
except Exception as e:
    print(f"✗ Connection failed: {e}")
EOF

# Run it
python test_connection.py
```

### Example 2: Power Cycle a VM

```bash
cat > power_cycle.py << 'EOF'
from chaosmonkey.config import load_settings
from chaosmonkey.core.platform_orchestrator import PlatformOrchestrator
import time

settings = load_settings(None)
orchestrator = PlatformOrchestrator(settings)

vm_name = "test-vm-01"  # Change to your test VM
platform = "vsphere"     # or "olvm"

print(f"Power cycling {vm_name}...")

# Get current state
vm = orchestrator.get_vm_info(platform, vm_name)
print(f"Current state: {vm.power_state.value}")

# Power off
print("Powering off...")
orchestrator.power_off_vm(platform, vm_name, graceful=True)

# Wait
print("Waiting 10 seconds...")
time.sleep(10)

# Power on
print("Powering on...")
orchestrator.power_on_vm(platform, vm_name)

print("✓ Power cycle complete!")
EOF

python power_cycle.py
```

### Example 3: Discover and Report

```bash
cat > discover_report.py << 'EOF'
from chaosmonkey.config import load_settings
from chaosmonkey.core.platform_orchestrator import PlatformOrchestrator
from chaosmonkey.platforms.base import VMPowerState

settings = load_settings(None)
orchestrator = PlatformOrchestrator(settings)

print("Discovering VMs on vSphere...")
vms = orchestrator.discover_vms("vsphere")

# Group by power state
powered_on = [vm for vm in vms if vm.power_state == VMPowerState.POWERED_ON]
powered_off = [vm for vm in vms if vm.power_state == VMPowerState.POWERED_OFF]

print(f"\nSummary:")
print(f"  Total VMs: {len(vms)}")
print(f"  Powered On: {len(powered_on)}")
print(f"  Powered Off: {len(powered_off)}")

print(f"\nPowered On VMs:")
for vm in powered_on[:10]:  # Show first 10
    print(f"  - {vm.name} (Host: {vm.host})")

# Calculate total resources
total_cpu = sum(vm.cpu_count for vm in vms if vm.cpu_count)
total_memory_gb = sum(vm.memory_mb / 1024 for vm in vms if vm.memory_mb)

print(f"\nTotal Resources:")
print(f"  CPUs: {total_cpu}")
print(f"  Memory: {total_memory_gb:.1f} GB")
EOF

python discover_report.py
```

---

## Troubleshooting

### Issue: Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'ovirtsdk4'
pip install ovirt-engine-sdk-python

# Error: ModuleNotFoundError: No module named 'pyVmomi'
pip install pyvmomi

# Or install all at once
pip install -e '.[platforms]'
```

### Issue: Connection Fails

```python
# Test connection manually
python -c "
from chaosmonkey.platforms.vsphere import VSpherePlatform
p = VSpherePlatform('vcenter.example.com', 'user', 'pass')
try:
    p.connect()
    print('Connected!')
    p.disconnect()
except Exception as e:
    print(f'Failed: {e}')
"
```

### Issue: Environment Variables Not Loaded

```bash
# Check if .env is being loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('VSPHERE_SERVER'))"

# Or check in the project
python -c "from chaosmonkey.config import load_settings; s = load_settings(None); print(s.platforms.vsphere.server)"
```

---

## Quick Command Reference

```bash
# Discovery
chaosmonkey platforms discover-vms --platform vsphere
chaosmonkey platforms discover-vms --platform olvm --name "web-*"
chaosmonkey platforms vm-info web-01 --platform vsphere

# Dora Discovery
chaosmonkey platforms dora-environments
chaosmonkey platforms dora-discover "Paytv" --username user --password pass
chaosmonkey platforms dora-discover "EPB-Prod" --output epb.json

# Power Operations
chaosmonkey platforms power-on web-01 --platform vsphere
chaosmonkey platforms power-off web-01 --platform vsphere --graceful
chaosmonkey platforms reboot web-01 --platform vsphere

# Chaos Experiments
chaosmonkey execute --chaos-type vsphere-vm-poweroff --override vm_name=web-01
chaosmonkey execute --chaos-type olvm-vm-shutdown --override vm_name=web-01
chaosmonkey execute --experiment my_experiment.json

# Help
chaosmonkey --help
chaosmonkey platforms --help
chaosmonkey platforms discover-vms --help
chaosmonkey platforms dora-discover --help
```

---

## Dora Module - Complete Feature Summary

### What is Dora?

Dora is a centralized API service that provides VM and hypervisor inventory across multiple vSphere environments. The ChaosMonkey Dora module allows you to:

1. **Discover VMs** across 13 pre-configured environments
2. **Query hypervisor information** without direct vCenter access
3. **Generate inventory reports** for multiple environments
4. **Validate chaos targets** before running experiments

### Supported Environments

- **Paytv** environments: Paytv, Oracle-Paytv, DR-Paytv
- **Arvig**: Arvig-Staging, Arvig-Prod
- **EPB**: EPB-Staging, EPB-Prod
- **Lumos**: Lumos-Prod
- **Comporium**: Comporium-Prod
- **MSG**: MSG-Prod
- **Liberty**: Liberty-Prod
- **Midco**: Midco-Staging, Midco-Prod

### Quick Dora Examples

```bash
# List all environments
chaosmonkey platforms dora-environments

# Discover a single environment
chaosmonkey platforms dora-discover "Paytv" \
  --username admin \
  --password secret

# Discover with output file
chaosmonkey platforms dora-discover "EPB-Prod" \
  --username admin \
  --password secret \
  --output epb_inventory.json

# Use environment variables (cleaner)
export DORA_USERNAME=admin
export DORA_PASSWORD=secret
chaosmonkey platforms dora-discover "Lumos-Prod"
```

### Python API Quick Reference

```python
from chaosmonkey.platforms.dora import DoraClient

# Initialize
client = DoraClient(
    dora_host="hostname",
    api_port=8000,
    auth_port=51051
)

# List environments
environments = DoraClient.list_environments()

# Discover environment
data = client.get_environment_data(
    environment="Paytv",
    username="admin",
    password="secret"
)

# Access data
print(f"Hypervisors: {len(data['hypervisors'])}")
print(f"VMs: {len(data['vms'])}")

# Iterate VMs
for vm in data['vms']:
    print(f"{vm['name']}: {vm['power_state']}")
```

### Common Dora Workflows

**1. Pre-Chaos VM Validation:**
```python
# Verify VM exists before running chaos experiment
data = client.get_environment_data("EPB-Staging", user, pass)
vm_names = [vm['name'] for vm in data['vms']]
if 'target-vm-01' not in vm_names:
    raise ValueError("Target VM not found!")
```

**2. Multi-Environment Discovery:**
```python
# Discover all production environments
for env in ["Arvig-Prod", "EPB-Prod", "Lumos-Prod"]:
    data = client.get_environment_data(env, user, pass)
    print(f"{env}: {len(data['vms'])} VMs")
```

**3. Inventory Export:**
```python
# Export complete inventory to CSV
import csv
data = client.get_environment_data("Paytv", user, pass)
with open('inventory.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Name', 'Host', 'State'])
    for vm in data['vms']:
        writer.writerow([vm['name'], vm['hypervisor'], vm['power_state']])
```

---

## Next Steps

1. **Start with discovery** to test your connection
2. **Try Dora discovery** to see available VMs across environments
3. **Test power operations** on a non-critical VM
4. **Create simple experiments** to test failover scenarios
5. **Integrate into CI/CD** for automated chaos testing

Need more help? Check:
- `docs/VM_PLATFORMS_GUIDE.md` - Complete guide
- `VM_PLATFORMS_QUICKSTART.md` - Quick start
- `MIGRATION_GUIDE.md` - Migration from old scripts
