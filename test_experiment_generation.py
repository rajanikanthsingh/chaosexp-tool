#!/usr/bin/env python3
"""
Test actual K6 experiment generation with health endpoint configuration
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add src to path to import chaosmonkey modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from chaosmonkey.core.nomad import NomadClient
from chaosmonkey.core.experiments import ExperimentTemplateRegistry
from chaosmonkey.config import Settings, NomadSettings

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

def main():
    print("🧪 Testing complete K6 experiment generation with health endpoint...")
    
    # Load configuration
    import os
    nomad_client = NomadClient(
        address=os.getenv("NOMAD_ADDR", "http://127.0.0.1:4646"),
        region=os.getenv("NOMAD_REGION"),
        token=os.getenv("NOMAD_TOKEN"),
        namespace=os.getenv("NOMAD_NAMESPACE")
    )
    experiment_registry = ExperimentTemplateRegistry()
    
    # Get a target with a health endpoint
    targets = nomad_client.enumerate_targets()
    test_target = None
    
    for target in targets:
        if hasattr(target, 'attributes') and target.attributes.get('health_endpoint'):
            # Skip cadvisor to test with a different service
            if target.identifier.lower() != 'cadvisor':
                test_target = target
                break
    
    if not test_target:
        print("❌ No targets with health endpoints found")
        return
    
    print(f"🎯 Selected target: {test_target.identifier}")
    print(f"   Kind: {test_target.kind}")
    print(f"   Address: {test_target.attributes.get('address', 'N/A')}")
    print(f"   Port: {test_target.attributes.get('port', 'N/A')}")
    print(f"   Health endpoint: {test_target.attributes.get('health_endpoint', 'N/A')}")
    
    # Generate a K6 load test experiment
    experiment_json = experiment_registry.render(
        chaos_type="k6_load_test",
        target=test_target,
        overrides={
            "duration": "30s",
            "virtual_users": 5,
            "ramp_up_time": "10s",
            "ramp_down_time": "5s"
        }
    )
    
    print("\n📋 Generated experiment content:")
    print(f"   Title: {experiment_json.get('title', 'N/A')}")
    print(f"   Description: {experiment_json.get('description', 'N/A')}")
    
    # Print configuration to verify variable substitution
    config = experiment_json.get('configuration', {})
    print(f"   Configuration variables:")
    print(f"     target_url: {config.get('target_url', 'N/A')}")
    print(f"     health_endpoint: {config.get('health_endpoint', 'N/A')}")
    
    # Check steady state probe
    steady_state = experiment_json.get('steady-state-hypothesis', {})
    probes = steady_state.get('probes', [])
    
    if probes:
        probe = probes[0]
        probe_url = probe.get('provider', {}).get('arguments', {}).get('url', 'N/A')
        print(f"   Steady state probe URL template: {probe_url}")
        
        # Verify the health endpoint is properly configured
        address = test_target.attributes.get('address', 'localhost')
        port = test_target.attributes.get('port', '8080')
        health_endpoint = test_target.attributes.get('health_endpoint', '/health')
        expected_health_url = f"http://{address}:{port}{health_endpoint}"
        print(f"   Expected health URL: {expected_health_url}")
        
        # Check if template variables are properly set
        if "${target_url}" in probe_url and "${health_endpoint}" in probe_url:
            print("✅ Health endpoint template correctly configured!")
        else:
            print(f"❌ Health endpoint template issue")
    else:
        print("❌ No steady state probes found")
    
    # Check method configuration
    method = experiment_json.get('method', [])
    if method:
        k6_action = method[0]
        k6_url = k6_action.get('provider', {}).get('arguments', {}).get('target_url', 'N/A')
        expected_target_url = f"http://{address}:{port}"
        print(f"   K6 target URL template: {k6_url}")
        print(f"   Expected target URL: {expected_target_url}")
        
        if "${target_url}" in str(k6_url) or k6_url == expected_target_url:
            print("✅ K6 target URL correctly configured!")
        else:
            print(f"❌ K6 target URL mismatch")
    else:
        print("❌ No K6 method found")

if __name__ == "__main__":
    main()