# ChaosMonkey Examples

This directory contains example scripts demonstrating various ChaosMonkey features.

## Available Examples

### 1. Metrics Collection Demo (`metrics_collection_demo.py`)

Demonstrates the metrics collection and comparison features:

- Collecting baseline metrics before chaos
- Continuous monitoring during chaos experiments
- Post-chaos metrics collection
- Metrics comparison and analysis
- Report generation

**Usage:**

```bash
# Make sure ChaosMonkey is installed
cd /Users/inderdeep.sidhu/PycharmProjects/chaosmonkey

# Run the demo
python examples/metrics_collection_demo.py
```

**Requirements:**
- Nomad cluster running with at least one allocation
- Python 3.11+
- ChaosMonkey dependencies installed

**What it demonstrates:**
- Single allocation metrics collection
- Job-level aggregated metrics
- Three-phase collection (before/during/after)
- Automatic recovery validation
- JSON report generation

## Running Examples

### Setup

Ensure you have ChaosMonkey installed and configured:

```bash
# Install dependencies
pip install -e .

# Configure Nomad connection (if needed)
export NOMAD_ADDR="http://localhost:4646"
export NOMAD_TOKEN="your-token-here"
```

### Run an Example

```bash
# From the project root
python examples/metrics_collection_demo.py
```

## Example Output

The metrics collection demo produces output like:

```
============================================================
CHAOS METRICS COLLECTION EXAMPLE
============================================================

🔧 Initializing clients...

============================================================
EXAMPLE 1: Allocation Metrics Collection
============================================================

🎯 Target: web-server.web[0] (47c8d0f2)

📊 Collecting BEFORE metrics...

============================================================
BEFORE METRICS
============================================================
Timestamp: 2024-01-15T10:00:00.123456
Target: 47c8d0f2

📊 CPU Metrics:
  Usage: 15.23%
  System Mode: 1234 ticks
  User Mode: 5678 ticks

💾 Memory Metrics:
  RSS: 512.00 MB
  Cache: 128.00 MB
  Usage: 640.00 MB
  Max Usage: 768.00 MB

⚡ Simulating chaos experiment (10 seconds)...

📊 Collecting DURING metrics (5 samples, 2s interval)...
   Collected 5 snapshots
   Snapshot 1: CPU = 15.45%
   Snapshot 2: CPU = 16.12%
   Snapshot 3: CPU = 15.89%
   Snapshot 4: CPU = 15.67%
   Snapshot 5: CPU = 15.34%

📊 Collecting AFTER metrics...

============================================================
AFTER METRICS
============================================================
...

📈 Generating comparison report...

============================================================
METRICS COMPARISON ANALYSIS
============================================================

📊 CPU Analysis:
  Before:       15.23%
  Peak During:  16.12%
  After:        15.34%
  Change:       +0.89%
  Recovery:     +0.11%
  Status:       ✅ RECOVERED (within 5%)

💾 Memory Analysis:
  Before:       512.00 MB
  Peak During:  520.00 MB
  After:        515.00 MB
  Change:       +8.00 MB
  Status:       ✅ RECOVERED (within 10%)

🚦 Status Analysis:
  Before:  running
  After:   running
  Status:  ✅ STABLE

💾 Full report saved to: metrics_comparison_example.json

============================================================
✅ Example completed successfully!
============================================================
```

## Creating Your Own Examples

Feel free to create additional examples following this structure:

1. Create a new Python file in this directory
2. Import necessary ChaosMonkey modules
3. Demonstrate a specific feature
4. Include helpful comments and output
5. Update this README with your example

## See Also

- [Metrics Collection Documentation](../docs/METRICS_COLLECTION.md)
- [Architecture Guide](../docs/ARCHITECTURE_AND_IMPLEMENTATION.md)
- [CLI Usage Guide](../README.md)
- [Web UI Guide](../docs/WEB_UI_GUIDE.md)
