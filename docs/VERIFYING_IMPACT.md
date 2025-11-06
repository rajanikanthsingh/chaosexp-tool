# Verifying Chaos Impact on Target Services

## How CPU Stress Affects Your Service

When the chaos CPU stress job runs, it creates **real resource contention** on the Nomad client node. Here's what happens:

### The Attack Vector

```
┌─────────────────────────────────────┐
│  Nomad Client Node                  │
│  (e.g., hostname) │
├─────────────────────────────────────┤
│                                     │
│  🎯 Your Service                    │
│     └─ Needs CPU to respond         │
│     └─ Needs CPU for processing     │
│                                     │
│  💣 Chaos Stress Job (8 workers)    │
│     └─ Consumes CPU aggressively    │
│     └─ Competes for same resources  │
│                                     │
│  ⚡ Resource Contention!            │
│     └─ Both fight for CPU time      │
│     └─ OS scheduler splits cycles   │
│     └─ Service gets degraded perf   │
└─────────────────────────────────────┘
```

### Expected Impact

| Metric | Normal | During Chaos | Impact |
|--------|---------|--------------|---------|
| **Response Time** | ~50ms | ~200-500ms | 4-10x slower |
| **CPU Available** | 100% | 20-40% | Severe contention |
| **Throughput** | 1000 req/s | 200-400 req/s | 60-80% reduction |
| **Error Rate** | <0.1% | 1-5% | Timeouts increase |

## How to Verify the Impact

### 1. Monitor Your Service Metrics

If your service has metrics/monitoring, watch for:

```bash
# Example Prometheus queries
rate(http_request_duration_seconds_sum[1m])  # Response time increases
rate(http_requests_total[1m])                 # Throughput decreases
rate(http_requests_errors[1m])                # Error rate increases
```

### 2. Check Nomad UI

1. **Open Nomad UI**: `http://your-nomad-server:4646/ui`

2. **Navigate to the target node**:
   - Jobs → Find your service
   - Click on allocation
   - Note the node name (e.g., `hostname`)

3. **Find the chaos job**:
   - Jobs → Look for `chaos-cpu-*` jobs
   - Verify it's on the same node
   - Check resource consumption

4. **View Resource Graphs**:
   - Click on the node
   - Check CPU utilization graphs
   - You should see spike during chaos

### 3. SSH to the Node (If Accessible)

```bash
# SSH to the target node
ssh hostname

# Watch real-time CPU usage
htop

# Or use top
top

# You should see:
# - Multiple 'stress' processes at ~99% CPU each
# - Your service competing for CPU
# - High load average (>8.0 during chaos)
```

### 4. Check Docker Containers

```bash
# On the target node
docker ps | grep stress

# Check resource usage
docker stats

# You'll see the stress container using significant CPU
```

### 5. Use Load Testing

Run a load test against your service:

**Before Chaos:**
```bash
# Install hey (HTTP load generator)
brew install hey

# Baseline test
hey -n 1000 -c 10 http://your-service/health

# Note the response times and throughput
```

**During Chaos:**
```bash
# Start chaos in one terminal
chaosmonkey execute --chaos-type cpu-hog --target-id your-service-job

# Run load test in another terminal (within 15s)
hey -n 1000 -c 10 http://your-service/health

# Compare results - should be significantly worse
```

### 6. Check Service Logs

Your service logs should show:

```
# Signs of stress
- Slower processing times
- Request queue buildup  
- Timeout warnings
- Connection pool exhaustion
```

### 7. Use ChaosMonkey CLI

```bash
# List active chaos jobs
chaosmonkey chaos-jobs --status running

# You'll see output like:
┌────────────────────────────────────┬──────┬────────┬─────────────────────┐
│ Job ID                             │ Type │ Status │ Submit Time         │
├────────────────────────────────────┼──────┼────────┼─────────────────────┤
│ chaos-cpu-your-service-1760010789  │ cpu  │running │ 2025-10-09 17:23:10 │
└────────────────────────────────────┴──────┴────────┴─────────────────────┘
```

## Understanding the Configuration

### Current CPU Stress Settings

From `src/chaosmonkey/stubs/actions.py`:

```python
cpu_workers = 8         # 8 parallel CPU workers
cpu_request = 4000      # 4000 MHz (4 GHz) CPU request
duration = 120          # 120 seconds by default
```

### Why 8 Workers?

- Most Nomad nodes have 8-32 CPU cores
- 8 workers ensure significant contention
- Each worker runs at ~100% of one CPU core
- Creates ~800% total CPU usage (8 cores maxed out)

### Resource Request Strategy

```python
"Resources": {
    "CPU": 4000,        # Request 4 GHz
    "MemoryMB": 512     # Minimal memory
}
```

- High CPU request ensures scheduler priority
- Minimal memory to avoid OOM issues
- Focuses purely on CPU contention

## What If You Don't See Impact?

### Possible Reasons

1. **Node Has Too Many Resources**
   - Solution: Increase workers to 16 or 32
   ```python
   cpu_workers = 16  # More aggressive
   ```

