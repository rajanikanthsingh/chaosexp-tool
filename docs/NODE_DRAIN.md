# Node Drain (Host Down) Chaos Experiment

## Overview

The **Host Down** (node drain) chaos experiment simulates a node failure by draining all allocations from a Nomad client node. This tests how your services handle node failures, service migrations, and cluster resilience.

## ⚠️ IMPORTANT: Permissions Required

Node drain operations require **elevated Nomad ACL permissions**. The standard token may not have sufficient privileges.

### Required ACL Policy

```hcl
# nomad-chaos-policy.hcl
node {
  policy = "write"  # Required for drain operations
}

namespace "default" {
  policy = "write"
}
```

### Permission Error

If you see `403: Permission denied`, your token doesn't have node write permissions:

```
[error] Failed to drain node: Drain API returned 403: Permission denied
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Before Drain: Node is Ready                            │
├─────────────────────────────────────────────────────────┤
│  Node: hostname                       │
│                                                         │
│  🟢 Status: ready                                       │
│  🟢 SchedulingEligibility: eligible                    │
│                                                         │
│  📦 Running Allocations: 8                              │
│     ├─ mobi-platform-account-service-job                │
│     ├─ other-service-1                                  │
│     ├─ other-service-2                                  │
│     └─ ... (5 more)                                     │
└─────────────────────────────────────────────────────────┘

          ⬇️  DRAIN ENABLED  ⬇️

┌─────────────────────────────────────────────────────────┐
│  During Drain: Node Migrating Workloads                 │
├─────────────────────────────────────────────────────────┤
│  Node: hostname                       │
│                                                         │
│  🟡 Status: ready                                       │
│  🔴 Drain: true                                         │
│  🔴 SchedulingEligibility: ineligible                  │
│                                                         │
│  📦 Migrating Allocations: 8 → 0                        │
│     ├─ mobi-platform-account-service → msacc02p1 ✓     │
│     ├─ other-service-1 → msath01p1 ✓                   │
│     └─ ... migrating to other nodes                    │
└─────────────────────────────────────────────────────────┘

          ⬇️  DRAIN COMPLETE  ⬇️

┌─────────────────────────────────────────────────────────┐
│  After Drain: Node Empty                                │
├─────────────────────────────────────────────────────────┤
│  Node: hostname                       │
│                                                         │
│  🟢 Status: ready                                       │
│  🔴 Drain: true (still active)                         │
│  🔴 SchedulingEligibility: ineligible                  │
│                                                         │
│  📦 Running Allocations: 0                              │
│     └─ All services migrated successfully               │
│                                                         │
│  ⚠️  Manual re-enable required to restore node          │
└─────────────────────────────────────────────────────────┘
```

## What Happens

### 1. Node Discovery
```
[discovery] Searching for service: mobi-platform-account-service-job
[discovery] Found 1 running allocation(s)
[discovery] Target node: hostname
[discovery] Allocations on node: 8
```

### 2. Drain Warning
```
⚠️  This will affect ALL 8 allocation(s) on this node!
[strategy] Current node status: ready
[strategy] Action: Enable node drain for 120 seconds
[impact] Expected impact: ALL services will be rescheduled to other nodes
```

### 3. Drain Execution
- Node marked as `ineligible` for new allocations
- Existing allocations begin graceful shutdown
- Nomad reschedules allocations to other nodes
- Services experience brief downtime during migration

### 4. Post-Drain State
- Node remains drained until manually re-enabled
- All allocations have migrated
- Node is healthy but not accepting workloads

## Configuration

### Default Settings

```python
duration_seconds = 120    # Drain deadline (2 minutes)
ignore_system_jobs = False  # Drain system jobs too
```

### Drain Deadline

The `duration_seconds` parameter sets the **maximum time** allowed for graceful migration:
- Allocations are given this time to stop gracefully
- After deadline, remaining allocations are force-killed
- Typically 120-300 seconds is reasonable

## Usage

### Basic Node Drain

```bash
# Drain node hosting target service
chaosmonkey execute \
  --chaos-type host-down \
  --target-id mobi-platform-account-service-job
```

### Expected Output

```
[discovery] Target node: hostname
[discovery] Allocations on node: 8
⚠️  This will affect ALL 8 allocation(s) on this node!
[strategy] Action: Enable node drain for 120 seconds
[action] Enabling drain mode on hostname...
[success] ✓ Node drain enabled successfully!
[impact] Allocations will begin migrating immediately
[impact] Service mobi-platform-account-service-job will be rescheduled
[verify] Drain active: True
[verify] Scheduling eligibility: ineligible
```

