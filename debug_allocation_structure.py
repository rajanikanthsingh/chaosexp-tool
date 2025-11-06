#!/usr/bin/env python3
"""Debug allocation structure"""

import sys
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.config import Settings
from chaosmonkey.core.nomad import NomadClient
import json

def debug_allocation_structure():
    """Debug allocation structure"""
    print("🔍 Debugging allocation structure...")
    
    settings = Settings()
    client = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region,
        token=settings.nomad.token,
        namespace=settings.nomad.namespace,
    )
    
    # Get first allocation and examine its structure
    allocations = client.list_allocations()
    
    if allocations:
        print("\n📦 First allocation structure:")
        first_alloc = allocations[0]
        
        # Show relevant fields
        interesting_fields = ['Name', 'JobID', 'TaskGroup', 'ID', 'NodeID']
        for field in interesting_fields:
            print(f"  {field}: {first_alloc.get(field, 'NOT_FOUND')}")
        
        # Show the services from this allocation
        print(f"\n🎯 Services in first allocation:")
        services_data = first_alloc.get('Services', {})
        for service_name, service_info in services_data.items():
            print(f"  Service: {service_name}")
            for key, value in service_info.items():
                if key in ['Service', 'Port', 'PortLabel', 'Tags']:
                    print(f"    {key}: {value}")
    
    # Get services and show their structure
    services = client.discover_services()
    if services:
        print(f"\n🎯 First service structure:")
        first_service = services[0]
        print(f"Service keys: {list(first_service.keys())}")
        for key, value in first_service.items():
            if key in ['Name', 'ID', 'Address', 'Port', 'Tags']:
                print(f"  {key}: {value}")

if __name__ == "__main__":
    debug_allocation_structure()