# Memory Hog Chaos Experiment

## Overview

The **Memory Hog** chaos experiment creates memory pressure on Nomad client nodes by allocating and holding large amounts of memory. This tests how your services behave under memory contention, potential OOM (Out Of Memory) situations, and swap thrashing.

## How It Works

### Architecture

```
┌─────────────────────────────────────┐
│  Nomad Client Node                  │
│  (e.g., hostname) │
├─────────────────────────────────────┤
│                                     │
│  🎯 Your Service                    │
│     └─ Needs memory for operations  │
│     └─ May have memory limits       │
│                                     │
│  💣 Memory Stress Job (2 workers)   │
│     └─ Allocates 2GB RAM (default)  │
│     └─ Holds memory for duration    │
│     └─ Competes for available RAM   │
│                                     │
│  ⚡ Memory Pressure!                │
│     └─ Physical RAM exhaustion      │
│     └─ Swap file activation         │
│     └─ Potential OOM kills          │
│     └─ Severe performance degradation │
└─────────────────────────────────────┘
```

### What Happens

1. **Memory Allocation**: Stress workers allocate memory chunks
2. **Memory Hold**: Keep memory allocated for the duration
3. **Memory Pressure**: Node runs low on available RAM
4. **System Response**:
   - Swap file activation (if available)
   - Page cache eviction
   - OOM killer may activate
   - Services experience allocation failures

## Configuration

### Default Settings

```python
memory_mb = 2048        # 2GB memory allocation
memory_workers = 2      # 2 parallel workers (1GB each)
duration = 120          # 120 seconds
```

### Customization

Edit `src/chaosmonkey/core/experiments.py`:

```python
replacements = {
    "memory_mb": 4096,  # 4GB for more aggressive stress
}
```

Or in `src/chaosmonkey/stubs/actions.py`:

```python
# More aggressive configuration
memory_workers = 4
memory_per_worker = memory_mb_int // memory_workers
```

## Usage

### Basic Memory Stress

```bash
# Default 2GB memory stress for 120 seconds
chaosmonkey execute --chaos-type memory-hog --target-id <service-id>

# Example
chaosmonkey execute --chaos-type memory-hog --target-id mobi-platform-account-service-job
```

### List Memory Chaos Jobs

```bash
# See all chaos jobs
chaosmonkey chaos-jobs

# Filter for running jobs
chaosmonkey chaos-jobs --status running
```

### Expected Output

```
[discovery] Searching for service: mobi-platform-account-service-job
[discovery] Found 1 running allocation(s)
[discovery] Target node: hostname
[discovery] Datacenter: dev1
[strategy] Using 2 memory workers, 1024MB each
[strategy] Total memory allocation: 2048MB
[deploy] Submitting chaos job: chaos-mem-mobi-platform-account-service-job-xxx
[deploy] Target: mobi-platform-account-service-job on hostname
[deploy] Memory to allocate: 2048MB (2 workers)
[impact] Expected impact: Memory contention, potential OOM, swap usage
[success] ✓ Chaos job deployed successfully!
[verify] Job status: running
[impact] All services on this node will compete for 2048MB memory
```

## Expected Impact

### On Target Service

| Metric | Normal | During Memory Stress | Impact |
|--------|--------|---------------------|---------|
| **Available Memory** | 16GB | 14GB | 2GB consumed |
| **Memory Allocation** | Fast | Slow/Fails | Allocation delays |
| **Swap Usage** | 0MB | 100MB-2GB | Disk thrashing |
| **Response Time** | ~50ms | ~500-5000ms | 10-100x slower |
| **Error Rate** | <0.1% | 2-10% | OOM errors |

### System Symptoms

1. **Memory Exhaustion**
   - Available RAM drops significantly
   - Buffer/cache memory reclaimed
   - Free memory approaches zero

2. **Swap Activation** (if enabled)
   - Swap usage increases
   - Disk I/O spikes
   - Severe performance degradation

