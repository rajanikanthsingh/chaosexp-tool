#!/usr/bin/env python3
"""Simple K6 test with a real URL"""

import subprocess
import tempfile
import os

def simple_k6_test():
    """Run a simple K6 test with a real resolved URL"""
    # Use the URL we know works from our diagnostics
    test_url = "http://10.174.165.142:8080"
    
    k6_script = f"""
import http from 'k6/http';
import {{ check }} from 'k6';

export let options = {{
  duration: '5s',
  vus: 1,
}};

export default function() {{
  let response = http.get('{test_url}');
  check(response, {{
    'status is 200 or similar': (r) => r.status >= 200 && r.status < 400,
  }});
}}
"""
    
    print(f"🧪 Testing K6 with URL: {test_url}")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(k6_script)
        script_path = f.name
    
    try:
        result = subprocess.run(
            ['k6', 'run', script_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"📊 K6 exit code: {result.returncode}")
        
        if result.stdout:
            print("📈 K6 results:")
            # Show only the last 15 lines
            stdout_lines = result.stdout.strip().split('\n')
            for line in stdout_lines[-15:]:
                print(f"  {line}")
        
        if result.stderr and result.returncode != 0:
            print("⚠️ K6 stderr:")
            stderr_lines = result.stderr.strip().split('\n')  
            for line in stderr_lines[-5:]:
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
        if os.path.exists(script_path):
            os.unlink(script_path)

if __name__ == "__main__":
    simple_k6_test()