### Recovery Command

After testing, you **MUST manually re-enable** the node:

```bash
# Method 1: Using Nomad CLI
nomad node eligibility -enable <node-id>

# Method 2: Using HTTP API
curl -X POST \
  http://nomad-server:4646/v1/node/<node-id>/eligibility \
  -d '{"Eligibility":"eligible"}' \
  -H "X-Nomad-Token: $NOMAD_TOKEN"

# Method 3: Disable drain and mark eligible
nomad node drain -disable -enable <node-id>
```

## Expected Impact

### On Target Service

| Phase | Status | Duration | Impact |
|-------|--------|----------|--------|
| **Pre-Drain** | Running | - | Normal operation |
| **Drain Start** | Stopping | 0-10s | Service begins shutdown |
| **Migration** | Pending | 10-60s | Brief downtime |
| **Rescheduled** | Starting | 60-90s | New instance starting |
| **Post-Migration** | Running | 90s+ | Running on new node |

### On Other Services

**ALL services on the node** are affected:
- Every allocation must migrate
- Causes cluster-wide rescheduling
- May impact multiple teams/services
- High risk - use with caution!

### System Impact

```
Before Drain:
  msacc01p1: 8 allocations (busy)
  msacc02p1: 5 allocations
  msacc03p1: 4 allocations

During/After Drain:
  msacc01p1: 0 allocations (drained)
  msacc02p1: 9 allocations ⬆️
  msacc03p1: 8 allocations ⬆️
```

## Verification

### 1. Check Node Status

```bash
# Via CLI
nomad node status <node-id>

# Look for:
# Drain: true
# Eligibility: ineligible
```

### 2. Watch Allocations Migrate

```bash
# Real-time monitoring
watch -n 2 'nomad node status <node-id> | grep -A 20 "Allocations"'

# Should see allocation count decrease: 8 → 6 → 4 → 2 → 0
```

### 3. Verify Service Relocated

```bash
# Find new allocation
nomad job status mobi-platform-account-service-job

# Check which node it's running on now
# Should be different from original node
```

### 4. Check Cluster Capacity

```bash
# See which nodes received the migrated allocations
chaosmonkey discover --clients

# Look for increased allocation counts on other nodes
```

### 5. Nomad UI

1. Go to: `http://nomad-server:4646/ui/clients`
2. Find the drained node
3. Should show:
   - Status: Draining or Complete
   - Eligibility: Ineligible
   - Allocations: 0 or decreasing

## Safety Considerations

### ⚠️ HIGH RISK CHAOS

This is one of the **most disruptive** chaos types:

- ❌ Affects ALL services on the node
- ❌ Causes multiple service migrations
- ❌ May impact other teams
- ❌ Requires manual recovery
- ❌ Can exhaust cluster capacity

### Prerequisites

Before running node drain chaos:

1. ✅ **Sufficient cluster capacity**
   ```bash
   # Check available resources on other nodes
   chaosmonkey discover --clients
   
   # Ensure other nodes can absorb the workload
   ```

2. ✅ **Service redundancy**
   ```bash
   # Verify service has multiple instances
   nomad job status <service-id>
   
   # Count should be > 1
   ```

3. ✅ **Off-hours testing**
   - Low traffic periods
   - Maintenance windows
   - Staging environment first

4. ✅ **Team coordination**
   - Notify affected teams
   - Have rollback plan
   - Monitor actively

5. ✅ **Proper ACL permissions**
   - Node write access required
   - Test permissions first

### Risk Mitigation

1. **Test in Staging First**
   ```bash
   # Always test in non-production
   export NOMAD_ADDR=http://staging-nomad:4646
   chaosmonkey execute --chaos-type host-down --target-id test-service
   ```

2. **Start with Low-Impact Nodes**
   ```bash
   # Find nodes with few allocations
   chaosmonkey discover --clients | grep "1\|2"
   
   # Drain nodes with minimal impact
   ```

3. **Coordinate with Team**
   ```bash
   # Announce in Slack/Teams
   echo "Starting node drain chaos test on msacc01p1..."
   
   # Get approval before proceeding
   ```

