#!/usr/bin/env python3
"""Test script to verify VM status endpoint."""

import json
import sys
import os
from pathlib import Path

# When running this script directly, ensure the repository src folder is on sys.path
# so `import chaosmonkey` works even outside an installed environment.
REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def test_dora_status_endpoint():
    """Test the /api/dora/vm-status endpoint."""
    print("Testing VM status retrieval from Dora API...")
    print("-" * 60)
    
    # Test data
    vm_name = "hostname"
    environment = "Dev1"
    
    print(f"VM Name: {vm_name}")
    print(f"Environment: {environment}")
    print()
    
    # Load configuration
    try:
        from chaosmonkey.config import load_settings
        settings = load_settings(None)
        print("✓ Loaded configuration")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False

    # 1) Try querying vSphere API via VSpherePlatform
    try:
        print("\nAttempting vSphere API lookup...")
        from chaosmonkey.platforms.vsphere import VSpherePlatform

        vs = VSpherePlatform(
            server=settings.platforms.vsphere.server,
            username=settings.platforms.vsphere.username,
            password=settings.platforms.vsphere.password,
            port=settings.platforms.vsphere.port,
            insecure=settings.platforms.vsphere.insecure,
        )

        with vs:
            try:
                vm_info = vs.get_vm(vm_name)
                print(f"✅ vSphere: VM '{vm_name}' found")
                print(f"   Power state: {vm_info.power_state}")
                print(f"   Host: {vm_info.host}")
                print(f"   Datacenter: {vm_info.datacenter}")
                print(f"   Guest OS: {vm_info.guest_os}")
                return True
            except ValueError:
                print(f"vSphere: VM '{vm_name}' not found via vSphere API")
    except ImportError as ie:
        print(f"vSphere API not available: {ie}")
    except Exception as e:
        print(f"vSphere API lookup failed: {e}")

    # 2) Fallback: try govc CLI (if installed and configured)
    try:
        print("\nAttempting govc CLI lookup...")
        import subprocess
        res = subprocess.run(["govc", "vm.info", "-json", vm_name], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout:
            j = json.loads(res.stdout)
            # govc returns a structure with VirtualMachines
            vms = j.get('VirtualMachines') or j.get('VirtualMachine') or []
            if vms:
                vm = vms[0]
                # Try various paths for power state
                state = vm.get('Runtime', {}).get('PowerState') if isinstance(vm, dict) else None
                print(f"✅ govc: Found VM '{vm_name}'")
                print(f"   Raw govc data (truncated): {json.dumps(vm)[:1000]}")
                return True
        else:
            print(f"govc not available or VM not found (exit {res.returncode})")
    except FileNotFoundError:
        print("govc CLI not installed or not in PATH")
    except Exception as e:
        print(f"govc lookup failed: {e}")

    # 3) Final fallback: Dora API
    try:
        print("\nFalling back to Dora API lookup...")
        from chaosmonkey.platforms.dora import DoraClient

        client = DoraClient(
            dora_host=settings.platforms.dora.host,
            api_port=settings.platforms.dora.api_port,
            auth_port=settings.platforms.dora.auth_port,
        )

        data = client.get_environment_data(
            environment=environment,
            username=settings.platforms.dora.username,
            password=settings.platforms.dora.password,
        )

        vms_data = data.get('vms', {})
        if isinstance(vms_data, dict) and 'items' in vms_data:
            vms = vms_data['items']
        elif isinstance(vms_data, list):
            vms = vms_data
        else:
            vms = []

        print(f"✓ Found {len(vms)} VMs in Dora environment")

        vm_found = None
        for vm in vms:
            if vm.get('name') == vm_name:
                vm_found = vm
                break

        if vm_found:
            print(f"✅ Dora: VM Found: {vm_name}")
            print(f"   Status: {vm_found.get('state', 'unknown')}")
            print(f"   Host: {vm_found.get('host', 'N/A')}")
            print(json.dumps(vm_found, indent=2))
            return True
        else:
            print(f"❌ VM not found in Dora: {vm_name}")
            return False
    except Exception as e:
        print(f"❌ Dora lookup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_dora_status_endpoint()
    sys.exit(0 if success else 1)
