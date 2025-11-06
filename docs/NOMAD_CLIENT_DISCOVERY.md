# Nomad Client Discovery Feature

## Overview

The `chaosmonkey discover --clients` command provides comprehensive visibility into all Nomad client nodes in your cluster. This is essential for chaos engineering as it helps you identify target nodes, understand capacity, and plan chaos experiments.

## Usage

### Basic Discovery

```bash
# List all Nomad client nodes
chaosmonkey discover --clients
```

### Output

The command displays a detailed table with the following information for each client node:

| Column | Description | Example |
|--------|-------------|---------|
| **Name** | Fully qualified node name | hostname |
| **ID** | Node UUID (truncated) | 538b4367... |
| **Status** | Node operational status | ready, down, initializing |
| **Datacenter** | Datacenter location | dev1, prod1 |
| **Node Class** | Node classification | compute, storage, - |
| **CPU** | Total CPU capacity | 4,000 MHz, 8,000 MHz |
| **Memory** | Total memory capacity | 7.5 GB, 15.4 GB, 23.9 GB |
| **Drain** | Draining status | Yes (red), No (green) |
| **Allocations** | Running allocation count | 1, 3, 8 |

### Example Output

```
                                                 Nomad Client Nodes                                                 
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name                       ┃ ID          ┃ Status ┃ Datacenter ┃ Node Class ┃      CPU ┃  Memory ┃ Drain ┃ Allocations ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━┩
│ hostname │ 538b4367... │ ready  │ dev1       │ -          │  8,000   │ 15.4 GB │ No    │           8 │
│                            │             │        │            │            │      MHz │         │       │             │
│ hostname│ 13f8663e... │ ready  │ dev1       │ -          │  4,000   │ 23.9 GB │ No    │           3 │
│                            │             │        │            │            │      MHz │         │       │             │
│ hostname│ 994324d2... │ ready  │ dev1       │ -          │  4,000   │ 11.5 GB │ No    │           6 │
│                            │             │        │            │            │      MHz │         │       │             │
└────────────────────────────┴─────────────┴────────┴────────────┴────────────┴──────────┴─────────┴───────┴─────────────┘

Total: 34 client node(s)
Ready: 34 | Drained: 0
```

## Features

### 1. Status Color Coding

- **🟢 Green**: `ready` - Node is healthy and accepting workloads
- **🔴 Red**: `down` - Node is offline or unavailable
- **🟡 Yellow**: Other states (initializing, disconnected)

### 2. Drain Status

- **🟢 No**: Node accepting new allocations
- **🔴 Yes**: Node is draining (preventing new allocations)

### 3. Resource Information

Shows **total available resources** on each node:
- **CPU**: Measured in MHz (e.g., 4,000 MHz = 4 cores @ 1GHz)
- **Memory**: Displayed in GB for readability

### 4. Running Allocations

Count of currently running allocations on each node. Higher numbers indicate:
- Busier nodes
- Potential targets for resource contention chaos
- Good nodes to avoid during testing

### 5. Summary Statistics

At the bottom of the output:
```
Total: 34 client node(s)
Ready: 34 | Drained: 0
```

## Use Cases

### 1. Planning Chaos Experiments

Identify nodes with your target services:

```bash
# Find all nodes
chaosmonkey discover --clients

# Find services on specific node
chaosmonkey targets | grep msacc01p1
```

### 2. Capacity Planning

```bash
# Review cluster capacity
chaosmonkey discover --clients

# Calculate total resources:
# - Sum CPU columns
# - Sum Memory columns
# - Compare with running allocations
```

### 3. Health Monitoring

```bash
# Check for downed nodes
chaosmonkey discover --clients | grep "down"

# Check for draining nodes
chaosmonkey discover --clients | grep "Yes"

# Identify underutilized nodes (low allocation count)
chaosmonkey discover --clients | grep "0\|1\|2"
```

### 4. Targeted Chaos Testing

```bash
# Step 1: Find nodes with many allocations
chaosmonkey discover --clients

# Step 2: Target high-load nodes for chaos
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id <service-on-busy-node>
```

### 5. Pre-Chaos Validation

Before running chaos experiments:

```bash
# Verify cluster health
chaosmonkey discover --clients

# Ensure:
# - All nodes show "ready"
# - No nodes are draining
# - Resources are balanced
```

## Comparison with Standard Discover

### Standard Discovery (Services)
```bash
chaosmonkey discover
```
**Output**: JSON with service information
**Use**: Understand what services are running

### Client Discovery (Nodes)
```bash
chaosmonkey discover --clients
```
**Output**: Table with node information
**Use**: Understand cluster infrastructure

## Integration with Chaos Commands

### Finding Target Nodes

