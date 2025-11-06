#!/usr/bin/env python3
"""
Quick test script to verify Prometheus metrics collection for node targets.
"""

import json
from pathlib import Path
from src.chaosmonkey.config import load_settings
from src.chaosmonkey.core.prometheus_metrics import PrometheusMetricsCollector
from src.chaosmonkey.core.nomad import NomadClient

def test_prometheus_metrics():
    """Test Prometheus metrics collection."""
    print("=" * 80)
    print("TESTING PROMETHEUS METRICS COLLECTION")
    print("=" * 80)
    
    # Load configuration
    config_path = Path("config.yaml")
    settings = load_settings(config_path)
    
    # Initialize Prometheus collector
    print(f"\n1️⃣  Initializing Prometheus collector: {settings.prometheus.url}")
    collector = PrometheusMetricsCollector(
        prometheus_url=settings.prometheus.url,
        timeout=settings.prometheus.timeout,
    )
    print("   ✅ Prometheus collector initialized")
    
    # Get a test node from Nomad
    print("\n2️⃣  Getting test node from Nomad...")
    nomad = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region,
        token=settings.nomad.token,
        namespace=settings.nomad.namespace,
    )
    
    nodes = nomad.list_nodes()
    if not nodes:
        print("   ❌ No nodes found in Nomad")
        return False
    
    # Pick first ready node
    test_node = None
    for node in nodes[:10]:  # Check first 10 nodes
        if node.get("Status") == "ready":
            test_node = node
            break
    
    if not test_node:
        print("   ❌ No ready nodes found")
        return False
    
    node_name = test_node["Name"]
    node_id = test_node["ID"]
    short_name = node_name.split(".")[0] if "." in node_name else node_name
    
    print(f"   ✅ Using test node: {node_name}")
    print(f"      Node ID: {node_id}")
    print(f"      Short name: {short_name}")
    
    # Test metrics collection
    print(f"\n3️⃣  Collecting metrics from Prometheus for {short_name}...")
    metrics = collector.collect_node_metrics(node_name=short_name)
    
    if not metrics:
        print("   ❌ No metrics returned")
        return False
    
    print("   ✅ Metrics collected successfully!")
    
    # Verify metrics structure
    print("\n4️⃣  Verifying metrics structure...")
    expected_keys = ["cpu", "memory", "disk", "node_name", "timestamp"]
    for key in expected_keys:
        if key in metrics:
            print(f"   ✅ Has '{key}' field")
        else:
            print(f"   ❌ Missing '{key}' field")
            return False
    
    # Verify nested structure
    print("\n5️⃣  Verifying nested metric values...")
    cpu_percent = metrics.get("cpu", {}).get("percent")
    mem_usage = metrics.get("memory", {}).get("usage")
    disk_read = metrics.get("disk", {}).get("read_bytes")
    disk_write = metrics.get("disk", {}).get("write_bytes")
    
    print(f"   CPU: {cpu_percent:.2f}%" if cpu_percent else "   ❌ No CPU data")
    print(f"   Memory: {mem_usage / (1024**3):.2f} GB" if mem_usage else "   ❌ No memory data")
    print(f"   Disk Read: {disk_read} bytes/sec" if disk_read is not None else "   ❌ No disk read data")
    print(f"   Disk Write: {disk_write} bytes/sec" if disk_write is not None else "   ❌ No disk write data")
    
    if cpu_percent and mem_usage:
        print("\n   ✅ Metrics have real values!")
    else:
        print("\n   ⚠️  Some metrics are missing or zero")
    
    # Display full structure
    print("\n6️⃣  Full metrics structure:")
    print(json.dumps(metrics, indent=2))
    
    print("\n" + "=" * 80)
    print("✅ TEST PASSED - Prometheus metrics collection is working!")
    print("=" * 80)
    print("\n📝 Next steps:")
    print("   1. Run a chaos experiment from the Web UI on a node target")
    print("   2. Check the HTML report for graphs")
    print("   3. Verify metrics are collected before/during/after")
    
    return True

if __name__ == "__main__":
    import sys
    success = test_prometheus_metrics()
    sys.exit(0 if success else 1)
