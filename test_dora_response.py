#!/usr/bin/env python3
"""Test Dora API response format."""

import json
from chaosmonkey.platforms.dora import DoraClient
from chaosmonkey.config import load_settings

def test_dora_response():
    """Test what Dora API actually returns."""
    
    # Load settings
    settings = load_settings(None)
    
    # Create Dora client
    client = DoraClient(
        dora_host=settings.platforms.dora.host,
        api_port=settings.platforms.dora.api_port,
        auth_port=settings.platforms.dora.auth_port
    )
    
    # Get credentials
    username = settings.platforms.dora.username
    password = settings.platforms.dora.password
    
    print("Testing Dora API response...")
    print(f"Host: {settings.platforms.dora.host}")
    print(f"Environment: Dev\n")
    
    try:
        # Fetch environment data
        data = client.get_environment_data(
            environment="Dev",
            username=username,
            password=password
        )
        
        print("=" * 80)
        print("FULL RESPONSE:")
        print("=" * 80)
        print(json.dumps(data, indent=2, default=str))
        
        print("\n" + "=" * 80)
        print("DATA STRUCTURE ANALYSIS:")
        print("=" * 80)
        print(f"Response type: {type(data)}")
        print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        
        if 'vms' in data:
            vms = data['vms']
            print(f"\nVMs type: {type(vms)}")
            if isinstance(vms, dict):
                print(f"VMs keys: {list(vms.keys())}")
                print(f"VMs length: {len(vms)}")
            elif isinstance(vms, list):
                print(f"VMs length: {len(vms)}")
                if vms:
                    print(f"First VM type: {type(vms[0])}")
                    print(f"First VM: {json.dumps(vms[0], indent=2, default=str)}")
            else:
                print(f"VMs is a string or other type: {vms[:200] if isinstance(vms, str) else vms}")
        
        if 'hypervisors' in data:
            hypervisors = data['hypervisors']
            print(f"\nHypervisors type: {type(hypervisors)}")
            if isinstance(hypervisors, dict):
                print(f"Hypervisors keys: {list(hypervisors.keys())}")
            elif isinstance(hypervisors, list):
                print(f"Hypervisors length: {len(hypervisors)}")
            
    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        print("\nFull traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_dora_response()