```bash
# 1. List all client nodes
chaosmonkey discover --clients

# 2. Identify node with your service
# Look for node: hostname

# 3. Run chaos experiment
chaosmonkey execute \
  --chaos-type network-latency \
  --target-id mobi-platform-account-service-job
  
# The chaos will automatically target the correct node!
```

### Monitoring During Chaos

```bash
# Terminal 1: Run chaos
chaosmonkey execute --chaos-type cpu-hog --target-id my-service

# Terminal 2: Monitor nodes
watch -n 5 'chaosmonkey discover --clients'

# Watch allocation counts change as chaos jobs deploy
```

## Advanced Usage

### Filtering with grep

```bash
# Find specific node
chaosmonkey discover --clients | grep msacc01p1

# Find nodes with high allocation count
chaosmonkey discover --clients | grep -E "\s+([89]|[1-9][0-9])\s*$"

# Find nodes in specific datacenter
chaosmonkey discover --clients | grep "prod1"
```

### JSON Output (Future Enhancement)

```bash
# Not yet implemented, but planned:
chaosmonkey discover --clients --format json
```

Would output:
```json
{
  "nodes": [
    {
      "name": "hostname",
      "id": "538b4367-c20d-cdc7-2a73-6e59e245d5dc",
      "status": "ready",
      "datacenter": "dev1",
      "resources": {
        "cpu_mhz": 8000,
        "memory_mb": 15744
      },
      "allocations": 8
    }
  ]
}
```

## Troubleshooting

### No Nodes Displayed

**Symptom**: Table is empty

**Possible Causes**:
1. Nomad cluster has no client nodes
2. Connection issues
3. Wrong namespace

**Solution**:
```bash
# Check Nomad connection
curl http://nomad-server:4646/v1/nodes

# Verify namespace
export NOMAD_NAMESPACE=default
chaosmonkey discover --clients
```

### Missing Resource Information

**Symptom**: CPU/Memory show "-"

**Causes**:
1. Node API returned incomplete data
2. Node is initializing
3. Nomad version compatibility

**Note**: This is usually harmless and indicates the node hasn't fully registered its resources yet.

### Slow Response

**Symptom**: Command takes 10+ seconds

**Reason**: Makes API calls for each node to get detailed info

**Solution**: This is normal for large clusters. Be patient!

```bash
# For 34 nodes: ~5-10 seconds
# For 100 nodes: ~30-60 seconds
```

## Implementation Details

### API Calls Made

1. `GET /v1/nodes` - List all nodes
2. `GET /v1/node/{id}` - Get node details (per node)
3. `GET /v1/node/{id}/allocations` - Get allocations (per node)

### Resource Detection

The command intelligently handles different Nomad API versions:

```python
# Try Resources field (older API)
cpu = node.get("Resources", {}).get("CPU", 0)
memory = node.get("Resources", {}).get("MemoryMB", 0)

# Fallback to NodeResources (newer API)
if not cpu:
    cpu = node.get("NodeResources", {}).get("Cpu", {}).get("CpuShares", 0)
if not memory:
    memory = node.get("NodeResources", {}).get("Memory", {}).get("MemoryMB", 0)
```

## Best Practices

1. **Run before chaos experiments** to understand cluster state
2. **Monitor allocation counts** to avoid overloading nodes
3. **Check drain status** to avoid nodes being decommissioned
4. **Use in automation** for pre-flight checks
5. **Document node characteristics** for reproducible tests

## Example Workflow

```bash
#!/bin/bash
# Complete chaos testing workflow

echo "=== 1. Check Cluster Health ==="
chaosmonkey discover --clients

echo ""
echo "=== 2. Identify Target Services ==="
chaosmonkey targets

echo ""
echo "=== 3. Run Chaos Experiment ==="
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id mobi-platform-account-service-job

echo ""
echo "=== 4. Monitor Active Chaos ==="
chaosmonkey chaos-jobs

echo ""
echo "=== 5. Verify Node Status ==="
chaosmonkey discover --clients
```

## Future Enhancements

Planned features:

- [ ] JSON output format
- [ ] Filter by datacenter
- [ ] Filter by status (ready, down)
- [ ] Sort by resources or allocation count
- [ ] Show resource utilization percentage
- [ ] Export to CSV
- [ ] Historical tracking
- [ ] Resource alerts (over 80% utilized)

---

**Command Reference**:
```bash
chaosmonkey discover --clients       # List all Nomad client nodes
chaosmonkey discover --clients -h    # Show help
```

**See Also**:
- `chaosmonkey targets` - List chaos targets (services)
- `chaosmonkey chaos-jobs` - List active chaos experiments
- `chaosmonkey execute` - Run chaos experiments
