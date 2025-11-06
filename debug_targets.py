#!/usr/bin/env python3
"""Debug script to test Nomad target enumeration."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chaosmonkey.config import load_settings
from chaosmonkey.core.orchestrator import ChaosOrchestrator

def main():
    print("=" * 80)
    print("ChaosMonkey Target Enumeration Debug")
    print("=" * 80)
    
    # Load config
    print("\n1. Loading configuration...")
    config = load_settings(None)
    print(f"   NOMAD_ADDR: {config.nomad.address}")
    print(f"   NOMAD_NAMESPACE: {config.nomad.namespace or 'default'}")
    print(f"   NOMAD_TOKEN: {'*' * 8 if config.nomad.token else 'Not set'}")
    
    # Create orchestrator
    print("\n2. Creating orchestrator...")
    orchestrator = ChaosOrchestrator(config)
    
    # Test discover_services
    print("\n3. Testing discover_services()...")
    try:
        services = orchestrator._nomad.discover_services()
        print(f"   ✅ Found {len(services)} services")
        if services:
            for i, svc in enumerate(services[:5], 1):  # Show first 5
                print(f"      {i}. ID: {svc.get('ID')}, Name: {svc.get('Name')}, Type: {svc.get('Type')}")
            if len(services) > 5:
                print(f"      ... and {len(services) - 5} more")
        else:
            print("   ⚠️  No services returned!")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test list_allocations
    print("\n4. Testing list_allocations()...")
    try:
        allocations = orchestrator._nomad.list_allocations()
        print(f"   ✅ Found {len(allocations)} allocations")
        if allocations:
            for i, alloc in enumerate(allocations[:5], 1):  # Show first 5
                print(f"      {i}. ID: {alloc.get('ID')[:12]}..., Name: {alloc.get('Name')}, Status: {alloc.get('ClientStatus')}")
            if len(allocations) > 5:
                print(f"      ... and {len(allocations) - 5} more")
        else:
            print("   ⚠️  No allocations returned!")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test enumerate_targets
    print("\n5. Testing enumerate_targets()...")
    try:
        targets = orchestrator.enumerate_targets()
        print(f"   ✅ Found {len(targets)} targets")
        if targets:
            for i, target in enumerate(targets[:10], 1):  # Show first 10
                print(f"      {i}. ID: {target.identifier}")
                print(f"         Name: {target.attributes.get('name')}")
                print(f"         Kind: {target.kind}")
                print(f"         Node: {target.attributes.get('node')}")
                print(f"         Status: {target.attributes.get('status')}")
                print()
            if len(targets) > 10:
                print(f"      ... and {len(targets) - 10} more")
        else:
            print("   ⚠️  No targets returned!")
            print("\n   This is why you're getting the error:")
            print("   'Target mobi-platform-account-service-job not found in catalog'")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Try to find specific target
    print("\n6. Looking for 'mobi-platform-account-service-job'...")
    try:
        all_targets = orchestrator.enumerate_targets()
        found = False
        for target in all_targets:
            if 'mobi-platform-account-service-job' in target.identifier.lower() or \
               'mobi-platform-account-service' in target.attributes.get('name', '').lower():
                print(f"   ✅ Found matching target!")
                print(f"      ID: {target.identifier}")
                print(f"      Name: {target.attributes.get('name')}")
                found = True
                break
        
        if not found:
            print(f"   ⚠️  Target 'mobi-platform-account-service-job' not found")
            print(f"\n   Available target IDs:")
            for target in all_targets[:20]:
                print(f"      - {target.identifier}")
            if len(all_targets) > 20:
                print(f"      ... and {len(all_targets) - 20} more")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("Debug complete")
    print("=" * 80)

if __name__ == "__main__":
    main()
