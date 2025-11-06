#!/usr/bin/env python3
"""Test health endpoint URL generation"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from chaosmonkey.core.experiments import ExperimentTemplateRegistry
from chaosmonkey.core.nomad import NomadClient
from chaosmonkey.config import Settings

def test_health_endpoint():
    """Test health endpoint URL generation"""
    print("🧪 Testing health endpoint URL generation...")
    
    # Get a service target from Nomad
    settings = Settings()
    nomad_client = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region, 
        token=settings.nomad.token,
        namespace=settings.nomad.namespace,
    )
    
    targets = nomad_client.enumerate_targets()
    service_targets = [t for t in targets if t.kind == "service" and t.attributes.get("address")]
    
    if not service_targets:
        print("❌ No service targets with addresses found")
        return
        
    # Find a target that might have a health endpoint
    target = service_targets[0]
    print(f"🎯 Using target: {target.identifier}")
    print(f"   Address: {target.attributes.get('address')}")
    print(f"   Port: {target.attributes.get('port')}")
    print(f"   Health endpoint: {target.attributes.get('health_endpoint', 'NOT FOUND')}")
    
    # Generate experiment using k6 load test
    template_registry = ExperimentTemplateRegistry()
    experiment = template_registry.render(
        chaos_type="k6_load_test",
        target=target,
        overrides={}
    )
    
    print(f"\n📋 Generated experiment:")
    print(f"   Target URL: {experiment['configuration'].get('target_url')}")
    print(f"   Health endpoint: {experiment['configuration'].get('health_endpoint')}")
    print(f"   Full health URL: {experiment['configuration'].get('target_url')}{experiment['configuration'].get('health_endpoint')}")
    
    # Check the probe configuration  
    probes = experiment.get("steady-state-hypothesis", {}).get("probes", [])
    if probes:
        probe = probes[0]
        probe_url = probe.get("provider", {}).get("url", "")
        print(f"   Probe URL: {probe_url}")
        
        if "/monitoring/health" in probe_url:
            print("✅ Health endpoint correctly set to /monitoring/health")
        elif "/health" in probe_url:
            print("ℹ️ Health endpoint using /health (may work)")
        else:
            print("⚠️ Health endpoint not found in probe URL")
    else:
        print("❌ No probes found in experiment")

if __name__ == "__main__":
    test_health_endpoint()