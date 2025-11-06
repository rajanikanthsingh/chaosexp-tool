# Host-Down Chaos Strategy

## Overview

The **host-down** chaos type simulates a complete node failure by **draining** the Nomad node, which forces all allocations to migrate to other healthy nodes in the cluster.

## Strategy: Node Drain

### What is Node Drain?

Node drain is a **graceful shutdown** mechanism in Nomad that:
1. Marks the node as **ineligible** for new allocations
2. Signals all running allocations to stop
3. Waits for allocations to shut down gracefully (up to deadline)
4. Triggers Nomad scheduler to place allocations on other nodes

### Why Drain Instead of Hard Kill?

| Approach | Description | Use Case |
|----------|-------------|----------|
| **Node Drain** ✅ | Graceful migration | Simulates planned maintenance, node upgrade |
| **Hard Kill** ❌ | Immediate termination | Simulates hardware failure, power loss |

We use **Node Drain** because:
- ✅ More realistic for most failure scenarios
- ✅ Allows graceful shutdown (saves state, closes connections)
- ✅ Nomad handles rescheduling automatically
- ✅ Reversible (can re-enable node)
- ✅ Production-safe (when done correctly)

## Implementation Strategy

### Step-by-Step Process

```
┌─────────────────────────────────────────────────────┐
│ 1. DISCOVER TARGET NODE                             │
├─────────────────────────────────────────────────────┤
│ • Find which node hosts the target service          │
│ • Get node ID, name, datacenter                     │
│ • Count allocations on node                         │
│                                                     │
│ Input:  service_id = "mobi-platform-account-service"│
│ Output: node_id = "538b4367-c20d-..."               │
│         node_name = "hostname"    │
│         alloc_count = 8                             │
└─────────────────────────────────────────────────────┘
                     ⬇️
┌─────────────────────────────────────────────────────┐
│ 2. VALIDATE NODE STATE                              │
├─────────────────────────────────────────────────────┤
│ • Check if node is already draining                 │
│ • Verify node status is "ready"                     │
│ • Warn about number of affected allocations         │
│                                                     │
│ Checks:                                             │
│ ✓ Drain status = false                              │
│ ✓ Status = ready                                    │
│ ⚠️  ALL 8 allocations will be affected!             │
└─────────────────────────────────────────────────────┘
                     ⬇️
┌─────────────────────────────────────────────────────┐
│ 3. ENABLE DRAIN MODE                                │
├─────────────────────────────────────────────────────┤
│ • POST to /v1/node/{id}/drain                       │
│ • Set drain deadline (default: 120 seconds)         │
│ • Mark node as ineligible                           │
│                                                     │
│ API Call:                                           │
│ {                                                   │
│   "DrainSpec": {                                    │
│     "Deadline": 120000000000,  // 120s in ns        │
│     "IgnoreSystemJobs": false                       │
│   },                                                │
│   "MarkEligible": false                             │
│ }                                                   │
└─────────────────────────────────────────────────────┘
                     ⬇️
┌─────────────────────────────────────────────────────┐
│ 4. NOMAD AUTOMATIC MIGRATION                        │
├─────────────────────────────────────────────────────┤
│ Nomad Scheduler Takes Over:                         │
│ • Finds suitable nodes for each allocation          │
│ • Checks resource availability                      │
│ • Considers constraints and affinities              │
│ • Starts new allocations on target nodes            │
│ • Signals old allocations to stop                   │
│                                                     │
│ Timeline:                                           │
│ 0-10s:  New allocations placed                      │
│ 10-30s: New instances starting                      │
│ 30-60s: Health checks passing                       │
│ 60-90s: Old allocations stopping                    │
│ 90s+:   Migration complete                          │
└─────────────────────────────────────────────────────┘
                     ⬇️
┌─────────────────────────────────────────────────────┐
│ 5. VERIFY DRAIN STATUS                              │
├─────────────────────────────────────────────────────┤
│ • Wait 3 seconds for API to reflect changes         │
│ • Query node status                                 │
│ • Confirm drain is active                           │
│ • Check scheduling eligibility                      │
│                                                     │
│ Expected:                                           │
│ ✓ Drain = true                                      │
│ ✓ SchedulingEligibility = "ineligible"             │
│ ✓ Status = "ready" (still healthy)                 │
└─────────────────────────────────────────────────────┘
                     ⬇️
┌─────────────────────────────────────────────────────┐
│ 6. PROVIDE RECOVERY INSTRUCTIONS                    │
├─────────────────────────────────────────────────────┤
│ ⚠️  MANUAL INTERVENTION REQUIRED!                   │
│                                                     │
│ To re-enable node after testing:                    │
│ $ nomad node eligibility -enable {node_id}          │
│                                                     │
│ Or via API:                                         │
│ $ curl -X POST http://nomad:4646/v1/node/{id}/...  │
│    -d '{"Eligibility":"eligible"}'                  │
└─────────────────────────────────────────────────────┘
```

