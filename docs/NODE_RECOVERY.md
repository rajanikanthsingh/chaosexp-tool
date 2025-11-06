# Node Recovery Guide

## Overview

After running **host-down** chaos experiments or manually draining nodes, they must be recovered to restore full cluster capacity. This guide covers both draining and recovery operations for complete node lifecycle management.

## Quick Commands

### Drain Nodes (Simulate Failures)

```bash
# List available nodes
chaosmonkey drain-nodes

# Drain a specific node with confirmation
chaosmonkey drain-nodes --node-id <NODE_ID>

# Drain with custom deadline and skip confirmation
chaosmonkey drain-nodes --node-id <NODE_ID> --deadline 600 --yes

# Preview drain operation
chaosmonkey drain-nodes --node-id <NODE_ID> --dry-run
```

### Recover Nodes (Restore Service)

```bash
# Recover all drained nodes
chaosmonkey recover-nodes

# Recover a specific node
chaosmonkey recover-nodes --node-id <NODE_ID> --yes

# Preview recovery operation
chaosmonkey recover-nodes --dry-run
```

## Command Options

Both `drain-nodes` and `recover-nodes` support:
- `--node-id` / `-n`: Target specific node (partial ID matching supported)
- `--dry-run`: Preview operations without making changes
- `--yes` / `-y`: Skip confirmation prompts
- `--config` / `-c`: Custom configuration file path

Additional for `drain-nodes`:
- `--deadline` / `-d`: Drain deadline in seconds (default: 300)

## Step-by-Step Recovery Process

### Step 1: Check for Drained Nodes

```bash
chaosmonkey discover --clients | grep "Drain: Yes"
```

Or check specific node:
```bash
nomad node status <NODE_ID>
```

### Step 2: Run Recovery Command

```bash
chaosmonkey recover-nodes
```

**Example Output:**
```
Found 2 drained/ineligible node(s):

┌─────────────────────────────────┬─────────────┬─────────┬───────────┬──────────────┐
│ Node Name                       │ Node ID     │ Status  │ Draining  │ Eligibility  │
├─────────────────────────────────┼─────────────┼─────────┼───────────┼──────────────┤
│ hostname      │ 538b4367... │ ready   │ 🔴 Yes    │ 🔴 ineligible│
│ hostname      │ a7f3d82b... │ ready   │ 🔴 Yes    │ 🔴 ineligible│
└─────────────────────────────────┴─────────────┴─────────┴───────────┴──────────────┘

⚠️  Recover 2 node(s)? [y/N]: y

Recovering nodes...

  Disabling drain on hostname... ✓
  Enabling eligibility on hostname... ✓
  Disabling drain on hostname... ✓
  Enabling eligibility on hostname... ✓

==================================================
✓ Successfully recovered 2 node(s)

💡 Tip: Run 'chaosmonkey discover --clients' to verify node status
```

### Step 3: Verify Recovery

```bash
chaosmonkey discover --clients
```

Check that:
- ✅ **Drain**: No
- ✅ **Eligibility**: eligible  
- ✅ **Status**: ready

### Step 4: Monitor Allocation Rebalancing

```bash
watch -n 5 'nomad node status <NODE_ID> | head -30'
```

Nomad will gradually rebalance allocations across all available nodes.

## What the Recovery Command Does

### For Each Drained Node:

#### 1. **Disable Drain**

```http
POST /v1/node/{node_id}/drain
{
  "DrainSpec": null,
  "MarkEligible": false
}
```

This stops the drain process and allows existing allocations to continue.

#### 2. **Enable Eligibility**

```http
POST /v1/node/{node_id}/eligibility
{
  "Eligibility": "eligible"
}
```

This marks the node as eligible to receive new allocations.

## Manual Recovery (Alternative)

If you prefer to use the Nomad CLI directly:

### Option 1: Full Recovery

```bash
# Disable drain
nomad node drain -disable <NODE_ID>

# Enable eligibility
nomad node eligibility -enable <NODE_ID>
```

### Option 2: Quick Enable (if not draining)

```bash
nomad node eligibility -enable <NODE_ID>
```

### Option 3: Using cURL

```bash
# Disable drain
curl -X POST "http://nomad:4646/v1/node/<NODE_ID>/drain" \
  -H "X-Nomad-Token: $NOMAD_TOKEN" \
  -d '{"DrainSpec": null, "MarkEligible": false}'

# Enable eligibility
curl -X POST "http://nomad:4646/v1/node/<NODE_ID>/eligibility" \
  -H "X-Nomad-Token: $NOMAD_TOKEN" \
  -d '{"Eligibility": "eligible"}'
```

## Recovery Scenarios

### Scenario 1: Node Still Has Allocations

**Problem:** Node was marked ineligible but not fully drained.

**Solution:**
```bash
# Just enable eligibility
chaosmonkey recover-nodes --node-id <NODE_ID>
```

### Scenario 2: Node Fully Drained

**Problem:** Node has 0 allocations after drain completed.

**Solution:**
```bash
# Recover node
chaosmonkey recover-nodes --node-id <NODE_ID>

# Wait for natural rebalancing (may take time)
# Or force rebalancing by scaling jobs up/down
nomad job scale <JOB_ID> <NEW_COUNT>
```

### Scenario 3: Multiple Nodes Drained

**Problem:** Ran multiple chaos experiments and forgot to recover nodes.

**Solution:**
```bash
# Recover all at once
chaosmonkey recover-nodes

# Verify
chaosmonkey discover --clients | grep "Drain:"
```

### Scenario 4: Partial Recovery Failure

**Problem:** Some nodes recovered, others failed.

