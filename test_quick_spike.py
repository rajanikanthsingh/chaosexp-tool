#!/usr/bin/env python3
"""Test quick spike test template"""

import sys
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.core.experiments import ExperimentTemplateRegistry
from chaosmonkey.core.nomad import NomadClient
from chaosmonkey.config import Settings

def test_quick_spike():
    """Test the quick spike test template"""
    print("🧪 Testing quick spike test template...")
    
    # Get a target from Nomad
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
        
    target = service_targets[0]
    print(f"🎯 Using target: {target.identifier}")
    print(f"   Address: {target.attributes.get('address')}")
    print(f"   Port: {target.attributes.get('port')}")
    
    # Generate experiment using quick spike test
    template_registry = ExperimentTemplateRegistry()
    experiment = template_registry.render(
        chaos_type="quick_spike_test",
        target=target,
        overrides={}
    )
    
    print("\n📋 Generated experiment configuration:")
    print(f"   Title: {experiment.get('title')}")
    print(f"   Description: {experiment.get('description')}")
    
    # Check the stages in the experiment
    method = experiment.get("method", [])
    if method:
        action = method[0]
        arguments = action.get("provider", {}).get("arguments", {})
        options = arguments.get("options", {})
        stages = options.get("stages", [])
        
        print(f"\n⚡ Quick spike test stages:")
        total_duration = 0
        for i, stage in enumerate(stages, 1):
            duration_str = stage.get("duration", "")
            target_users = stage.get("target", 0)
            print(f"   Stage {i}: {duration_str} at {target_users} users")
            
            # Convert to seconds for total calculation
            if "s" in duration_str:
                total_duration += int(duration_str.replace("s", ""))
            elif "m" in duration_str:
                total_duration += int(duration_str.replace("m", "")) * 60
        
        print(f"\n⏱️ Total test duration: {total_duration} seconds ({total_duration/60:.1f} minutes)")
        print("✅ Quick spike test template configured successfully!")
    else:
        print("❌ No method found in experiment")

if __name__ == "__main__":
    test_quick_spike()