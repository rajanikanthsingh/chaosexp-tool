# Metrics Source Comparison - Testing Guide

**Created:** 2024  
**Purpose:** Test three different metrics sources to determine which one actually works in your environment

## Overview

We've created three test scripts to validate which metrics source provides **real-time resource usage data** for chaos experiment monitoring:

1. **Nomad API** - `test_nomad_metrics_api.py`
2. **Prometheus** - `test_prometheus_metrics_api.py`
3. **Oracle OLVM/OVIRT** - `test_ovirt_metrics_api.py`

## Current Problem

- Chaos experiments run successfully ✅
- Metrics collection is working ✅
- BUT: All metrics show **zero values** ❌

**Root Cause:** We're using Nomad server API which only provides **static capacity** (total CPU MHz, total Memory MB), not **real-time usage** (current CPU %, memory bytes consumed).

## What We Need

For proper chaos monitoring, we need:
- **CPU usage** in % (current utilization)
- **Memory consumption** in bytes (current usage)
- **Disk I/O** read/write bytes and operations
- **Time-series data** to plot before/during/after graphs

## Test Scripts

### 1. Nomad API Test

**File:** `tests/test_nomad_metrics_api.py`

**What it tests:**
- ✅ Node info endpoint (static data)
- ✅ Allocation list endpoint
- ✅ Allocation stats endpoint (real-time)
- ✅ Client API endpoint (real-time)
- ✅ Metrics endpoint (Prometheus format)

**How to run:**
```bash
cd /Users/inderdeep.sidhu/PycharmProjects/chaosmonkey

# Run with default Nomad (from config)
python tests/test_nomad_metrics_api.py

# Or specify Nomad URL
NOMAD_ADDR=http://your-nomad:4646 python tests/test_nomad_metrics_api.py
```

**Expected outcome:**
- ✅ Will determine if Nomad provides real-time metrics
- ✅ Will show which API endpoints work
- ⚠️ May fail if client API not accessible

---

### 2. Prometheus Test

**File:** `tests/test_prometheus_metrics_api.py`

**What it tests:**
- ✅ Prometheus connectivity
- ✅ node_exporter metrics availability
- ✅ CPU, memory, disk I/O metrics
- ✅ Time-series query capability
- ✅ Nomad-specific metrics (if configured)

**How to run:**
```bash
cd /Users/inderdeep.sidhu/PycharmProjects/chaosmonkey

# Run with default Prometheus
python tests/test_prometheus_metrics_api.py

# Or specify Prometheus URL
PROMETHEUS_URL=http://your-prometheus:9090 python tests/test_prometheus_metrics_api.py
```

**Expected outcome:**
- ✅ Will show if Prometheus is accessible
- ✅ Will list all available metrics
- ✅ Will show sample real-time data
- ⚠️ Requires node_exporter on monitored nodes

---

### 3. OVIRT/OLVM Test

**File:** `tests/test_ovirt_metrics_api.py`

**What it tests:**
- ✅ OVIRT API connectivity
- ✅ VM list and status
- ✅ VM statistics (real-time metrics)
- ✅ Nomad node to VM mapping
- ✅ Available metric types

**How to run:**
```bash
cd /Users/inderdeep.sidhu/PycharmProjects/chaosmonkey

# Set credentials
export OVIRT_URL="https://your-ovirt-engine.example.com"
export OVIRT_USERNAME="admin@internal"
export OVIRT_PASSWORD="your_password"

# Run test
python tests/test_ovirt_metrics_api.py
```

**Expected outcome:**
- ✅ Will show if OVIRT API is accessible
- ✅ Will list VMs and their metrics
- ✅ Will show CPU, memory, disk I/O stats
- ⚠️ Requires VM-level access (not allocation-level)

---

## Comparison Matrix

| Feature | Nomad | Prometheus | OVIRT |
|---------|-------|------------|-------|
| **Real-time CPU %** | ⚠️ Maybe (client API) | ✅ Yes | ✅ Yes (VM-level) |
| **Real-time Memory** | ⚠️ Maybe (client API) | ✅ Yes | ✅ Yes (VM-level) |
| **Disk I/O** | ⚠️ Maybe | ✅ Yes | ✅ Yes |
| **Time-series data** | ❌ No | ✅ Yes | ⚠️ Limited |
| **Granularity** | Allocation-level | Node-level | VM-level |
| **Already deployed** | ✅ Yes | ❓ Unknown | ✅ Yes (via Dora) |
| **API accessibility** | ✅ Easy | ✅ Easy | ⚠️ Needs mapping |
| **Historical data** | ❌ No | ✅ Yes | ⚠️ Via DWH |