2. **Service Has CPU Limits**
   - Check service's Nomad job spec
   - Service might be throttled already
   
3. **Service Is Idle**
   - No traffic = no noticeable impact
   - Solution: Send load while chaos runs

4. **Monitoring Gaps**
   - Set up proper metrics collection
   - Use Prometheus + Grafana
   - Enable Nomad telemetry

5. **Stress Job Failed to Start**
   - Check: `chaosmonkey chaos-jobs`
   - View logs in Nomad UI
   - Verify Docker image availability

## Advanced Verification

### Using Nomad API

```bash
# Get node resource allocation
curl -s "http://nomad-server:4646/v1/node/${NODE_ID}" | \
  jq '.Resources, .Reserved'

# Get allocations on node
curl -s "http://nomad-server:4646/v1/node/${NODE_ID}/allocations" | \
  jq '.[] | {JobID, ClientStatus, Resources}'
```

### Using Prometheus (If Available)

```promql
# CPU usage by container
sum(rate(container_cpu_usage_seconds_total[1m])) 
  by (container_name, node)

# Compare your service vs stress container
sum(rate(container_cpu_usage_seconds_total{
  container_name=~"your-service|stress"
}[1m])) by (container_name)
```

### Using Grafana Dashboard

Create a dashboard with:
- Service response time (p50, p95, p99)
- Service throughput (requests/sec)
- Error rate
- CPU usage by allocation
- Mark chaos experiment timeframes

## Expected Timeline

```
T+0s   → Chaos job submitted
T+2s   → Container starts pulling
T+5s   → Stress workers begin executing
T+10s  → Full CPU contention established
         ⚡ Service impact now visible
T+120s → Stress terminates automatically
T+125s → CPU returns to normal
         ✓ Service performance recovers
```

## Real-World Example

### Scenario: Testing Account Service

```bash
# 1. Baseline measurement
hey -n 1000 -c 10 http://account-service/api/users/123
# Result: 45ms avg, 0% errors

# 2. Start chaos
chaosmonkey execute \
  --chaos-type cpu-hog \
  --target-id mobi-platform-account-service-job

# 3. During chaos (run within 15-20s)
hey -n 1000 -c 10 http://account-service/api/users/123
# Result: 385ms avg, 3% errors (timeouts)

# 4. After chaos completes
hey -n 1000 -c 10 http://account-service/api/users/123
# Result: 48ms avg, 0% errors (recovered)
```

### What This Proves

✅ Service degrades under resource contention  
✅ Service recovers after chaos ends  
✅ Error handling works (or doesn't!)  
✅ SLOs are met (or missed!)  
✅ Alerts fire appropriately (hopefully!)

## Making It More Impactful

### Increase Stress Intensity

Edit `src/chaosmonkey/stubs/actions.py`:

```python
# More aggressive
cpu_workers = 16  # Use 16 workers instead of 8
cpu_request = 8000  # Request 8 GHz

# Even more extreme
cpu_workers = 32
cpu_request = 16000
```

### Longer Duration

Edit `src/chaosmonkey/core/experiments.py`:

```python
"duration_seconds": 300,  # 5 minutes of stress
```

### Add Memory Stress

Future enhancement - combine CPU + memory stress:
```python
"--vm", "2",  # Add memory workers
"--vm-bytes", "2G",  # Allocate 2GB memory
```

## Safety Considerations

### Current Safety Features

✅ **Time-limited**: Auto-terminates after duration  
✅ **Node-constrained**: Only affects one node  
✅ **Resource-limited**: Has CPU/memory limits  
✅ **Batch job**: Won't restart if killed  
✅ **No data destruction**: Only CPU usage  

### Best Practices

1. **Start small**: 15-30 second duration first
2. **Off-hours**: Run during low-traffic periods
3. **Monitor**: Watch dashboards during test
4. **Alert team**: Let oncall know you're testing
5. **Have runbook**: Know how to manually stop if needed

### Emergency Stop

If something goes wrong:

```bash
# List chaos jobs
chaosmonkey chaos-jobs --status running

# Stop via Nomad CLI
nomad job stop chaos-cpu-<service>-<timestamp>

# Or via API
curl -X DELETE "http://nomad-server:4646/v1/job/<chaos-job-id>"

# Or via UI
# Nomad UI → Jobs → chaos-cpu-* → Stop
```

## Measuring Success

Your chaos engineering is successful when you can answer:

✅ Does the service degrade predictably under CPU stress?  
✅ Do monitoring alerts fire within expected timeframes?  
✅ Does the service recover automatically after stress?  
✅ Are error rates within acceptable SLO bounds?  
✅ Do dependent services handle the degradation gracefully?  
✅ Is the incident response process effective?  

## Next Steps

1. **Document baseline performance** before chaos
2. **Run chaos experiments** during load testing
3. **Validate monitoring and alerting** trigger correctly
4. **Test auto-scaling** responses to high CPU
5. **Verify incident response procedures** work
6. **Improve service resilience** based on findings

---

**Remember**: The goal isn't to break things - it's to **prove they work** under stress! 🎯
