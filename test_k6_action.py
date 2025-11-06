#!/usr/bin/env python3
"""Test K6 action with the fixed script generation"""

import sys
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.stubs.actions import run_k6_script

def test_k6_action():
    """Test the K6 action with stress test script"""
    
    # This is the same script from the template that was causing issues
    script_text = """import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '5s', target: 2 },
    { duration: '10s', target: 5 },
    { duration: '5s', target: 0 },
  ],
};

export default function() {
  let response = http.get('http://10.174.27.17:8098');
  check(response, {
    'status is not 5xx': (r) => r.status < 500,
  });
}"""
    
    options = {
        "thresholds": {
            "http_req_failed": ["rate<0.5"],
            "http_req_duration": ["p(95)<2000"]
        }
    }
    
    print("🧪 Testing K6 action with stress test script...")
    print("📊 Script has inline options: Yes")
    print("📊 Additional options provided: Yes")
    
    result = run_k6_script(
        script_text=script_text,
        target_url="http://10.174.27.17:8098",
        options=options,
        ramp_up_users=2,
        max_users=5,
        stress_response_threshold=2000
    )
    
    print(f"\n📊 Success: {result['success']}")
    print(f"📊 Status: {result.get('status', 'unknown')}")
    
    if result.get('k6_output'):
        print("\n📈 K6 output (last 10 lines):")
        output_lines = result['k6_output'].strip().split('\n')
        for line in output_lines[-10:]:
            if line.strip():
                print(f"  {line}")
    
    if result.get('error'):
        print(f"\n❌ Error: {result['error']}")

if __name__ == "__main__":
    test_k6_action()