#!/usr/bin/env python3
"""Test K6 integration"""

import sys
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.core.k6_runner import is_k6_available, run_k6_script

def test_k6():
    print("🔍 Testing K6 integration...")
    
    # Check if K6 is available
    print(f"K6 available: {is_k6_available()}")
    
    if is_k6_available():
        # Test simple K6 script
        simple_script = """
        export default function() {
            console.log("Hello from K6!");
        }
        """
        
        print("🚀 Running simple K6 test...")
        result = run_k6_script(simple_script, {"vus": 1, "duration": "1s"})
        
        print(f"Success: {result['success']}")
        if result['success']:
            print("✅ K6 is working!")
        else:
            print(f"❌ K6 failed: {result.get('error', 'Unknown error')}")
            print(f"STDERR: {result.get('stderr', 'None')}")
    else:
        print("❌ K6 not available")

if __name__ == "__main__":
    test_k6()