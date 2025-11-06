#!/usr/bin/env python3
"""Debug allocation matching"""

import sys
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.config import Settings
from chaosmonkey.core.nomad import NomadClient

def debug_allocations():
    """Debug allocation matching"""
    print("🔍 Debugging allocation matching...")
    
    settings = Settings()
    client = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region,
        token=settings.nomad.token,
        namespace=settings.nomad.namespace,
    )
    
    # Get services and allocations
    services = client.discover_services()
    allocations = client.list_allocations()
    
    print(f"📊 Found {len(services)} services and {len(allocations)} allocations")
    
    # Show first few services
    print("\n🎯 First 5 services:")
    for service in services[:5]:
        print(f"  Service: {service['Name']} (ID: {service.get('ID', 'None')})")
    
    # Show first few allocations
    print("\n📦 First 5 allocations:")
    for alloc in allocations[:5]:
        print(f"  Allocation: {alloc.get('Name', 'Unknown')} -> Node: {alloc.get('NodeID', 'Unknown')}")
    
    # Check allocation matching
    allocation_index = {alloc["Name"]: alloc for alloc in allocations}
    print("\n🔍 Testing service-to-allocation matching:")
    
    for service in services[:5]:
        service_name = service["Name"]
        alloc = allocation_index.get(service_name, {})
        if alloc:
            print(f"  ✅ {service_name} -> Node: {alloc.get('NodeID', 'Unknown')}")
        else:
            print(f"  ❌ {service_name} -> No matching allocation found")
    
    # Show unique allocation names
    alloc_names = set(alloc.get("Name", "Unknown") for alloc in allocations)
    print(f"\n📋 Unique allocation names ({len(alloc_names)}):")
    for name in sorted(list(alloc_names))[:10]:
        print(f"  - {name}")
    
    if len(alloc_names) > 10:
        print(f"  ... and {len(alloc_names) - 10} more")

if __name__ == "__main__":
    debug_allocations()