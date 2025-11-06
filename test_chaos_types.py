#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chaosmonkey.web.app import app
import json

def test_chaos_types():
    with app.test_client() as client:
        response = client.get('/api/chaos-types')
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.get_json()}")

if __name__ == "__main__":
    test_chaos_types()