3. **OOM Killer** (if memory limit exceeded)
   - Kernel kills processes to free memory
   - Services may be terminated
   - Container restarts triggered

4. **Performance Degradation**
   - Slower memory allocations
   - Page faults increase
   - CPU time spent on memory management

## Verification

### 1. Check Node Memory Usage

```bash
# SSH to target node
ssh hostname

# Check memory usage
free -h

# Watch real-time memory
watch -n 1 free -h

# Expected output during stress:
#               total        used        free      shared  buff/cache   available
# Mem:           16Gi        14Gi       500Mi        10Mi        1.5Gi       2.0Gi
# Swap:         4.0Gi       2.0Gi       2.0Gi
```

### 2. Monitor with htop

```bash
# On the target node
htop

# Look for:
# - stress processes with high RES (resident memory)
# - Swap usage bar increasing
# - Available memory decreasing
```

### 3. Check Docker Memory Stats

```bash
# On the target node
docker stats

# You'll see the stress container using significant MEMORY
```

### 4. Nomad UI

1. Navigate to: `http://nomad-server:4646/ui`
2. Go to: Jobs → `chaos-mem-<service>-<timestamp>`
3. Check: Allocations → Resources → Memory graph
4. Should show: 2GB+ memory usage

### 5. Service Health Checks

Monitor your service for:

```bash
# Check if service is experiencing memory issues
# Look for:
- "Out of memory" errors in logs
- Memory allocation failures
- Slow garbage collection
- Increased swap usage
- OOM kills and restarts
```

### 6. System Logs

```bash
# Check for OOM killer activity
sudo dmesg | grep -i "out of memory"
sudo dmesg | grep -i "oom"

# Check kernel logs
sudo journalctl -k | grep -i oom
```

## Technical Details

### Memory Stress Job Specification

```json
{
  "Job": {
    "ID": "chaos-mem-<service>-<timestamp>",
    "Type": "batch",
    "TaskGroups": [{
      "Tasks": [{
        "Driver": "docker",
        "Config": {
          "image": "polinux/stress",
          "command": "stress",
          "args": [
            "--vm", "2",           // Number of memory workers
            "--vm-bytes", "1024M", // Memory per worker
            "--timeout", "120s"    // Duration
          ]
        },
        "Resources": {
          "CPU": 500,              // Minimal CPU
          "MemoryMB": 2304         // 2048 + 256 overhead
        }
      }]
    }]
  }
}
```

### How stress Tool Works

The `stress` command from `polinux/stress` image:

```bash
stress --vm 2 --vm-bytes 1024M --timeout 120s

# --vm N          : Spawn N workers spinning on malloc()/free()
# --vm-bytes B    : Allocate B bytes per worker (default 256MB)
# --timeout T     : Stop after T seconds
```

Each worker:
1. Allocates memory via `malloc()`
2. Writes data to allocated memory (ensures physical allocation)
3. Holds the memory for duration
4. Frees memory on timeout

## Safety Considerations

### Built-in Safety

✅ **Time-limited**: Auto-terminates after duration  
✅ **Resource-limited**: Has memory + CPU limits  
✅ **Node-constrained**: Only affects one node  
✅ **Batch job**: Won't restart automatically  
✅ **Predictable**: Same memory amount each time  

### Potential Risks

⚠️ **OOM Killer**: May kill important processes  
⚠️ **Service Disruption**: Services may crash  
⚠️ **Performance Impact**: Can affect all node services  
⚠️ **Swap Thrashing**: Can cause severe slowdown  

### Risk Mitigation

1. **Start Small**
   ```python
   memory_mb = 1024  # Start with 1GB
   duration = 30     # Short duration
   ```

2. **Know Node Capacity**
   ```bash
   # Check total memory before testing
   ssh <node> free -h
   ```

3. **Set Memory Limits** on your services
   ```hcl
   # In your Nomad job spec
   resources {
     memory = 4096
     memory_max = 6144  # Allow burst but with limit
   }
   ```

