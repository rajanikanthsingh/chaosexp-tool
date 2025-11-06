#!/usr/bin/env python3
"""Test K6 runner directly"""

import sys
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.core.k6_runner import k6_runner

def test_k6_runner():
    """Test the K6 runner with the actual URL from the report"""
    target_url = "http://10.174.27.17:8098"
    
    print(f"🧪 Testing K6 runner with URL: {target_url}")
    print(f"📍 K6 binary available: {k6_runner.is_available()}")
    print(f"📍 K6 binary path: {k6_runner.k6_binary}")
    
    if not k6_runner.is_available():
        print("❌ K6 not available!")
        return
    
    # Simple stress test script
    script_text = f"""
export default function() {{
  let response = http.get('{target_url}');
  check(response, {{
    'status is success': (r) => r.status >= 200 && r.status < 500,
  }});
}}
"""
    
    options = {
        "duration": "5s",
        "vus": 2,
    }
    
    print("🚀 Running K6 stress test...")
    result = k6_runner.run_script(script_text, options)
    
    print(f"📊 Success: {result['success']}")
    print(f"📊 Return code: {result.get('returncode', 'N/A')}")
    
    if result.get('stdout'):
        print("\n📈 K6 stdout:")
        stdout_lines = result['stdout'].strip().split('\n')
        for line in stdout_lines[-10:]:  # Last 10 lines
            print(f"  {line}")
    
    if result.get('stderr'):
        print("\n⚠️ K6 stderr:")
        stderr_lines = result['stderr'].strip().split('\n')
        for line in stderr_lines[-5:]:  # Last 5 lines
            print(f"  {line}")
    
    if result.get('error'):
        print(f"\n💥 Error: {result['error']}")

if __name__ == "__main__":
    test_k6_runner()