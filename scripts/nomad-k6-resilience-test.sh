#!/bin/bash
# 
# Example: Comprehensive Nomad Service Resilience Testing with k6
#
# This script demonstrates a complete workflow for testing a Nomad service
# under various failure conditions while monitoring performance with k6.
#

set -e

SERVICE_NAME="${1:-my-web-service}"
NODE_ID="${2}"

echo "🚀 Starting comprehensive resilience testing for service: $SERVICE_NAME"

# Function to run k6 test and capture results
run_k6_test() {
    local test_type="$1"
    local test_name="$2"
    local extra_args="$3"
    
    echo "📊 Running $test_name..."
    chaosmonkey execute --chaos-type "$test_type" --target-id "$SERVICE_NAME" $extra_args --dry-run=false
    sleep 5  # Allow system to stabilize
}

# Function to introduce chaos and test
run_chaos_with_load() {
    local chaos_type="$1"
    local chaos_name="$2"
    local chaos_args="$3"
    
    echo "💥 Introducing $chaos_name while load testing..."
    
    # Start chaos in background
    chaosmonkey execute --chaos-type "$chaos_type" --target-id "$SERVICE_NAME" $chaos_args &
    CHAOS_PID=$!
    
    # Wait a moment for chaos to take effect
    sleep 10
    
    # Run load test during chaos
    run_k6_test "k6-api-test" "API Load Test During $chaos_name" "--virtual-users 20 --response-threshold 1500"
    
    # Wait for chaos to complete
    wait $CHAOS_PID || echo "⚠️  Chaos experiment completed"
    sleep 5
}

echo "🔍 Step 1: Discovering Nomad services..."
chaosmonkey discover

echo "🎯 Step 2: Listing available targets..."
chaosmonkey targets --chaos-type k6-load-test

echo "📈 Step 3: Baseline performance test..."
run_k6_test "k6-load-test" "Baseline Load Test" "--virtual-users 10 --duration 60"

echo "🔗 Step 4: API endpoint validation test..."
run_k6_test "k6-api-test" "API Validation Test" "--virtual-users 15 --duration 90"

echo "🗄️  Step 5: Database connectivity test..."
run_k6_test "k6-database-test" "Database Load Test" "--virtual-users 8 --duration 120"

echo "💥 Step 6: Testing resilience under various failure conditions..."

# Test under CPU pressure
run_chaos_with_load "cpu-hog" "CPU Pressure" "--duration 90"

# Test under memory pressure
run_chaos_with_load "memory-hog" "Memory Pressure" "--duration 90"

# Test under network latency
run_chaos_with_load "network-latency" "Network Latency" "--duration 90 --latency-ms 300"

# Test under packet loss
run_chaos_with_load "packet-loss" "Packet Loss" "--duration 90"

# Node drain test (if node ID provided)
if [ -n "$NODE_ID" ]; then
    echo "🏥 Step 7: Testing node failure recovery..."
    
    echo "   7a: Draining node $NODE_ID..."
    chaosmonkey drain-nodes --node-id "$NODE_ID" --yes
    
    echo "   7b: Testing performance with reduced capacity..."
    run_k6_test "k6-spike-test" "Performance During Node Drain" "--virtual-users 25 --response-threshold 2000"
    
    echo "   7c: Recovering node..."
    chaosmonkey recover-nodes --node-id "$NODE_ID" --yes
    
    echo "   7d: Verifying recovery..."
    sleep 30  # Allow time for service redistribution
    run_k6_test "k6-load-test" "Post-Recovery Verification" "--virtual-users 15"
fi

echo "⚡ Step 8: Final spike test..."
run_k6_test "k6-spike-test" "Final Spike Test" "--virtual-users 50 --response-threshold 1000"

echo "📊 Step 9: Generating final report..."
chaosmonkey report

echo "✅ Comprehensive resilience testing completed!"
echo "📁 Check the reports/ directory for detailed results"
echo "🌐 Open the web UI at http://localhost:8080 to view results"

# Optional: Start web UI
read -p "🚀 Start web UI to view results? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting web UI..."
    python run_web_ui.py
fi