**Solution:**
```bash
# Check the error message
# May need elevated permissions

# Try individual recovery
chaosmonkey recover-nodes --node-id <FAILED_NODE_ID>

# Or use nomad CLI with elevated token
nomad node eligibility -enable <NODE_ID>
```

## Troubleshooting

### Error: "Permission denied"

**Cause:** ACL token lacks `node { policy = "write" }` permission.

**Solutions:**

1. **Use elevated token:**
   ```bash
   export NOMAD_TOKEN=<elevated_token>
   chaosmonkey recover-nodes
   ```

2. **Request access:**
   - Contact Nomad admin
   - Request `node:write` policy
   - Update `NOMAD_TOKEN` environment variable

3. **Manual recovery with admin credentials:**
   ```bash
   nomad node eligibility -enable <NODE_ID>
   ```

### Error: "Node not found"

**Cause:** Invalid node ID or node removed from cluster.

**Solution:**
```bash
# List all nodes to find correct ID
chaosmonkey discover --clients

# Use correct full node ID
chaosmonkey recover-nodes --node-id <CORRECT_ID>
```

### Error: "Connection refused"

**Cause:** Cannot connect to Nomad cluster.

**Solution:**
```bash
# Check Nomad address
echo $NOMAD_ADDR

# Verify connectivity
curl -s "$NOMAD_ADDR/v1/status/leader"

# Update if needed
export NOMAD_ADDR=http://nomad-dev-fqdn:4646
```

### Node Recovered But No Allocations

**Cause:** Nomad doesn't immediately rebalance workloads.

**Normal Behavior:**
- Nomad only places new allocations when needed
- Existing allocations stay on current nodes
- Rebalancing happens naturally over time

**Force Rebalancing (if needed):**
```bash
# Scale job down then up
nomad job scale <JOB_ID> 0
nomad job scale <JOB_ID> <ORIGINAL_COUNT>

# Or restart job
nomad job stop <JOB_ID>
nomad job run <JOB_FILE>
```

## Best Practices

### ✅ Do's

1. **Recover promptly after chaos testing**
   ```bash
   # Right after experiment
   chaosmonkey recover-nodes
   ```

2. **Use dry-run first**
   ```bash
   chaosmonkey recover-nodes --dry-run
   ```

3. **Verify recovery**
   ```bash
   chaosmonkey discover --clients
   ```

4. **Document in experiment report**
   ```bash
   echo "Nodes recovered at $(date)" >> experiment-notes.txt
   ```

5. **Set calendar reminders**
   - Schedule recovery 15 minutes after chaos window
   - Don't leave nodes drained overnight

### ❌ Don'ts

1. **Don't forget to recover nodes**
   - Reduced cluster capacity
   - May cause resource exhaustion

2. **Don't recover during active incident**
   - May cause additional disruption
   - Wait for stability first

3. **Don't recover without checking status**
   - Verify chaos experiment completed
   - Ensure no ongoing migrations

4. **Don't blindly recover all nodes**
   - Some may be intentionally drained for maintenance
   - Check with team first

## Automation Ideas

### Auto-Recovery Script

```bash
#!/bin/bash
# auto-recover.sh - Automatically recover nodes after chaos

EXPERIMENT_DURATION=300  # 5 minutes

# Run chaos experiment
chaosmonkey run-experiment host-down --service-id my-service

# Wait for experiment to complete
sleep $EXPERIMENT_DURATION

# Auto-recover
sleep 60  # Give time for observation
chaosmonkey recover-nodes --dry-run
sleep 5
chaosmonkey recover-nodes <<< "y"  # Auto-confirm

# Verify
chaosmonkey discover --clients | grep "Drain:"
```

### Scheduled Recovery (Cron)

```bash
# Add to crontab: Recover any drained nodes daily at 2 AM
0 2 * * * cd /path/to/chaosmonkey && chaosmonkey recover-nodes <<< "y" >> /var/log/node-recovery.log 2>&1
```

### Monitoring Alert

Set up monitoring to alert if nodes remain drained for too long:

```bash
#!/bin/bash
# check-drained-nodes.sh

DRAINED_COUNT=$(chaosmonkey discover --clients | grep -c "Drain: Yes")

if [ "$DRAINED_COUNT" -gt 0 ]; then
  echo "ALERT: $DRAINED_COUNT node(s) still drained!"
  # Send notification
  curl -X POST https://hooks.slack.com/... \
    -d "{\"text\":\"⚠️ $DRAINED_COUNT Nomad node(s) still drained!\"}"
fi
```

## Recovery Checklist

After running host-down chaos:

- [ ] Wait for chaos experiment to complete
- [ ] Check node status: `chaosmonkey discover --clients`
- [ ] Identify drained nodes
- [ ] Run recovery: `chaosmonkey recover-nodes`
- [ ] Verify recovery successful
- [ ] Check service health
- [ ] Monitor allocation rebalancing
- [ ] Document in experiment report
- [ ] Notify team of recovery

## Summary

| Method | Command | When to Use |
|--------|---------|-------------|
| **Auto-recover all** | `chaosmonkey recover-nodes` | After chaos testing |
| **Recover specific** | `chaosmonkey recover-nodes -n <ID>` | Targeted recovery |
| **Dry run** | `chaosmonkey recover-nodes --dry-run` | Preview changes |
| **Manual CLI** | `nomad node eligibility -enable <ID>` | If tool fails |
| **Verify** | `chaosmonkey discover --clients` | Check status |

---

**Key Takeaway:** Always recover drained nodes after chaos experiments to restore full cluster capacity! 🔄

**Related Docs:**
- [Host-Down Strategy](./HOST_DOWN_STRATEGY.md) - How node drain works
- [Node Drain Guide](./NODE_DRAIN.md) - Complete drain documentation
- [Reports Guide](./REPORTS_GUIDE.md) - View experiment results
