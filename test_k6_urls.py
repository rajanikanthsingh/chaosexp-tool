#!/usr/bin/env python3
"""Test K6 URL generation with real Nomad data"""

import sys
import os
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.config import Settings
from chaosmonkey.core.orchestrator import ChaosOrchestrator
from chaosmonkey.core.experiments import ExperimentTemplateRegistry

def test_url_generation():
    """Test what URLs would be generated for K6 tests"""
    print("🔍 Testing K6 URL generation with real Nomad data...")
    
    try:
        settings = Settings()
        orchestrator = ChaosOrchestrator(settings)
        registry = ExperimentTemplateRegistry()
        
        print(f"📡 Connecting to Nomad: {settings.nomad.address}")
        
        # Get real targets
        targets = orchestrator.enumerate_targets("k6_load_test")
        print(f"📊 Found {len(targets)} targets")
        
        if len(targets) <= 4:
            print("⚠️  Warning: Only getting stub data, not real Nomad data")
        
        # Show URL generation for first few services
        service_targets = [t for t in targets if t.kind == "service"][:5]
        
        if service_targets:
            print("\n🎯 Service targets and their generated URLs:")
            for target in service_targets:
                url = registry._build_target_url(target)
                print(f"  Service: {target.identifier}")
                print(f"    URL: {url}")
                print(f"    Node: {target.attributes.get('node', 'unknown')}")
                print(f"    Address: {target.attributes.get('address', 'none')}")
                print(f"    Port: {target.attributes.get('port', 8080)}")
                print()
        else:
            print("❌ No service targets found")
            
        # Show node targets
        node_targets = [t for t in targets if t.kind == "node"][:3]
        if node_targets:
            print("🖥️  Node targets:")
            for target in node_targets:
                print(f"  Node: {target.identifier}")
                print(f"    Status: {target.attributes.get('status', 'unknown')}")
                print()
                
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure NOMAD_ADDR and NOMAD_TOKEN are set correctly")

if __name__ == "__main__":
    test_url_generation()