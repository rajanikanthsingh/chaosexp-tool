#!/usr/bin/env python3
"""Test K6 load test with real resolved URLs"""

import sys
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.config import Settings
from chaosmonkey.core.experiments import ExperimentTemplateRegistry
from chaosmonkey.core.nomad import NomadClient

def test_k6_load_test():
    """Test a real K6 load test with properly resolved URLs"""
    print("🚀 Testing K6 load test with resolved URLs...")
    
    settings = Settings()
    client = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region,
        token=settings.nomad.token,
        namespace=settings.nomad.namespace,
    )
    
    template_manager = ExperimentTemplateRegistry()
    
    # Get a service with a real IP address
    targets = client.enumerate_targets()
    service_targets = [t for t in targets if t.kind == "service" and t.attributes.get("address") and t.attributes.get("address") != ""]
    
    if not service_targets:
        print("❌ No service targets with real IP addresses found")
        return
    
    # Use the first service with a real IP
    target = service_targets[0]
    print(f"🎯 Testing with target: {target.identifier}")
    print(f"   Address: {target.attributes.get('address')}")
    print(f"   Port: {target.attributes.get('port')}")
    
    # Build the URL using the template manager
    url = template_manager._build_target_url(target)
    print(f"   Generated URL: {url}")
    
    # Create a simple K6 test script
    k6_script = template_manager.get_k6_load_test_script([target], {
        'duration': '10s',
        'vus': 1,
        'rps': 1
    })
    
    print(f"\n📝 Generated K6 script preview (first 500 chars):")
    print(k6_script[:500] + "..." if len(k6_script) > 500 else k6_script)
    
    # Write the script to a temporary file and test it
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(k6_script)
        script_path = f.name
    
    try:
        print(f"\n🧪 Running K6 test with script: {script_path}")
        
        # Run k6 with the script
        import subprocess
        result = subprocess.run(
            ['k6', 'run', '--duration', '5s', '--vus', '1', script_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"📊 K6 exit code: {result.returncode}")
        
        if result.stdout:
            print("📈 K6 stdout:")
            # Show only the last 20 lines to avoid flooding
            stdout_lines = result.stdout.strip().split('\n')
            for line in stdout_lines[-20:]:
                print(f"  {line}")
        
        if result.stderr:
            print("⚠️ K6 stderr:")
            stderr_lines = result.stderr.strip().split('\n')  
            for line in stderr_lines[-10:]:
                print(f"  {line}")
                
        if result.returncode == 0:
            print("✅ K6 test completed successfully!")
        else:
            print(f"❌ K6 test failed with exit code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("⏰ K6 test timed out after 30 seconds")
    except Exception as e:
        print(f"💥 Error running K6 test: {e}")
    finally:
        # Clean up
        if os.path.exists(script_path):
            os.unlink(script_path)

if __name__ == "__main__":
    test_k6_load_test()