## Running All Tests

```bash
cd /Users/inderdeep.sidhu/PycharmProjects/chaosmonkey

# Test 1: Nomad
echo "========== TESTING NOMAD API =========="
python tests/test_nomad_metrics_api.py > test_results_nomad.txt 2>&1
cat test_results_nomad.txt

# Test 2: Prometheus
echo ""
echo "========== TESTING PROMETHEUS API =========="
PROMETHEUS_URL=http://your-prometheus:9090 python tests/test_prometheus_metrics_api.py > test_results_prometheus.txt 2>&1
cat test_results_prometheus.txt

# Test 3: OVIRT
echo ""
echo "========== TESTING OVIRT API =========="
export OVIRT_URL="https://your-ovirt-engine.example.com"
export OVIRT_USERNAME="admin@internal"
export OVIRT_PASSWORD="your_password"
python tests/test_ovirt_metrics_api.py > test_results_ovirt.txt 2>&1
cat test_results_ovirt.txt

# Summary
echo ""
echo "=========================================="
echo "All tests complete! Review results above."
echo "=========================================="
```

## What to Look For

### ✅ **GOOD SIGNS:**
- Connection successful
- Metrics endpoints return data
- Real values (not zeros) for CPU, memory, disk
- Time-series queries work

### ❌ **BAD SIGNS:**
- Connection refused
- Authentication failures
- All metrics return zero
- Endpoints not found (404)

### ⚠️ **WARNINGS:**
- Limited metrics available
- Only static data (capacity, not usage)
- Requires additional setup
- Mapping complexity

## Decision Criteria

After running all three tests, choose based on:

1. **Which one actually works?**
   - Returns real, non-zero data
   - Accessible from ChaosMonkey host
   - Authentication succeeds

2. **Which provides the best data?**
   - Real-time CPU % (not just MHz)
   - Real-time memory usage (not just capacity)
   - Disk I/O rates
   - Time-series for before/during/after

3. **Which is easiest to integrate?**
   - Already deployed
   - Simple API calls
   - No complex mapping required
   - Good documentation

## Next Steps

### After Testing:

1. **Review test output** from all three scripts
2. **Compare results** using the criteria above
3. **Choose the best source** (or combination)
4. **Report findings** with:
   - Which sources work ✅
   - Which sources don't work ❌
   - Sample data showing real values
   - Any issues encountered

5. **Get approval** before modifying main code
6. **Implement chosen solution**

## Expected Recommendations

Based on typical deployments:

### Most Likely: **Prometheus** ✅
- If node_exporter is deployed
- Best for time-series data
- Industry standard
- Easy integration

### Alternative: **Nomad Client API** ⚠️
- If client nodes are accessible
- Allocation-level granularity
- Direct from source
- May have network restrictions

### Fallback: **OVIRT** ⚠️
- If nodes run on OVIRT VMs
- VM-level accurate
- Hypervisor perspective
- Requires VM mapping

## Support

If you encounter issues:

1. **Check environment variables:**
   ```bash
   echo "Nomad: $NOMAD_ADDR"
   echo "Prometheus: $PROMETHEUS_URL"
   echo "OVIRT: $OVIRT_URL"
   ```

2. **Test connectivity manually:**
   ```bash
   curl http://your-nomad:4646/v1/status/leader
   curl http://your-prometheus:9090/api/v1/query?query=up
   curl -k https://your-ovirt/ovirt-engine/api
   ```

3. **Check network access:**
   - Firewall rules
   - VPN requirements
   - SSL certificates

4. **Review error messages** in test output

## Summary

These three test scripts will definitively show:
- ✅ Which metrics sources work in your environment
- ✅ What real data each source provides
- ✅ Which is best for chaos monitoring

**No main code changes** until you approve the chosen solution! 🎯