4. **Monitor Carefully**
   - Watch service metrics
   - Check for OOM events
   - Have rollback plan ready

5. **Off-Hours Testing**
   - Run during low-traffic periods
   - Have team on standby
   - Test in staging first

## Emergency Stop

If the memory stress causes issues:

### Method 1: Via CLI

```bash
# Stop the chaos job
nomad job stop chaos-mem-<service>-<timestamp>
```

### Method 2: Via API

```bash
# Get job ID from chaos-jobs command
chaosmonkey chaos-jobs

# Stop via curl
curl -X DELETE "http://nomad-server:4646/v1/job/<chaos-job-id>"
```

### Method 3: Via Nomad UI

1. Go to: `http://nomad-server:4646/ui`
2. Navigate to: Jobs
3. Find: `chaos-mem-*` job
4. Click: Stop button

### Method 4: Kill Container (Last Resort)

```bash
# On the node
docker ps | grep stress
docker kill <container-id>
```

## Comparison: Memory Hog vs CPU Hog

| Aspect | Memory Hog | CPU Hog |
|--------|------------|---------|
| **Resource** | Memory/RAM | CPU cycles |
| **Impact Type** | Allocation failures, OOM | Slowness, timeouts |
| **Severity** | High (can kill processes) | Medium (degrades perf) |
| **Recovery** | May need restart | Auto-recovers |
| **System Effect** | Swap, OOM killer | High load average |
| **Detection** | Memory metrics, OOM logs | CPU metrics, slow responses |

## Advanced Configurations

### More Aggressive Memory Stress

```python
# In actions.py
memory_mb_int = 8192  # 8GB
memory_workers = 4     # 4 workers x 2GB each
```

### Combined CPU + Memory Stress

```python
# In the stress job args
"args": [
    "--cpu", "4",           # Add CPU stress
    "--vm", "4",            # Memory stress
    "--vm-bytes", "2048M",  # 2GB per worker
    "--timeout", "120s"
]
```

### Memory + I/O Stress

```python
"args": [
    "--vm", "2",
    "--vm-bytes", "2048M",
    "--io", "2",            # Add I/O stress
    "--timeout", "120s"
]
```

## Troubleshooting

### Job Doesn't Start

**Symptom**: Job stays in "pending" state

**Causes**:
- Node doesn't have enough memory
- Memory request too high
- Other allocations using memory

**Solution**:
```bash
# Check node available memory
nomad node status <node-id>

# Reduce memory request
memory_mb = 1024  # Try 1GB instead
```

### No Visible Impact

**Symptom**: Service performance unchanged

**Possible Reasons**:
1. Node has too much RAM (128GB+ nodes)
2. Service not under load
3. Service has low memory usage
4. Swap space absorbing impact

**Solutions**:
- Increase `memory_mb` to 8GB or more
- Generate load on service during test
- Use smaller nodes for testing
- Disable swap to see true impact

### OOM Killer Triggers

**Symptom**: Services get killed during stress

**This is expected behavior!** It shows:
✅ Your chaos testing found a real issue  
✅ Node memory limits are being enforced  
✅ Need to adjust service memory limits  

**Actions**:
1. Increase service memory limits
2. Add memory reserves
3. Implement graceful degradation
4. Use smaller memory stress amounts

## Success Metrics

Memory hog testing is successful when you can answer:

✅ How does the service behave when memory is exhausted?  
✅ Does the service handle allocation failures gracefully?  
✅ Do memory alerts trigger appropriately?  
✅ Does the service recover after memory pressure?  
✅ Are memory limits properly configured?  
✅ Does the OOM killer target correct processes?  

## Next Steps

1. **Document memory baselines** before chaos
2. **Test with increasing memory stress** (1GB → 2GB → 4GB)
3. **Validate memory monitoring** and alerting
4. **Test memory limits** and reservations
5. **Verify graceful degradation** under memory pressure
6. **Improve memory efficiency** based on findings

---

**Remember**: Memory issues are often more severe than CPU issues. Test carefully! 🎯