## Key Configuration Parameters

### 1. Drain Deadline

```python
duration_seconds = 120  # Default: 2 minutes
```

**What it means:**
- Maximum time for graceful shutdown
- After deadline, remaining allocations are **force-killed**
- Longer deadline = more time for graceful migration
- Shorter deadline = faster chaos but may cause abrupt termination

**Recommendations:**
```python
# Fast-starting services (stateless web apps)
duration_seconds = 60

# Database services with state
duration_seconds = 300

# Mission-critical with complex shutdown
duration_seconds = 600
```

### 2. IgnoreSystemJobs

```python
"IgnoreSystemJobs": False  # Drain ALL jobs including system jobs
```

**Options:**
- `False`: Drain everything (default) - most realistic
- `True`: Keep system jobs running - less disruptive

**System jobs include:**
- Log collectors
- Monitoring agents
- Security scanners
- Infrastructure services

### 3. MarkEligible

```python
"MarkEligible": False  # Node stays ineligible after drain
```

**What it means:**
- `False`: Node remains drained until manual re-enable ✅
- `True`: Node automatically becomes eligible after drain

**Why False?**
- Prevents automatic re-population
- Gives time to analyze impact
- Requires conscious recovery decision
- Simulates permanent node loss

## How Nomad Handles Migration

### Scheduler Logic

```
FOR each allocation on draining node:
  1. Find eligible nodes with capacity
  2. Calculate placement scores based on:
     - Available resources
     - Existing allocations (spread)
     - Constraints (datacenter, class)
     - Affinities (prefer certain nodes)
  3. Select best candidate node
  4. Create new allocation on target node
  5. Wait for new allocation to be healthy
  6. Signal old allocation to stop (SIGTERM)
  7. Wait for graceful shutdown (up to deadline)
  8. Force kill if deadline exceeded (SIGKILL)
```

### Example Migration Flow

```
Before Drain:
  msacc01p1: [Service-A, Service-B, Service-C]  ← Draining
  msacc02p1: [Service-D]
  msacc03p1: [Service-E]

During Drain:
  msacc01p1: [Service-A*, Service-B*, Service-C*]  ← Stopping
  msacc02p1: [Service-D, Service-A↓]               ← Starting
  msacc03p1: [Service-E, Service-B↓, Service-C↓]   ← Starting

After Drain:
  msacc01p1: []                                     ← Empty
  msacc02p1: [Service-D, Service-A]                 ← Running
  msacc03p1: [Service-E, Service-B, Service-C]      ← Running
```

## Strategy Advantages

### ✅ Pros

1. **Realistic**
   - Mimics real-world maintenance scenarios
   - Similar to node upgrades, decommissioning
   - Tests actual failure handling paths

2. **Controlled**
   - Graceful shutdown (saves state)
   - Predictable timeline
   - Reversible (can re-enable)

3. **Comprehensive**
   - Tests service redundancy
   - Validates cluster capacity
   - Exercises Nomad scheduler
   - Checks health checks and readiness

4. **Production-Safe**
   - No data corruption risk
   - Nomad handles complexity
   - Can be scheduled during maintenance windows

5. **Observable**
   - Can watch migration in real-time
   - Clear status indicators
   - Detailed API responses

### ⚠️ Cons

1. **Not Instant**
   - Takes 1-3 minutes for full migration
   - Doesn't simulate instant hardware failure

2. **Requires Capacity**
   - Cluster must have spare resources
   - May fail if no suitable nodes available

3. **Affects All Services**
   - Can't selectively drain one service
   - High blast radius

4. **Manual Recovery**
   - Requires explicit re-enable command
   - Easy to forget and leave node drained

5. **Permission Requirements**
   - Needs `node { policy = "write" }` ACL
   - Not available with basic tokens

## Alternative Strategies (Not Implemented)

### Strategy 2: Allocation Stop

```python
# Stop specific allocation instead of draining node
nomad.allocation.stop(allocation_id)
```

**Pros:**
- ✅ Surgical (affects only target service)
- ✅ Lower blast radius

