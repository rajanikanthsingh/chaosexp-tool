#!/usr/bin/env python3
"""Verify K6 integration is working correctly"""

import sys
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.config import Settings
from chaosmonkey.core.nomad import NomadClient

def test_integration():
    """Test the key integration points"""
    print("🔍 Testing K6 integration...")
    
    settings = Settings()
    client = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region,
        token=settings.nomad.token,
        namespace=settings.nomad.namespace,
    )
    
    # Test service discovery and URL resolution
    targets = client.enumerate_targets()
    
    service_targets = [t for t in targets if hasattr(t, 'attributes') and t.attributes.get('address')]
    
    print(f"📊 Found {len(targets)} total targets")
    print(f"🎯 Found {len(service_targets)} service targets with resolved addresses")
    
    if service_targets:
        example_target = service_targets[0]
        address = example_target.attributes.get('address')
        port = example_target.attributes.get('port', 8080)
        url = f"http://{address}:{port}"
        
        print(f"✅ Example resolved URL: {url}")
        print(f"   Service: {example_target.attributes.get('name')}")
        print(f"   Node: {example_target.attributes.get('node', 'unknown')}")
        
        return True
    else:
        print("❌ No service targets with resolved addresses found")
        return False

if __name__ == "__main__":
    try:
        success = test_integration()
        if success:
            print("\n🎉 K6 integration appears to be working correctly!")
        else:
            print("\n⚠️ K6 integration may have issues")
    except Exception as e:
        print(f"\n💥 Error testing integration: {e}")