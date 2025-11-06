#!/usr/bin/env python3
"""
Test actual K6 experiment generation with health endpoint configuration using CLI
"""

import tempfile
import json
from pathlib import Path

def main():
    print("🧪 Testing actual K6 experiment file generation...")
    
    # Create a temporary experiment file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Use the chaosmonkey CLI to generate an experiment
        from subprocess import run, PIPE
        
        # Get available targets first
        result = run([
            'python', '-m', 'chaosmonkey.cli', 'targets', '--chaos-type', 'k6_load_test'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode != 0:
            print(f"❌ Failed to get targets: {result.stderr}")
            return
        
        # Find a target with a health endpoint
        lines = result.stdout.strip().split('\n')
        selected_target = None
        
        for line in lines:
            if 'system' in line and 'cadvisor' in line:
                # Extract target ID (first part before the pipe)
                target_id = line.split('|')[0].strip()
                selected_target = target_id
                break
        
        if not selected_target:
            print("❌ No suitable target found")
            return
        
        print(f"🎯 Using target: {selected_target}")
        
        # Generate experiment with the target
        result = run([
            'python', '-m', 'chaosmonkey.cli', 'experiment',
            '--target', selected_target,
            '--chaos-type', 'k6_load_test',
            '--output', temp_path,
            '--duration', '30s',
            '--virtual-users', '5'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode != 0:
            print(f"❌ Failed to generate experiment: {result.stderr}")
            return
        
        print("✅ Experiment generated successfully!")
        
        # Read and analyze the generated experiment
        with open(temp_path, 'r') as f:
            experiment_json = json.loads(f.read())
        
        print(f"\n📋 Generated experiment analysis:")
        print(f"   Title: {experiment_json.get('title', 'N/A')}")
        print(f"   Description: {experiment_json.get('description', 'N/A')}")
        
        # Check configuration
        config = experiment_json.get('configuration', {})
        print(f"\n🔧 Configuration:")
        print(f"   target_url: {config.get('target_url', 'N/A')}")
        print(f"   health_endpoint: {config.get('health_endpoint', 'N/A')}")
        
        # Check steady state probe URL
        steady_state = experiment_json.get('steady-state-hypothesis', {})
        probes = steady_state.get('probes', [])
        
        if probes:
            probe = probes[0]
            probe_url = probe.get('provider', {}).get('arguments', {}).get('url', 'N/A')
            print(f"\n🔍 Steady state probe:")
            print(f"   URL template: {probe_url}")
            
            # Check if it uses the template variables
            if '${target_url}' in probe_url and '${health_endpoint}' in probe_url:
                print("✅ Health endpoint template correctly configured!")
            else:
                print("❌ Health endpoint template not using variables")
        else:
            print("❌ No steady state probes found")
        
        # Check K6 method
        method = experiment_json.get('method', [])
        if method:
            k6_action = method[0]
            k6_args = k6_action.get('provider', {}).get('arguments', {})
            k6_target_url = k6_args.get('target_url', 'N/A')
            print(f"\n🚀 K6 load test:")
            print(f"   Target URL template: {k6_target_url}")
            
            if '${target_url}' in k6_target_url:
                print("✅ K6 target URL template correctly configured!")
            else:
                print("❌ K6 target URL not using template variable")
        else:
            print("❌ No K6 method found")
            
    finally:
        # Clean up
        Path(temp_path).unlink(missing_ok=True)

if __name__ == "__main__":
    main()