**Cons:**
- ❌ Less realistic (nodes don't fail partially)
- ❌ Doesn't test cluster-wide impact

### Strategy 3: Node Eligibility Toggle

```python
# Mark node ineligible without draining
nomad.node.set_eligibility(node_id, eligible=False)
```

**Pros:**
- ✅ Prevents new allocations
- ✅ Keeps existing allocations running

**Cons:**
- ❌ Doesn't simulate failure (services keep running)
- ❌ Not a realistic failure mode

### Strategy 4: Job Stop

```python
# Stop the job entirely
nomad.job.deregister(job_id)
```

**Pros:**
- ✅ Simple and direct

**Cons:**
- ❌ Affects all instances, not just one node
- ❌ Too aggressive for chaos testing

## Monitoring the Strategy

### What to Watch

```bash
# Terminal 1: Monitor node status
watch -n 2 'nomad node status {node_id} | head -30'

# Terminal 2: Monitor allocations
watch -n 2 'nomad node status {node_id} | grep -A 20 Allocations'

# Terminal 3: Monitor job status
watch -n 2 'nomad job status {service_id}'

# Terminal 4: Monitor cluster capacity
watch -n 5 'chaosmonkey discover --clients'
```

### Key Metrics

| Metric | Normal | During Drain | What to Check |
|--------|--------|--------------|---------------|
| **Drain Status** | false | true | Node API |
| **Eligibility** | eligible | ineligible | Node API |
| **Allocation Count** | 8 | 8→6→4→2→0 | Node status |
| **Service Instances** | 1 | 1→2→1 | Job status |
| **Response Time** | 50ms | 100-500ms | APM/logs |
| **Error Rate** | 0.1% | 2-5% | Monitoring |

## Recovery Strategy

### Automatic Recovery (Not Implemented)

Ideally, we would:
```python
# Schedule a job to re-enable node after duration
def schedule_node_recovery(node_id, delay_seconds):
    time.sleep(delay_seconds)
    nomad.node.set_eligibility(node_id, eligible=True)
    nomad.node.drain_node(node_id, enable=False)
```

### Manual Recovery (Current Approach)

**Step 1: Check node is empty**
```bash
nomad node status {node_id} | grep "Allocations"
# Should show 0 allocations
```

**Step 2: Re-enable node**
```bash
# Disable drain
nomad node drain -disable {node_id}

# Make eligible again
nomad node eligibility -enable {node_id}
```

**Step 3: Verify recovery**
```bash
nomad node status {node_id}
# Should show:
# Drain: false
# Eligibility: eligible
# Status: ready
```

**Step 4: Monitor repopulation**
```bash
watch -n 5 'nomad node status {node_id}'
# Allocations should gradually return as scheduler rebalances
```

## Comparison with Other Strategies

| Strategy | Realism | Control | Blast Radius | Reversible | Complexity |
|----------|---------|---------|--------------|------------|------------|
| **Node Drain** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🔴 High | ✅ Yes | Medium |
| Allocation Stop | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🟡 Low | ✅ Yes | Low |
| Node Ineligible | ⭐⭐ | ⭐⭐⭐⭐⭐ | 🟢 None | ✅ Yes | Low |
| Job Stop | ⭐⭐ | ⭐⭐⭐ | 🔴 Very High | ✅ Yes | Low |
| Hard Kill | ⭐⭐⭐⭐⭐ | ⭐ | 🔴 High | ❌ No | High |

## Best Practices

### Before Running

1. ✅ **Verify cluster capacity**
   ```bash
   chaosmonkey discover --clients
   # Ensure other nodes can absorb workload
   ```

2. ✅ **Check service redundancy**
   ```bash
   nomad job status {service_id}
   # Ensure count > 1
   ```

3. ✅ **Coordinate with team**
   - Announce in chat
   - Get approval
   - Set up monitoring

### During Chaos

1. ✅ **Watch migration progress**
   ```bash
   watch -n 2 'nomad node status {node_id}'
   ```

2. ✅ **Monitor service health**
   - Check APM dashboard
   - Watch error rates
   - Monitor response times

3. ✅ **Document observations**
   - Note migration duration
   - Record any issues
   - Capture screenshots

### After Chaos

1. ✅ **Verify migration complete**
   ```bash
   nomad node status {node_id}
   # Should show 0 allocations
   ```

2. ✅ **Re-enable node**
   ```bash
   nomad node eligibility -enable {node_id}
   ```

3. ✅ **Validate service recovered**
   ```bash
   nomad job status {service_id}
   # All instances should be healthy
   ```

4. ✅ **Review and document**
   - Write incident report
   - Note lessons learned
   - Update runbooks

## Summary

The **Node Drain** strategy provides:
- 🎯 **Realistic** failure simulation
- 🔒 **Safe** and reversible process
- 📊 **Observable** migration process
- ⚙️ **Automated** by Nomad scheduler
- ⚠️ **High impact** for thorough testing

**Trade-off:** Requires elevated permissions and manual recovery, but provides the most comprehensive test of cluster resilience.

---

**Strategy Status**: ⚠️ Implemented but requires `node { policy = "write" }` ACL permissions

**Documentation**: See `docs/NODE_DRAIN.md` for complete usage guide