4. **Monitor Continuously**
   ```bash
   # Terminal 1: Run chaos
   chaosmonkey execute --chaos-type host-down --target-id my-service
   
   # Terminal 2: Monitor allocations
   watch -n 2 'nomad node status <node-id>'
   
   # Terminal 3: Monitor cluster
   watch -n 5 'chaosmonkey discover --clients'
   ```

## Manual Drain (Alternative)

If you lack ACL permissions, manually drain nodes:

### Step 1: Enable Drain

```bash
# Get node ID
NODE_ID=$(nomad node status -short | grep msacc01p1 | awk '{print $1}')

# Enable drain with deadline
nomad node drain \
  -enable \
  -deadline 2m \
  -yes \
  $NODE_ID
```

### Step 2: Monitor Migration

```bash
# Watch allocations drain
watch -n 2 "nomad node status $NODE_ID"
```

### Step 3: Document for Testing

```bash
# Note the chaos event
echo "Node $NODE_ID drained at $(date)" >> chaos-log.txt
```

### Step 4: Re-enable Node

```bash
# After testing, restore node
nomad node drain -disable $NODE_ID
nomad node eligibility -enable $NODE_ID
```

## Troubleshooting

### Permission Denied (403)

**Symptom**: `Drain API returned 403: Permission denied`

**Cause**: Token lacks node write permissions

**Solution**:
```bash
# Check current ACL policy
nomad acl policy info chaos-policy

# Update policy to include node write
nomad acl policy apply \
  -description "Chaos engineering with node access" \
  chaos-policy \
  chaos-policy.hcl

# Regenerate token with new policy
nomad acl token create \
  -name="chaos-token" \
  -policy=chaos-policy
```

### Node Already Draining

**Symptom**: `Node is already in drain mode`

**Cause**: Previous drain not completed or cleared

**Solution**:
```bash
# Disable existing drain
nomad node drain -disable <node-id>

# Re-enable scheduling
nomad node eligibility -enable <node-id>

# Try chaos experiment again
```

### Insufficient Cluster Capacity

**Symptom**: Allocations stay in `pending` state

**Cause**: No other nodes have capacity for migrated workloads

**Solution**:
```bash
# Check cluster capacity
chaosmonkey discover --clients

# Options:
1. Stop drain: nomad node drain -disable <node-id>
2. Add more nodes to cluster
3. Stop other non-critical jobs to free resources
```

### Migration Timeout

**Symptom**: Some allocations force-killed after deadline

**Cause**: Services took too long to stop gracefully

**Solution**:
```python
# Increase deadline in experiments.py
replacements = {
    "duration_seconds": 300  # 5 minutes instead of 2
}
```

## Comparison: Node Drain vs Other Chaos

| Chaos Type | Scope | Impact | Recovery | Risk |
|------------|-------|--------|----------|------|
| **Node Drain** | Entire node | ALL services | Manual | 🔴 Very High |
| **CPU Hog** | Single node | Resource contention | Auto | 🟡 Medium |
| **Memory Hog** | Single node | OOM possible | Auto | 🟠 High |
| **Network Latency** | Containers | Slow responses | Auto | 🟡 Medium |
| **Disk I/O** | Single node | I/O slowness | Auto | 🟡 Medium |

## Best Practices

1. **Always test in staging first**
2. **Verify cluster has spare capacity**
3. **Coordinate with affected teams**
4. **Monitor the entire drain process**
5. **Document recovery steps**
6. **Re-enable node after testing**
7. **Review service resilience after**

## Success Metrics

Node drain testing is successful when you can answer:

✅ Did all services migrate successfully?  
✅ Was there any data loss during migration?  
✅ How long did migration take?  
✅ Did health checks work correctly?  
✅ Were alerts triggered appropriately?  
✅ Did the cluster absorb the workload?  
✅ Can we quickly recover the node?  

## Future Enhancements

Planned improvements:

- [ ] Automatic node re-enable after duration
- [ ] Gradual drain (migrate one service at a time)
- [ ] Dry-run mode (simulate without actual drain)
- [ ] Integration with ACL token management
- [ ] Rollback automation
- [ ] Node drain scheduling

---

**Remember**: Node drain is the **nuclear option** of chaos engineering. Use it sparingly and with great care! 💥

**Command Reference**:
```bash
# Run node drain chaos
chaosmonkey execute --chaos-type host-down --target-id <service>

# Re-enable node after testing
nomad node eligibility -enable <node-id>
```
